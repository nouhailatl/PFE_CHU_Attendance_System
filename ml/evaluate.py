"""
ml/evaluate.py
==============
Comprehensive evaluation of the RandomForest model:
  • Stratified K-fold cross-validation (k=5)
  • Holdout test-set report (same 80/20 stratified split used in train.py)
  • Per-class precision / recall / F1
  • Confusion matrix (text)
  • Feature importances

Run:  python ml/evaluate.py
"""
from dotenv import load_dotenv
load_dotenv()

import os, sys, pickle
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    ConfusionMatrixDisplay,
)
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
FEATURES_CSV = os.path.join(BASE_DIR, "..", "etl", "features.csv")
RF_PATH      = os.path.join(BASE_DIR, "models", "rf_model.pkl")

FEATURE_COLS = [
    "taux_presence",
    "retard_moyen_min",
    "variabilite_horaire",
    "max_absences_consecutives",
    "score_irregularite",
    "score_engagement",
]
LABEL_COL = "risk_label"
N_SPLITS  = 5
RANDOM_STATE = 42


# ── Helpers ───────────────────────────────────────────────────────────────────

def banner(title: str):
    line = "─" * 60
    print(f"\n{line}\n  {title}\n{line}")


def load_features() -> pd.DataFrame:
    if not os.path.exists(FEATURES_CSV):
        print(f"❌ features.csv not found at {FEATURES_CSV}")
        sys.exit(1)
    df = pd.read_csv(FEATURES_CSV)
    df = df.dropna(subset=FEATURE_COLS + [LABEL_COL])
    return df


# ── Main ──────────────────────────────────────────────────────────────────────

def evaluate():
    df = load_features()
    print(f"📦  Dataset: {len(df)} rows")

    X   = df[FEATURE_COLS].values
    le  = LabelEncoder()
    y   = le.fit_transform(df[LABEL_COL].values)

    banner("Class distribution")
    dist = df[LABEL_COL].value_counts()
    for label, cnt in dist.items():
        pct = 100 * cnt / len(df)
        print(f"  {label:<15} {cnt:>5}  ({pct:.1f}%)")

    # ── Stratified holdout split (mirrors train.py) ───────────────────────────
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=RANDOM_STATE, stratify=y
    )

    banner("Holdout test set  (stratified 80/20)")

    # Apply SMOTE to train set exactly as in train.py
    min_k = max(1, min(5, pd.Series(y_train).value_counts().min() - 1))
    sm    = SMOTE(random_state=RANDOM_STATE, k_neighbors=min_k)
    X_tr_res, y_tr_res = sm.fit_resample(X_train, y_train)

    rf_eval = RandomForestClassifier(
        n_estimators=200,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    rf_eval.fit(X_tr_res, y_tr_res)
    y_pred = rf_eval.predict(X_test)

    print(classification_report(y_test, y_pred, target_names=le.classes_))

    cm = confusion_matrix(y_test, y_pred)
    banner("Confusion matrix  (rows=actual, cols=predicted)")
    header = "         " + "  ".join(f"{c:>10}" for c in le.classes_)
    print(header)
    for i, row in enumerate(cm):
        cells = "  ".join(f"{v:>10}" for v in row)
        print(f"{le.classes_[i]:>8} {cells}")

    # ── Stratified K-fold cross-validation ───────────────────────────────────
    banner(f"Stratified {N_SPLITS}-fold cross-validation  (pipeline: SMOTE → RF)")

    # Use imbalanced-learn pipeline so SMOTE is re-fitted inside each fold
    # (prevents data leakage from oversampling before CV split)
    cv_pipeline = ImbPipeline([
        ("smote", SMOTE(random_state=RANDOM_STATE, k_neighbors=min_k)),
        ("rf",    RandomForestClassifier(
                      n_estimators=200,
                      min_samples_leaf=2,
                      class_weight="balanced",
                      random_state=RANDOM_STATE,
                      n_jobs=-1,
                  )),
    ])

    skf     = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)
    scoring = ["accuracy", "f1_macro", "f1_weighted", "precision_macro", "recall_macro"]

    cv_results = cross_validate(
        cv_pipeline, X, y,
        cv=skf,
        scoring=scoring,
        return_train_score=False,
        n_jobs=-1,
    )

    print(f"  {'Metric':<22}  {'Mean':>8}  {'Std':>8}  {'Min':>8}  {'Max':>8}")
    print(f"  {'─'*22}  {'─'*8}  {'─'*8}  {'─'*8}  {'─'*8}")
    for metric in scoring:
        vals = cv_results[f"test_{metric}"]
        print(
            f"  {metric:<22}  {vals.mean():>8.4f}  {vals.std():>8.4f}"
            f"  {vals.min():>8.4f}  {vals.max():>8.4f}"
        )

    # ── Feature importances (from pre-trained artifact if available) ──────────
    banner("Feature importances  (from saved RF artifact)")
    if os.path.exists(RF_PATH):
        with open(RF_PATH, "rb") as f:
            artifact = pickle.load(f)
        saved_rf = artifact["model"]
        importances = saved_rf.feature_importances_
        pairs = sorted(zip(FEATURE_COLS, importances), key=lambda x: x[1], reverse=True)
        for feat, imp in pairs:
            bar = "█" * int(imp * 40)
            print(f"  {feat:<30}  {imp:.4f}  {bar}")
    else:
        # Fall back to the freshly trained model
        importances = rf_eval.feature_importances_
        pairs = sorted(zip(FEATURE_COLS, importances), key=lambda x: x[1], reverse=True)
        for feat, imp in pairs:
            bar = "█" * int(imp * 40)
            print(f"  {feat:<30}  {imp:.4f}  {bar}")
        print("  (artifact not found — showing holdout model importances)")

    banner("Evaluation complete ✅")


if __name__ == "__main__":
    evaluate()