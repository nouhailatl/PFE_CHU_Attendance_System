from pathlib import Path
import sys

# Keeping the team's path setup for executing outside of root directory
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv
load_dotenv(BACKEND_ROOT / ".env")

"""
migrate.py — safe additive migration for Neon DB.
==================================================
Run this ONCE to bring the schema up to date without touching existing data.

What it does:
  • Creates the ml_predictions table if it doesn't exist yet.
  • Adds any missing columns to daily_status that earlier versions omitted
    (checkin_status, checkout_status, needs_attention) — safe no-ops if
    they already exist on Neon.
  • Never drops a table, never truncates, never modifies existing rows.

Safe to re-run: every operation is guarded by IF NOT EXISTS or a
column-existence check.

Nouveautés v2 :
  • Table  'rotations'        — périodes de stage par service
  • Colonne interns.cne       — N° APOGEE (identifiant universitaire)
  • Colonne interns.annee     — année d'études (3, 4, 5 ou 6)
  • Colonne interns.groupe    — groupe de TD (G1, G2, G3…)
 
Safe to re-run : chaque opération est gardée par IF NOT EXISTS ou
ADD COLUMN IF NOT EXISTS (PostgreSQL ≥ 9.6 / Neon).
"""
from sqlalchemy import text
from database import engine

# We use raw SQL so we have full control over IF NOT EXISTS guards,
# which SQLAlchemy's create_all() does NOT provide for columns.

MIGRATIONS = [

    # ── Colonnes supplémentaires sur interns ──────────────────────────────────
    """
    ALTER TABLE interns
        ADD COLUMN IF NOT EXISTS cne VARCHAR
    """,
    """
    ALTER TABLE interns
        ADD COLUMN IF NOT EXISTS annee INTEGER
    """,
    """
    ALTER TABLE interns
        ADD COLUMN IF NOT EXISTS groupe VARCHAR
    """,
    # Nouveaux champs Intern
    "ALTER TABLE interns ADD COLUMN IF NOT EXISTS type VARCHAR",
    "ALTER TABLE interns ADD COLUMN IF NOT EXISTS school VARCHAR",
    "ALTER TABLE interns ADD COLUMN IF NOT EXISTS specialty VARCHAR",
    "ALTER TABLE interns ADD COLUMN IF NOT EXISTS start_date DATE",
    "ALTER TABLE interns ADD COLUMN IF NOT EXISTS end_date DATE",
    "ALTER TABLE interns ADD COLUMN IF NOT EXISTS archive_status VARCHAR DEFAULT 'active'",

    # Arborescence Department
    "ALTER TABLE departments ADD COLUMN IF NOT EXISTS parent_id VARCHAR REFERENCES departments(id)",
 
    # ── Index sur cne pour les lookups rapides à l'import ─────────────────────
    """
    CREATE INDEX IF NOT EXISTS ix_interns_cne
        ON interns (cne)
    """,
 
    # ── Table rotations ───────────────────────────────────────────────────────
    # Un étudiant peut passer par plusieurs services (rotations successives).
    # Chaque ligne = un passage dans un service pour une période donnée.
    # Le scanner lit cette table pour savoir dans quel service pointer le scan.
    """
    CREATE TABLE IF NOT EXISTS rotations (
        id             VARCHAR PRIMARY KEY,
        intern_id      VARCHAR NOT NULL REFERENCES interns(id) ON DELETE CASCADE,
        department_id  VARCHAR NOT NULL REFERENCES departments(id),
        periode_num    INTEGER NOT NULL,
        date_debut     DATE    NOT NULL,
        date_fin       DATE    NOT NULL,
        annee_univ     VARCHAR DEFAULT '2025-2026',
        created_at     TIMESTAMP DEFAULT now(),
        UNIQUE (intern_id, department_id, periode_num, annee_univ)
    )
    """,
 
    # ── Index pour le scanner (lookup par intern_id + date du jour) ───────────
    """
    CREATE INDEX IF NOT EXISTS ix_rotations_intern_date
        ON rotations (intern_id, date_debut, date_fin)
    """,
 
    # ── Index pour la vue planning (lookup par department_id + période) ───────
    """
    CREATE INDEX IF NOT EXISTS ix_rotations_dept_periode
        ON rotations (department_id, periode_num)
    """,
 

    # ── 1. ml_predictions table ───────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS ml_predictions (
        id               VARCHAR PRIMARY KEY,
        intern_id        VARCHAR REFERENCES interns(id),
        risk_label       VARCHAR,
        risk_confidence  FLOAT,
        is_anomaly       BOOLEAN,
        anomaly_score    FLOAT,
        shadow_mode      BOOLEAN DEFAULT TRUE,
        predicted_at     TIMESTAMP DEFAULT now()
    )
    """,

    # ── 2. Index on ml_predictions.intern_id ─────────────────────────────────
    """
    CREATE INDEX IF NOT EXISTS ix_ml_predictions_intern_id
        ON ml_predictions (intern_id)
    """,

    # ── 3. daily_status — add checkin_status if missing ───────────────────────
    # PostgreSQL doesn't have IF NOT EXISTS for ADD COLUMN before v9.6, but
    # Neon runs PostgreSQL 15+ so this is fine.
    """
    ALTER TABLE daily_status
        ADD COLUMN IF NOT EXISTS checkin_status VARCHAR
    """,

    # ── 4. daily_status — add checkout_status if missing ─────────────────────
    """
    ALTER TABLE daily_status
        ADD COLUMN IF NOT EXISTS checkout_status VARCHAR
    """,

    # ── 5. daily_status — add needs_attention if missing ─────────────────────
    """
    ALTER TABLE daily_status
        ADD COLUMN IF NOT EXISTS needs_attention BOOLEAN DEFAULT FALSE
    """,

    # ── 6. daily_status — add department_id if missing ───────────────────────
    """
    ALTER TABLE daily_status
        ADD COLUMN IF NOT EXISTS department_id VARCHAR REFERENCES departments(id)
    """,

    # ──────────────────────────────────────────────────────────────────────────
    # ── PHASE 1: FILIÈRE STRUCTURE ────────────────────────────────────────────
    # ──────────────────────────────────────────────────────────────────────────
    
    # ── 7. Create etablissements table ────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS etablissements (
        id             VARCHAR PRIMARY KEY,
        nom            VARCHAR UNIQUE NOT NULL,
        type           VARCHAR,
        description    TEXT,
        created_at     TIMESTAMP DEFAULT now()
    )
    """,
    
    # ── 8. Create specialites_filieres table ──────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS specialites_filieres (
        id             VARCHAR PRIMARY KEY,
        filiere        VARCHAR NOT NULL,
        nom            VARCHAR NOT NULL,
        description    TEXT,
        created_at     TIMESTAMP DEFAULT now(),
        UNIQUE (filiere, nom)
    )
    """,

    # ── 9. Create PostgreSQL ENUM for filiere (if PostgreSQL) ─────────────────
    # For PostgreSQL: create ENUM type for strict type checking
    # For SQLite: this is skipped (no error) since SQLite doesn't support ENUMs
    """
    DO $$ BEGIN
        CREATE TYPE filiere_enum AS ENUM ('Médicale', 'Infirmière', 'Techniques Santé/Lab', 'Administrative');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;
    """,

    # ── 10. Add filiere column to interns ──────────────────────────────────────
    """
    ALTER TABLE interns
        ADD COLUMN IF NOT EXISTS filiere VARCHAR
    """,

    # ── 11. Add specialite_id column to interns ───────────────────────────────
    """
    ALTER TABLE interns
        ADD COLUMN IF NOT EXISTS specialite_id VARCHAR REFERENCES specialites_filieres(id)
    """,

    # ── 12. Add etablissement_id column to interns ────────────────────────────
    """
    ALTER TABLE interns
        ADD COLUMN IF NOT EXISTS etablissement_id VARCHAR REFERENCES etablissements(id)
    """,

    # ── 13. Index on etablissements.nom for fast lookups ──────────────────────
    """
    CREATE INDEX IF NOT EXISTS ix_etablissements_nom
        ON etablissements (nom)
    """,

    # ── 14. Index on specialites_filieres for lookups ───────────────────────── 
    """
    CREATE INDEX IF NOT EXISTS ix_specialites_filiere
        ON specialites_filieres (filiere)
    """,

    # ── 15. Index on interns.filiere for filtering ────────────────────────────
    """
    CREATE INDEX IF NOT EXISTS ix_interns_filiere
        ON interns (filiere)
    """,

    # ── 16. Index on interns.etablissement_id ────────────────────────────────
    """
    CREATE INDEX IF NOT EXISTS ix_interns_etablissement_id
        ON interns (etablissement_id)
    """,
]


def run_migrations():
    with engine.connect() as conn:
        for i, sql in enumerate(MIGRATIONS, start=1):
            stmt = sql.strip()
            # Derive a short label for the log line
            first_line = stmt.splitlines()[0].strip()
            print(f"  [{i}/{len(MIGRATIONS)}] {first_line[:72]}…")
            try:
                conn.execute(text(stmt))
                conn.commit()
                print(f"         ✅ OK")
            except Exception as e:
                # Roll back this statement only; continue with the rest
                conn.rollback()
                err_str = str(e).split("\n")[0]
                print(f"         ⚠️  Skipped ({err_str})")

    print("\n✅ Migration complete — no existing data was modified.")


if __name__ == "__main__":
    print("🔧 Running Neon DB migrations…\n")
    run_migrations()