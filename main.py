"""
CHU Internship Attendance Platform — main.py
=============================================

CHECK-IN tiers (Morocco local time — UTC+1, fixed offset, no DST):
  before 08:30        → ❌ rejected  (window not open)
  08:30 – 09:35       → on_time
  09:36 – 10:10       → late
  after  10:10        → missed_checkin  (recorded, NOT rejected)

CHECK-OUT tiers:
  before 15:00        → early_checkout  (recorded with flag, NOT rejected)
  15:00 – 17:00       → completed
  after  17:00        → missed_checkout (recorded, NOT rejected)

OTHER RULES:
  - Any two scans within 5 minutes         → ❌ rejected (double-scan guard)
  - No scan at all by end of day           → auto-marked "absent"
    via POST /admin/mark-absences (run once at ~18:00 via cron or manually)
  - Checked in but no checkout by night    → auto-closed as "missed_checkout"
    via POST /admin/auto-close-checkouts   (run once at ~23:00 via cron)
    work_duration = min(CHECKOUT_CLOSE - arrival_time, STANDARD_WORK_HOURS)

STATUS FIELDS on DailyStatus:
  status          → daily admin verdict (one word, shown on dashboard):
                    "on_time" | "late" | "missed_checkin"
                    | "early_checkout" | "missed_checkout" | "absent"
  checkin_status  → "on_time" | "late" | "missed_checkin" | None
  checkout_status → "completed" | "early_checkout" | "missed_checkout" | None
  needs_attention → Boolean flag the dashboard reads to show an alarm icon.
                    True whenever: missed_checkin, early_checkout,
                    missed_checkout, or absent.

NIGHTLY PIPELINE — POST /admin/run-nightly-pipeline:
  Step 1 → auto-close forgotten checkouts
  Step 2 → mark absent interns
  Step 3 → run ETL + feature engineering
  Step 4 → retrain ML models (if enough data exists, else keep rule-based labels)

Times stored as UTC-naive in SQLite (backward-compatible with existing data).
All comparisons use Morocco local time (UTC+1, fixed offset).
"""
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from database import SessionLocal, Intern, DailyStatus, Department, Admin
from schemas import LoginRequest, InternCreate, CreateAdminRequest, ChangePasswordRequest
from auth import (                        
    get_current_admin,
    require_super_admin,
    verify_password,
    create_access_token,
    hash_password,
    AdminRole
)
from pydantic import BaseModel, computed_field
from typing import Optional
from datetime import datetime, time, timezone, timedelta, date as date_type
import uuid
import subprocess
import os

from excel_export import export_to_excel
import threading

def export_in_background():
    threading.Thread(target=export_to_excel, daemon=True).start()

# ── TIMEZONE ──────────────────────────────────────────────────────────────────
# Morocco has been permanently on UTC+1 since October 2018 (no DST).
TZ = timezone(timedelta(hours=1), name="Morocco/UTC+1")


def now_local() -> datetime:
    """Return the current datetime in Morocco local time (UTC+1, aware)."""
    return datetime.now(TZ)


def to_local(dt: datetime) -> datetime:
    """Convert a naive UTC datetime (from SQLite) → Morocco local time (UTC+1)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(TZ)


def to_utc_naive(dt: datetime) -> datetime:
    """Convert a Morocco-aware datetime → UTC-naive for SQLite storage."""
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


# ── TIME WINDOWS ──────────────────────────────────────────────────────────────
CHECKIN_OPEN  = time(8,  30)
CHECKIN_LATE  = time(9,  35)
CHECKIN_CLOSE = time(10, 10)

CHECKOUT_OPEN  = time(15, 0)
CHECKOUT_CLOSE = time(17, 0)

# Standard credited work hours when checkout is auto-closed at night
# An intern who arrived on time (08:30) and forgot checkout gets credited
# min(CHECKOUT_CLOSE - arrival_time, STANDARD_WORK_HOURS)
STANDARD_WORK_HOURS = 8.0

# Minimum gap between any two scans for the same intern
DOUBLE_SCAN_MINUTES = 5

# Statuses that should raise an alarm on the admin dashboard
ATTENTION_STATUSES = {"missed_checkin", "early_checkout", "missed_checkout", "absent"}

# Minimum number of intern-days of data before ML models are trusted
# Below this threshold the system falls back to rule-based labels
ML_MIN_SAMPLES = 30


# ── CHECKIN STATUS RESOLVER ───────────────────────────────────────────────────

def resolve_checkin_status(t: time) -> str:
    if t < CHECKIN_OPEN:
        raise HTTPException(
            status_code=400,
            detail="Too early for check-in — window opens at 08:30",
        )
    if t <= CHECKIN_LATE:
        return "on_time"
    if t <= CHECKIN_CLOSE:
        return "late"
    return "missed_checkin"


# ── CHECKOUT STATUS RESOLVER ──────────────────────────────────────────────────

def resolve_checkout_status(t: time) -> str:
    if t < CHECKOUT_OPEN:
        return "early_checkout"
    if t <= CHECKOUT_CLOSE:
        return "completed"
    return "missed_checkout"


# ── DOUBLE-SCAN GUARD ─────────────────────────────────────────────────────────

def check_double_scan(daily: DailyStatus, now: datetime) -> None:
    last_scan = daily.departure_time or daily.arrival_time
    if last_scan is None:
        return
    gap_minutes = (now - to_local(last_scan)).total_seconds() / 60
    if gap_minutes < DOUBLE_SCAN_MINUTES:
        remaining = int(DOUBLE_SCAN_MINUTES - gap_minutes)
        raise HTTPException(
            status_code=429,
            detail=(
                f"Scan ignored: too soon after previous scan — "
                f"wait {remaining} more minute(s)"
            ),
        )


# ── DB HELPER ─────────────────────────────────────────────────────────────────

def get_today_record(intern_id: str, today: date_type, db: Session):
    """Return today's DailyStatus for an intern, or None if no scan yet."""
    return db.query(DailyStatus).filter(
        DailyStatus.intern_id == intern_id,
        DailyStatus.date >= datetime(today.year, today.month, today.day),
        DailyStatus.date <  datetime(today.year, today.month, today.day) + timedelta(days=1),
    ).first()


def get_unclosed_checkins(today: date_type, db: Session):
    """
    Return all DailyStatus rows for today where the intern checked in
    but never checked out. These are candidates for auto-close.
    """
    return db.query(DailyStatus).filter(
        DailyStatus.date >= datetime(today.year, today.month, today.day),
        DailyStatus.date <  datetime(today.year, today.month, today.day, 23, 59, 59),
        DailyStatus.arrival_time  != None,   # noqa: E711 — SQLAlchemy needs !=
        DailyStatus.departure_time == None,  # noqa: E711
    ).all()


# ── PYDANTIC SCHEMAS ──────────────────────────────────────────────────────────

class DailyStatusOut(BaseModel):
    id: str
    intern_id: str
    status: Optional[str]
    checkin_status: Optional[str]
    checkout_status: Optional[str]
    needs_attention: Optional[bool]
    work_duration: Optional[float]
    date: Optional[datetime]
    arrival_time: Optional[datetime]
    departure_time: Optional[datetime]

    model_config = {"from_attributes": True}

    def model_post_init(self, __context):
        if self.date:
            self.date = to_local(self.date)
        if self.arrival_time:
            self.arrival_time = to_local(self.arrival_time)
        if self.departure_time:
            self.departure_time = to_local(self.departure_time)


class ScanRequest(BaseModel):
    intern_id: str


class InternCreate(BaseModel):
    first_name: str
    last_name: str
    department_id: str


# ── APP SETUP ─────────────────────────────────────────────────────────────────

app = FastAPI(title="CHU Plateforme de Pointage")
app.mount("/static", StaticFiles(directory="."), name="static")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    # Routes publiques qui peuvent être cachées
    public_routes = ["/", "/auth/login", "/docs", "/openapi.json", "/static"]
    is_public = any(request.url.path.startswith(r) for r in public_routes)
    if not is_public:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    # Routes publiques qui peuvent être cachées
    public_routes = ["/", "/auth/login", "/docs", "/openapi.json", "/static"]
    is_public = any(request.url.path.startswith(r) for r in public_routes)
    if not is_public:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ── /scan ─────────────────────────────────────────────────────────────────────

@app.post("/scan")
def register_scan(request: ScanRequest, db: Session = Depends(get_db)):

    intern = db.query(Intern).filter(Intern.id == request.intern_id).first()
    if not intern:
        raise HTTPException(status_code=404, detail="Stagiaire introuvable")

    now   = now_local()
    today = now.date()
    t     = now.time()

    daily = get_today_record(request.intern_id, today, db)

    # ── CASE A: No record today → CHECK-IN ───────────────────────────────
    if daily is None:
        checkin_status  = resolve_checkin_status(t)
        needs_attention = checkin_status in ATTENTION_STATUSES

        daily = DailyStatus(
            id=str(uuid.uuid4()),
            intern_id=request.intern_id,
            date=to_utc_naive(now),
            arrival_time=to_utc_naive(now),
            departure_time=None,
            status=checkin_status,
            checkin_status=checkin_status,
            checkout_status=None,
            work_duration=0.0,
            needs_attention=needs_attention,
        )
        db.add(daily)
        db.commit()
        

        labels = {
            "on_time":        "✅ À l'heure",
            "late":           "⏰ En retard",
            "missed_checkin": "⚠️ Hors créneau — enregistré comme missed check-in",
        }

       
        export_in_background()   # ← la nouvell ligne
    
        return {
            "event":           "check_in",
            "checkin_status":  checkin_status,
            "needs_attention": needs_attention,
            "message": (
                f"Bonjour {intern.first_name} ! "
                f"Arrivée à {now.strftime('%H:%M')} — {labels[checkin_status]}"
            ),
        }

    # ── Double-scan guard ─────────────────────────────────────────────────
    check_double_scan(daily, now)

    # ── CASE B: Checked in, no checkout yet → CHECK-OUT ──────────────────
    if daily.arrival_time and not daily.departure_time:

        checkout_status = resolve_checkout_status(t)
        arr_local       = to_local(daily.arrival_time)
        duration        = round((now - arr_local).total_seconds() / 3600, 2)

        daily.departure_time  = to_utc_naive(now)
        daily.work_duration   = duration
        daily.checkout_status = checkout_status

        if checkout_status in ATTENTION_STATUSES:
            daily.status          = checkout_status
            daily.needs_attention = True

        db.commit()

        labels = {
            "completed":       f"✅ Départ à {now.strftime('%H:%M')} — {duration}h travaillées",
            "early_checkout":  f"⚠️ Départ anticipé à {now.strftime('%H:%M')} — {duration}h (visible sur dashboard)",
            "missed_checkout": f"🔴 Hors créneau à {now.strftime('%H:%M')} — {duration}h travaillées",
        }

        export_in_background()
        
        return {
            "event":           "check_out",
            "checkout_status": checkout_status,
            "needs_attention": checkout_status in ATTENTION_STATUSES,
            "work_duration":   duration,
            "message":         f"Au revoir {intern.first_name} ! {labels[checkout_status]}",
        }

    # ── CASE C: Both already recorded ────────────────────────────────────
    return {
        "event":   "already_complete",
        "message": f"Pointage déjà complet pour aujourd'hui ({intern.first_name})",
    }


# ── /admin/auto-close-checkouts ───────────────────────────────────────────────

@app.post("/admin/auto-close-checkouts", tags=["Administration"])
def auto_close_checkouts(db: Session = Depends(get_db)):
    """
    Auto-close any intern who checked in today but never checked out.

    Called nightly (e.g. cron at 23:00) BEFORE mark-absences.

    Work duration logic:
      - We credit the intern up to CHECKOUT_CLOSE (17:00), not up to now.
        This is fairer — they should not be penalised for a system-level close.
      - We then cap the result at STANDARD_WORK_HOURS (8h) so a very early
        arrival doesn't inflate the figure.
      - Formula: min(CHECKOUT_CLOSE - arrival_time_local, STANDARD_WORK_HOURS)

    Status logic:
      - checkout_status  → always "missed_checkout"
      - status           → "missed_checkout" UNLESS already "missed_checkin"
                           (we never downgrade a worse existing status)
      - needs_attention  → always True
    """
    now   = now_local()
    today = now.date()

    unclosed = get_unclosed_checkins(today, db)
    closed_count = 0

    for daily in unclosed:
        arr_local = to_local(daily.arrival_time)

        # Credit hours up to CHECKOUT_CLOSE (17:00), capped at STANDARD_WORK_HOURS
        checkout_close_dt = now.replace(
            hour=CHECKOUT_CLOSE.hour,
            minute=CHECKOUT_CLOSE.minute,
            second=0,
            microsecond=0,
        )
        credited_hours = round(
            min(
                (checkout_close_dt - arr_local).total_seconds() / 3600,
                STANDARD_WORK_HOURS,
            ),
            2,
        )
        # Guard against negative duration (e.g. very late missed_checkin arrivals)
        credited_hours = max(credited_hours, 0.0)

        # Set a virtual departure time of CHECKOUT_CLOSE for record-keeping
        virtual_departure = now.replace(
            hour=CHECKOUT_CLOSE.hour,
            minute=CHECKOUT_CLOSE.minute,
            second=0,
            microsecond=0,
        )

        daily.departure_time  = to_utc_naive(virtual_departure)
        daily.work_duration   = credited_hours
        daily.checkout_status = "missed_checkout"
        daily.needs_attention = True

        # Never overwrite a worse checkin status with missed_checkout
        if daily.status != "missed_checkin":
            daily.status = "missed_checkout"

        closed_count += 1

    db.commit()

    return {
        "message": f"✅ {closed_count} checkout(s) automatiquement fermé(s) pour {today}",
        "date":    str(today),
        "count":   closed_count,
        "note":    (
            f"Durée créditée = min(heures jusqu'à {CHECKOUT_CLOSE.strftime('%H:%M')}, "
            f"{STANDARD_WORK_HOURS}h) par stagiaire"
        ),
    }


# ── /admin/mark-absences ──────────────────────────────────────────────────────

def _mark_absences_logic(db: Session) -> dict:
    """Core absence-marking logic, callable without auth."""
    now   = now_local()
    today = now.date()
    scanned_today = {
        row.intern_id
        for row in db.query(DailyStatus.intern_id).filter(
            DailyStatus.date >= datetime(today.year, today.month, today.day),
            DailyStatus.date <  datetime(today.year, today.month, today.day) + timedelta(days=1),
        ).all()
    }
    all_interns  = db.query(Intern).all()
    absent_count = 0
    for intern in all_interns:
        if intern.id not in scanned_today:
            db.add(DailyStatus(
                id=str(uuid.uuid4()),
                intern_id=intern.id,
                date=to_utc_naive(now),
                arrival_time=None,
                departure_time=None,
                status="absent",
                checkin_status=None,
                checkout_status=None,
                work_duration=0.0,
                needs_attention=True,
            ))
            absent_count += 1
    db.commit()
    return {"message": f"✅ {absent_count} stagiaire(s) marqué(s) absent(s) pour {today}",
            "date": str(today), "count": absent_count}

@app.post("/admin/mark-absences", tags=["Administration"])
def mark_absences(db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    return _mark_absences_logic(db)

# ── /admin/run-nightly-pipeline ───────────────────────────────────────────────

@app.post("/admin/run-nightly-pipeline", tags=["Administration"])
def run_nightly_pipeline(db: Session = Depends(get_db)):
    """
    Master nightly job. Runs all steps in order:
      1. Auto-close forgotten checkouts
      2. Mark absent interns
      3. Run ETL (transform.py) → refreshes features table + features.csv
      4. Retrain ML models (ml/train.py) → overwrites .pkl files

    Trigger via cron at 23:00 on weekdays:
      0 23 * * 1-5  curl -s -X POST http://localhost:8000/admin/run-nightly-pipeline

    Or call manually from the admin dashboard during development.
    """
    results = {}

    # ── Step 1: Auto-close checkouts ─────────────────────────────────────
    try:
        step1 = auto_close_checkouts(db)
        results["step1_auto_close"] = step1
    except Exception as e:
        results["step1_auto_close"] = {"error": str(e)}

    # ── Step 2: Mark absences ─────────────────────────────────────────────
    try:
        step2 = mark_absences(db)
        results["step2_mark_absences"] = step2
    except Exception as e:
        results["step2_mark_absences"] = {"error": str(e)}

    # ── Step 3: ETL ───────────────────────────────────────────────────────
    try:
        etl_result = subprocess.run(
            ["python", "etl/transform.py"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        results["step3_etl"] = {
            "returncode": etl_result.returncode,
            "stdout":     etl_result.stdout[-500:] if etl_result.stdout else "",
            "stderr":     etl_result.stderr[-300:] if etl_result.stderr else "",
        }
    except Exception as e:
        results["step3_etl"] = {"error": str(e)}

    # ── Step 4: ML retrain ────────────────────────────────────────────────
    ml_script = os.path.join("ml", "train.py")
    if os.path.exists(ml_script):
        try:
            ml_result = subprocess.run(
                ["python", ml_script],
                capture_output=True,
                text=True,
                timeout=120,
            )
            results["step4_ml_retrain"] = {
                "returncode": ml_result.returncode,
                "stdout":     ml_result.stdout[-500:] if ml_result.stdout else "",
                "stderr":     ml_result.stderr[-300:] if ml_result.stderr else "",
            }
        except Exception as e:
            results["step4_ml_retrain"] = {"error": str(e)}
    else:
        results["step4_ml_retrain"] = {
            "skipped": True,
            "reason":  "ml/train.py not found yet — will run once ML module is added",
        }

    return {
        "message": "✅ Pipeline nightly terminé",
        "ran_at":  now_local().isoformat(),
        "results": results,
    }


# ── /ml/predictions ───────────────────────────────────────────────────────────

@app.get("/ml/predictions", tags=["ML"])
def get_ml_predictions(db: Session = Depends(get_db)):
    """
    Returns the latest risk prediction and anomaly score per intern.

    - If ml/predict.py exists and models are trained → returns ML predictions.
    - Otherwise → returns rule-based labels from features.csv (cold start).

    Dashboard calls this endpoint. No ML knowledge needed on the frontend:
    just read risk_label, risk_confidence, is_anomaly, anomaly_score.

    Response shape per intern:
    {
        "intern_id":        "uuid",
        "full_name":        "Prénom Nom",
        "department":       "Cardiologie",
        "risk_label":       "Faible" | "Moyen" | "Élevé",
        "risk_confidence":  0.91,          # 0–1, null if rule-based
        "is_anomaly":       false,
        "anomaly_score":    -0.12,         # more negative = more anomalous, null if rule-based
        "source":           "ml" | "rules" # so dashboard can show a badge
    }
    """
    predict_script = os.path.join("ml", "predict.py")

    if os.path.exists(predict_script):
        # ML models exist — run predict.py and return its output
        try:
            result = subprocess.run(
                ["python", predict_script, "--output", "json"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                import json
                return json.loads(result.stdout)
        except Exception:
            pass  # Fall through to rule-based

    # ── Cold start / fallback: rule-based labels from features.csv ────────
    features_path = os.path.join("etl", "features.csv")
    if not os.path.exists(features_path):
        raise HTTPException(
            status_code=503,
            detail="Pas encore de données de features. Lancez d'abord le pipeline ETL.",
        )

    import csv
    predictions = []

    # Build a quick intern lookup: id → (full_name, department_name)
    interns = db.query(Intern).all()
    departments = {d.id: d.name for d in db.query(Department).all()}
    intern_map = {
        i.id: {
            "full_name":   f"{i.first_name} {i.last_name}",
            "department":  departments.get(i.department_id, "—"),
        }
        for i in interns
    }

    with open(features_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            intern_id = row["intern_id"]
            info = intern_map.get(intern_id, {"full_name": "—", "department": "—"})
            predictions.append({
                "intern_id":       intern_id,
                "full_name":       info["full_name"],
                "department":      info["department"],
                "risk_label":      row.get("risk_label", "—"),
                "risk_confidence": None,   # not available in rule-based mode
                "is_anomaly":      False,  # not available in rule-based mode
                "anomaly_score":   None,
                "source":          "rules",
            })

    return predictions


# ── OTHER ROUTES ──────────────────────────────────────────────────────────────

@app.get("/interns")
def list_interns(db: Session = Depends(get_db)):
    return db.query(Intern).all()


@app.get("/dashboard/history", response_model=list[DailyStatusOut])
def get_dashboard_data(db: Session = Depends(get_db)):
    return db.query(DailyStatus).all()


@app.post("/interns/add", tags=["Administration"])
def add_new_intern(
    intern_data: InternCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    new_uuid = str(uuid.uuid4())
    new_intern = Intern(
        id=new_uuid,
        first_name=intern_data.first_name,
        last_name=intern_data.last_name,
        department_id=intern_data.department_id,
    )
    try:
        db.add(new_intern)
        db.commit()
        db.refresh(new_intern)
        return {
            "message":   "Stagiaire ajouté avec succès",
            "id":        new_uuid,
            "full_name": f"{new_intern.first_name} {new_intern.last_name}",
        }
    except Exception as e:
        db.rollback()
        print(f"❌ REAL ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/departments")
def list_departments(db: Session = Depends(get_db)):
    return db.query(Department).all()


@app.delete("/interns/{intern_id}", tags=["Administration"])
def delete_intern(
    intern_id: str,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_super_admin)
):
    intern = db.query(Intern).filter(Intern.id == intern_id).first()
    if not intern:
        raise HTTPException(status_code=404, detail="Stagiaire non trouvé")
    db.delete(intern)
    db.commit()
    return {"message": f"Stagiaire {intern.first_name} supprimé"}


# ── AUTH ENDPOINTS ────────────────────────────────────────────────────────────

@app.post("/auth/login", tags=["Authentication"])
def login(request: LoginRequest, db: Session = Depends(get_db)):
    admin = db.query(Admin).filter(Admin.username == request.username).first()
    
    if not admin or not verify_password(request.password, admin.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Nom d'utilisateur ou mot de passe incorrect"
        )
    
    token = create_access_token(
        username=admin.username,
        role=AdminRole(admin.role),
        department_id=admin.department_id
    )
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": admin.role,
        "department_id": admin.department_id
    }


@app.post("/auth/seed-admin", tags=["Authentication"])
def seed_admin(db: Session = Depends(get_db)):
    any_admin = db.query(Admin).first()
    if any_admin:
        raise HTTPException(
            status_code=403,
            detail="Setup already completed — this endpoint is permanently locked"
        )
    
    new_admin = Admin(
        username="admin",
        hashed_password=hash_password("admin123"),
        role=AdminRole.SUPER_ADMIN.value,
        department_id=None
    )
    db.add(new_admin)
    db.commit()
    
    return {"message": "✅ Super admin created successfully — change your password after first login"}

@app.post("/auth/create-admin", tags=["Authentication"])
def create_admin(
    request: CreateAdminRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_super_admin)   # only super_admin can create accounts
):
    """
    Create a new admin or supervisor account.
    - Only callable by a logged-in super_admin.
    - Supervisors MUST have a department_id (UUID of their department).
    - Super admins have department_id = None.
    """
    # Validate role value
    try:
        role = AdminRole(request.role)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Rôle invalide. Valeurs acceptées : {[r.value for r in AdminRole]}"
        )

    # Supervisors must be linked to a department
    if role == AdminRole.SUPERVISOR and not request.department_id:
        raise HTTPException(
            status_code=400,
            detail="Un superviseur doit être assigné à un département"
        )

    # Super admins must NOT have a department (they see everything)
    if role == AdminRole.SUPER_ADMIN and request.department_id:
        raise HTTPException(
            status_code=400,
            detail="Un super admin ne peut pas être lié à un département spécifique"
        )

    # Check username uniqueness
    existing = db.query(Admin).filter(Admin.username == request.username).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Le nom d'utilisateur '{request.username}' est déjà pris"
        )

    # Verify department exists (for supervisors)
    if request.department_id:
        dept = db.query(Department).filter(Department.id == request.department_id).first()
        if not dept:
            raise HTTPException(
                status_code=404,
                detail="Département introuvable — vérifiez l'UUID"
            )

    new_admin = Admin(
        username=request.username,
        hashed_password=hash_password(request.password),
        role=role.value,
        department_id=request.department_id
    )
    db.add(new_admin)
    db.commit()

    return {
        "message":       f" Compte '{request.username}' créé avec succès",
        "username":      request.username,
        "role":          role.value,
        "department_id": request.department_id,
    }


@app.get("/auth/admins", tags=["Authentication"])
def list_admins(
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_super_admin)
):
    """List all admin accounts (super_admin only). Passwords are never returned."""
    admins = db.query(Admin).all()
    return [
        {
            "id":            a.id,
            "username":      a.username,
            "role":          a.role,
            "department_id": a.department_id,
        }
        for a in admins
    ]


@app.delete("/auth/admins/{admin_id}", tags=["Authentication"])
def delete_admin(
    admin_id: str,
    db: Session = Depends(get_db),
    current: Admin = Depends(require_super_admin)
):
    """Delete an admin account. A super_admin cannot delete their own account."""
    if admin_id == current.id:
        raise HTTPException(
            status_code=400,
            detail="Vous ne pouvez pas supprimer votre propre compte"
        )

    target = db.query(Admin).filter(Admin.id == admin_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Compte introuvable")

    db.delete(target)
    db.commit()
    return {"message": f" Compte '{target.username}' supprimé"}


@app.post("/auth/change-password", tags=["Authentication"])
def change_password(
    request: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current: Admin = Depends(get_current_admin)   # any logged-in admin
):
    """
    Any admin can change their OWN password.
    They must provide their current password to confirm identity.
    """
    if not verify_password(request.current_password, current.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Mot de passe actuel incorrect"
        )

    if len(request.new_password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Le nouveau mot de passe doit contenir au moins 8 caractères"
        )

    current.hashed_password = hash_password(request.new_password)
    db.commit()
    return {"message": " Mot de passe mis à jour avec succès"}