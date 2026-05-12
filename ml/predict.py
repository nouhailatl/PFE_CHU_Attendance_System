import os
import sys
import json
import argparse
import pandas as pd
import joblib
import sqlite3

# --- Configuration ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FEATURES_PATH = os.path.join(BASE_DIR, "..", "etl", "features.csv")
MODELS_DIR = os.path.join(BASE_DIR, "models")
RISK_MODEL_PATH = os.path.join(MODELS_DIR, "risk_model.pkl")
ANOMALY_MODEL_PATH = os.path.join(MODELS_DIR, "anomaly_model.pkl")
DB_PATH = os.path.join(BASE_DIR, "..", "hospital_stage.db")

FEATURE_COLS = [
    "taux_presence",
    "retard_moyen_min",
    "variabilite_horaire",
    "max_absences_consecutives",
    "score_irregularite",
    "score_engagement"
]

def load_intern_details():
    """Fetch intern names and departments from the database for enrichment."""
    details = {}
    if not os.path.exists(DB_PATH):
        return details
    try:
        conn = sqlite3.connect(DB_PATH)
        query = """
            SELECT i.id, i.first_name, i.last_name, d.name as department
            FROM interns i
            LEFT JOIN departments d ON i.department_id = d.id
        """
        df_interns = pd.read_sql_query(query, conn)
        conn.close()
        for _, row in df_interns.iterrows():
            details[row['id']] = {
                "full_name": f"{row['first_name']} {row['last_name']}",
                "department": row['department']
            }
    except Exception:
        pass # Fallback to empty details if DB fails
    return details

def predict(output_format="text"):
    # 1. Check if models exist
    if not os.path.exists(RISK_MODEL_PATH) or not os.path.exists(ANOMALY_MODEL_PATH):
        if output_format == "json":
            print(json.dumps([]))
        else:
            print("Error: Models not found. Run training first.")
        return

    # 2. Load Models
    risk_data = joblib.load(RISK_MODEL_PATH)
    rf_model = risk_data["model"]
    le = risk_data["label_encoder"]
    
    anomaly_model = joblib.load(ANOMALY_MODEL_PATH)

    # 3. Load Features
    if not os.path.exists(FEATURES_PATH):
        if output_format == "json":
            print(json.dumps([]))
        return
    
    df = pd.read_csv(FEATURES_PATH)
    if df.empty:
        if output_format == "json":
            print(json.dumps([]))
        return

    X = df[FEATURE_COLS]
    intern_ids = df["intern_id"].tolist()
    
    # 4. Run Predictions
    risk_preds = rf_model.predict(X)
    risk_labels = le.inverse_transform(risk_preds)
    risk_probs = rf_model.predict_proba(X).max(axis=1)
    
    # IsolationForest: 1 for normal, -1 for anomaly
    anomaly_preds = anomaly_model.predict(X)
    anomaly_scores = anomaly_model.decision_function(X) # lower is more anomalous
    
    # 5. Enrich with Intern Details (Names/Depts)
    intern_details = load_intern_details()
    
    results = []
    for i in range(len(df)):
        iid = intern_ids[i]
        details = intern_details.get(iid, {"full_name": "Unknown", "department": "Unknown"})
        
        results.append({
            "intern_id": iid,
            "full_name": details["full_name"],
            "department": details["department"],
            "risk_label": str(risk_labels[i]),
            "risk_confidence": round(float(risk_probs[i]), 2),
            "is_anomaly": bool(anomaly_preds[i] == -1),
            "anomaly_score": round(float(anomaly_scores[i]), 3),
            "source": "ml"
        })

    # 6. Output
    if output_format == "json":
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        # Simple text summary for CLI users
        for res in results:
            status = "ANOMALY" if res["is_anomaly"] else "Normal"
            print(f"Intern {res['intern_id']} ({res['full_name']}): {res['risk_label']} (conf: {res['risk_confidence']}) | {status}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", choices=["json", "text"], default="text")
    args = parser.parse_args()
    
    predict(output_format=args.output)