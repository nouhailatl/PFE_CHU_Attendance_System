from dotenv import load_dotenv
load_dotenv()

import pandas as pd
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import SessionLocal, engine   # ← engine used for pd.read_sql + to_sql

# ── Single connection via the SQLAlchemy engine (Neon / PostgreSQL) ───────────
# sqlite3 is gone — everything goes through the same engine that main.py uses.
conn = engine.connect()

print("=" * 50)
print("🚀 PIPELINE ETL — PLATEFORME CHU")
print("=" * 50)

# ─────────────────────────────────────────────────────────────────────────────
# ÉTAPE 1 — EXTRACT
# ─────────────────────────────────────────────────────────────────────────────
print("\n📥 ÉTAPE 1 — Extraction des données brutes...")

interns      = pd.read_sql("SELECT * FROM interns",      conn)
departments  = pd.read_sql("SELECT * FROM departments",  conn)
daily        = pd.read_sql("SELECT * FROM daily_status", conn)

daily["date"]           = pd.to_datetime(daily["date"])
daily["arrival_time"]   = pd.to_datetime(daily["arrival_time"])
daily["departure_time"] = pd.to_datetime(daily["departure_time"])

print(f"✅ {len(interns)} stagiaires")
print(f"✅ {len(departments)} départements")
print(f"✅ {len(daily)} enregistrements de pointage")

# ─────────────────────────────────────────────────────────────────────────────
# ÉTAPE 2 — DÉTECTION DES ANOMALIES
# ─────────────────────────────────────────────────────────────────────────────
print("\n🔍 ÉTAPE 2 — Détection des anomalies...")

non_fermees = daily[daily["departure_time"].isna()]
print(f"⚠️  Sessions non fermées : {len(non_fermees)}")

aberrantes = daily[
    (daily["work_duration"] < 0) |
    (daily["work_duration"] > 12)
]
print(f"⚠️  Durées aberrantes : {len(aberrantes)}")

# Nettoyer — keep absent rows out of the clean set but don't lose them for
# the consecutive-absence calculation below (which uses the raw `daily`).
daily_clean = daily.dropna(subset=["arrival_time"])
daily_clean = daily_clean[
    (daily_clean["work_duration"] >= 0) &
    (daily_clean["work_duration"] <= 12)
].copy()

print(f"✅ Données propres : {len(daily_clean)} enregistrements")

# ─────────────────────────────────────────────────────────────────────────────
# ÉTAPE 3 — SCHÉMA EN ÉTOILE  (written back to Neon, not SQLite)
# ─────────────────────────────────────────────────────────────────────────────
print("\n⭐ ÉTAPE 3 — Construction du schéma en étoile...")

# DIM_INTERN
dim_intern = interns[["id", "first_name", "last_name", "department_id"]].copy()
dim_intern.columns = ["intern_id", "prenom", "nom", "department_id"]
dim_intern.to_sql("dim_intern", conn, if_exists="replace", index=False)
print(f"✅ dim_intern      : {len(dim_intern)} lignes")

# DIM_DEPARTMENT
dim_department = departments[["id", "name"]].copy()
dim_department.columns = ["department_id", "nom_departement"]
dim_department.to_sql("dim_department", conn, if_exists="replace", index=False)
print(f"✅ dim_department  : {len(dim_department)} lignes")

# DIM_DATE
dates_uniques = daily_clean["date"].dt.date.unique()
dim_date = pd.DataFrame({
    "date":         dates_uniques,
    "jour":         [d.day   for d in dates_uniques],
    "mois":         [d.month for d in dates_uniques],
    "annee":        [d.year  for d in dates_uniques],
    "jour_semaine": [pd.Timestamp(d).day_name()           for d in dates_uniques],
    "semaine":      [pd.Timestamp(d).isocalendar()[1]     for d in dates_uniques],
    "est_weekend":  [pd.Timestamp(d).weekday() >= 5       for d in dates_uniques],
})
dim_date.to_sql("dim_date", conn, if_exists="replace", index=False)
print(f"✅ dim_date        : {len(dim_date)} lignes")

# FACT_ATTENDANCE
fact_attendance = daily_clean[[
    "id", "intern_id", "date",
    "arrival_time", "departure_time",
    "status", "work_duration"
]].copy()
fact_attendance["date"] = fact_attendance["date"].dt.date
fact_attendance.columns = [
    "fact_id", "intern_id", "date",
    "heure_arrivee", "heure_depart",
    "statut", "duree_heures",
]
fact_attendance.to_sql("fact_attendance", conn, if_exists="replace", index=False)
print(f"✅ fact_attendance : {len(fact_attendance)} lignes")

# ─────────────────────────────────────────────────────────────────────────────
# ÉTAPE 4 — FEATURE ENGINEERING
# ─────────────────────────────────────────────────────────────────────────────
print("\n⚙️  ÉTAPE 4 — Calcul des indicateurs par stagiaire...")

# Use the FULL daily table (including absent rows) for consecutive-absence calc
# but only present days for duration/lateness metrics.
total_jours = daily["date"].dt.date.nunique()
features = []

for intern_id in interns["id"]:
    # All rows for this intern (present + absent)
    all_data     = daily[daily["intern_id"] == intern_id]
    # Only present rows (arrival_time not null, duration sensible)
    present_data = daily_clean[daily_clean["intern_id"] == intern_id]

    if len(all_data) == 0:
        continue

    # 1. Taux de présence  (based on present days vs total working days)
    taux_presence = round((len(present_data) / total_jours) * 100, 2)

    # 2. Retard moyen — use checkin_status if available, else fall back to
    #    the old "Retard" status string so existing data still works.
    if "checkin_status" in present_data.columns:
        retards = present_data[present_data["checkin_status"].isin(["late", "missed_checkin"])]
    else:
        retards = present_data[present_data["status"] == "Retard"]

    if len(retards) > 0 and present_data["arrival_time"].notna().any():
        # Minutes past 08:30
        retard_minutes = retards["arrival_time"].apply(
            lambda t: max(0, (t.hour * 60 + t.minute) - (8 * 60 + 30))
            if pd.notna(t) else 0
        )
        retard_moyen = round(retard_minutes.mean(), 2)
    else:
        retard_moyen = 0

    # 3. Variabilité horaire
    variabilite = round(present_data["work_duration"].std(), 2) if len(present_data) > 1 else 0

    # 4. Absentéisme consécutif max  (uses ALL rows, not just clean ones)
    dates_presentes = set(all_data.dropna(subset=["arrival_time"])["date"].dt.date)
    if len(all_data) > 0:
        toutes_dates = pd.date_range(
            all_data["date"].min(), all_data["date"].max(), freq="B"
        )
        max_absent = compteur = 0
        for d in toutes_dates:
            if d.date() not in dates_presentes:
                compteur += 1
                max_absent = max(max_absent, compteur)
            else:
                compteur = 0
    else:
        max_absent = 0

    # 5. Score d'irrégularité
    irregularite = round(
        present_data["work_duration"].std() / present_data["work_duration"].mean(), 2
    ) if (len(present_data) > 1 and present_data["work_duration"].mean() > 0) else 0

    # 6. Score d'engagement
    score = round(
        (taux_presence * 0.5) +
        (max(0, 100 - retard_moyen) * 0.3) +
        (max(0, 100 - irregularite * 10) * 0.2), 2
    )

    features.append({
        "intern_id":                 intern_id,
        "taux_presence":             taux_presence,
        "retard_moyen_min":          retard_moyen,
        "variabilite_horaire":       variabilite,
        "max_absences_consecutives": max_absent,
        "score_irregularite":        irregularite,
        "score_engagement":          min(score, 100),
    })

df_features = pd.DataFrame(features)
print(f"✅ {len(df_features)} profils calculés")

# ─────────────────────────────────────────────────────────────────────────────
# ÉTAPE 5 — LABELS ML
# ─────────────────────────────────────────────────────────────────────────────
print("\n🏷️  ÉTAPE 5 — Attribution des labels de risque...")

def calculer_risque(row):
    if row["taux_presence"] < 50 or row["max_absences_consecutives"] >= 5:
        return "Élevé"
    elif row["taux_presence"] < 75 or row["max_absences_consecutives"] >= 3:
        return "Moyen"
    else:
        return "Faible"

df_features["risk_label"] = df_features.apply(calculer_risque, axis=1)
print(df_features["risk_label"].value_counts().to_string())

# ─────────────────────────────────────────────────────────────────────────────
# ÉTAPE 6 — SAVE
# ─────────────────────────────────────────────────────────────────────────────
print("\n💾 ÉTAPE 6 — Sauvegarde des résultats...")

# Resolve output path relative to this file so it works from any cwd
ETL_DIR      = os.path.dirname(os.path.abspath(__file__))
FEATURES_CSV = os.path.join(ETL_DIR, "features.csv")

df_features.to_csv(FEATURES_CSV, index=False)
print(f"✅ features.csv sauvegardé → {FEATURES_CSV}")

# Also write features table back to Neon for dashboard queries
df_features.to_sql("features", conn, if_exists="replace", index=False)
print("✅ Table 'features' mise à jour dans Neon")

print("\n" + "=" * 50)
print("✅ PIPELINE ETL TERMINÉ AVEC SUCCÈS !")
print("=" * 50)

conn.close()