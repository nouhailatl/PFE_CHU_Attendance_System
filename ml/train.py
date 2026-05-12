import os
import sys
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.preprocessing import LabelEncoder

# --- Configuration ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FEATURES_PATH = os.path.join(BASE_DIR, "..", "etl", "features.csv")
MODELS_DIR = os.path.join(BASE_DIR, "models")
RISK_MODEL_PATH = os.path.join(MODELS_DIR, "risk_model.pkl")
ANOMALY_MODEL_PATH = os.path.join(MODELS_DIR, "anomaly_model.pkl")

# We use these 6 numeric features as specified
FEATURE_COLS = [
    "taux_presence",
    "retard_moyen_min",
    "variabilite_horaire",
    "max_absences_consecutives",
    "score_irregularite",
    "score_engagement"
]
LABEL_COL = "risk_label"

def train():
    # 1. Load Data
    if not os.path.exists(FEATURES_PATH):
        print(f"Error: {FEATURES_PATH} not found.")
        sys.exit(1)

    df = pd.read_csv(FEATURES_PATH)

    # 2. Cold Start Guard
    if len(df) < 30:
        print(f"Warning: Only {len(df)} rows found in features.csv. Minimum 30 rows required for ML training.")
        print("Falling back to rule-based labels. Training aborted.")
        sys.exit(0)

    print(f"Starting training on {len(df)} records...")

    # Prepare features
    X = df[FEATURE_COLS]
    
    # --- Model 1: Risk Classifier (Supervised) ---
    y = df[LABEL_COL]
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)

    rf_model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')
    rf_model.fit(X, y_encoded)

    # Save RF model + LabelEncoder together
    os.makedirs(MODELS_DIR, exist_ok=True)
    joblib.dump({"model": rf_model, "label_encoder": le}, RISK_MODEL_PATH)
    print(f"Successfully saved Risk Model to {RISK_MODEL_PATH}")

    # --- Model 2: Anomaly Detector (Unsupervised) ---
    # Isolation Forest flags unusual patterns
    iso_forest = IsolationForest(n_estimators=100, contamination='auto', random_state=42)
    iso_forest.fit(X)

    joblib.dump(iso_forest, ANOMALY_MODEL_PATH)
    print(f"Successfully saved Anomaly Model to {ANOMALY_MODEL_PATH}")

if __name__ == "__main__":
    train()