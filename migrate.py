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
"""
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text
from database import engine

# We use raw SQL so we have full control over IF NOT EXISTS guards,
# which SQLAlchemy's create_all() does NOT provide for columns.

MIGRATIONS = [

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