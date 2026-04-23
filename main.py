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

STATUS FIELDS on DailyStatus:
  status          → daily admin verdict (one word, shown on dashboard):
                    "on_time" | "late" | "missed_checkin"
                    | "early_checkout" | "missed_checkout" | "absent"
  checkin_status  → "on_time" | "late" | "missed_checkin" | None
  checkout_status → "completed" | "early_checkout" | "missed_checkout" | None
  needs_attention → Boolean flag the dashboard reads to show an alarm icon.
                    True whenever: missed_checkin, early_checkout,
                    missed_checkout, or absent.

Times stored as UTC-naive in SQLite (backward-compatible with existing data).
All comparisons use Morocco local time (UTC+1, fixed offset).
"""
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from database import SessionLocal, Intern, DailyStatus, Department
from pydantic import BaseModel, computed_field
from typing import Optional
from datetime import datetime, time, timezone, timedelta
import uuid

# ── TIMEZONE ──────────────────────────────────────────────────────────────────
# Morocco has been permanently on UTC+1 since October 2018 (no DST).
# We use a fixed-offset timezone instead of the named "Africa/Casablanca"
# zone to avoid the tzdata package returning the wrong offset on Windows.
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
#
#  CHECK-IN
#  ──────────────────────────────────────────────────────
#  before 08:30  │  08:30 ── 09:35  │  09:36 ── 10:10  │  after 10:10
#   ❌ rejected  │    on_time        │    late           │  missed_checkin ⚠️
#
CHECKIN_OPEN  = time(8,  30)   # Before this → hard reject (too early)
CHECKIN_LATE  = time(9,  35)   # After this  → "late"
CHECKIN_CLOSE = time(10, 10)   # After this  → "missed_checkin" (not rejected)

#  CHECK-OUT
#  ──────────────────────────────────────────────────────
#  before 15:00        │  15:00 ── 17:00  │  after 17:00
#  early_checkout ⚠️   │    completed     │  missed_checkout ⚠️
#
CHECKOUT_OPEN  = time(15, 0)   # Before this → "early_checkout"
CHECKOUT_CLOSE = time(17, 0)   # After this  → "missed_checkout"

# Minimum gap between any two scans for the same intern (global guard)
DOUBLE_SCAN_MINUTES = 5

# Statuses that should raise an alarm on the admin dashboard
ATTENTION_STATUSES = {"missed_checkin", "early_checkout", "missed_checkout", "absent"}


# ── CHECKIN STATUS RESOLVER ───────────────────────────────────────────────────

def resolve_checkin_status(t: time) -> str:
    """
    Map scan time to a check-in status string.
    Only raises for scans before the window opens (08:30).
    Everything else is recorded, never rejected.
    """
    if t < CHECKIN_OPEN:
        raise HTTPException(
            status_code=400,
            detail="Too early for check-in — window opens at 08:30",
        )
    if t <= CHECKIN_LATE:
        return "on_time"
    if t <= CHECKIN_CLOSE:
        return "late"
    # After 10:10: intern came very late — record it, do not lose the data
    return "missed_checkin"


# ── CHECKOUT STATUS RESOLVER ──────────────────────────────────────────────────

def resolve_checkout_status(t: time) -> str:
    """
    Map scan time to a check-out status string.
    Never raises — every checkout scan is recorded.
    """
    if t < CHECKOUT_OPEN:
        return "early_checkout"
    if t <= CHECKOUT_CLOSE:
        return "completed"
    return "missed_checkout"


# ── DOUBLE-SCAN GUARD ─────────────────────────────────────────────────────────

def check_double_scan(daily: DailyStatus, now: datetime) -> None:
    """
    Reject any scan arriving within DOUBLE_SCAN_MINUTES of the last recorded
    scan. Uses departure_time if present, otherwise arrival_time.
    Global: applies regardless of whether this would be a check-in or check-out.
    """
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

def get_today_record(intern_id: str, today: datetime.date, db: Session):
    """Return today's DailyStatus for an intern, or None if no scan yet."""
    return db.query(DailyStatus).filter(
        DailyStatus.intern_id == intern_id,
        DailyStatus.date >= datetime(today.year, today.month, today.day),
        DailyStatus.date <  datetime(today.year, today.month, today.day, 23, 59, 59),
    ).first()

class DailyStatusOut(BaseModel):
    id: str
    intern_id: str
    status: Optional[str]
    checkin_status: Optional[str]
    checkout_status: Optional[str]
    needs_attention: Optional[bool]
    work_duration: Optional[float]

    # These will be converted from UTC → UTC+1 before sending
    date: Optional[datetime]
    arrival_time: Optional[datetime]
    departure_time: Optional[datetime]

    model_config = {"from_attributes": True}

    def model_post_init(self, __context):
        # Convert all datetime fields to Morocco local time
        if self.date:
            self.date = to_local(self.date)
        if self.arrival_time:
            self.arrival_time = to_local(self.arrival_time)
        if self.departure_time:
            self.departure_time = to_local(self.departure_time)
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


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ScanRequest(BaseModel):
    intern_id: str


class InternCreate(BaseModel):
    first_name: str
    last_name: str
    department_id: str


# ── /scan ─────────────────────────────────────────────────────────────────────

@app.post("/scan")
def register_scan(request: ScanRequest, db: Session = Depends(get_db)):

    # 1. Verify intern exists
    intern = db.query(Intern).filter(Intern.id == request.intern_id).first()
    if not intern:
        raise HTTPException(status_code=404, detail="Stagiaire introuvable")

    # 2. Current Morocco local time
    now   = now_local()
    today = now.date()
    t     = now.time()

    # 3. Fetch today's record (None if first scan of the day)
    daily = get_today_record(request.intern_id, today, db)

    # ── CASE A: No record today → CHECK-IN ───────────────────────────────
    if daily is None:
        checkin_status = resolve_checkin_status(t)  # raises only if before 08:30

        # needs_attention is True for any anomaly — dashboard shows alarm icon
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
            "on_time":       "✅ À l'heure",
            "late":          "⏰ En retard",
            "missed_checkin":"⚠️ Hors créneau — enregistré comme missed check-in",
        }
        return {
            "event":          "check_in",
            "checkin_status": checkin_status,
            "needs_attention": needs_attention,
            "message": (
                f"Bonjour {intern.first_name} ! "
                f"Arrivée à {now.strftime('%H:%M')} — {labels[checkin_status]}"
            ),
        }

    # ── Double-scan guard applies to all remaining cases ──────────────────
    check_double_scan(daily, now)

    # ── CASE B: Checked in, no checkout yet → CHECK-OUT ──────────────────
    if daily.arrival_time and not daily.departure_time:

        checkout_status = resolve_checkout_status(t)

        arr_local = to_local(daily.arrival_time)
        duration  = round((now - arr_local).total_seconds() / 3600, 2)

        daily.departure_time  = to_utc_naive(now)
        daily.work_duration   = duration
        daily.checkout_status = checkout_status

        # Override daily status for checkout anomalies so the dashboard
        # shows the most critical flag (not the check-in punctuality)
        if checkout_status in ATTENTION_STATUSES:
            daily.status          = checkout_status
            daily.needs_attention = True   # trigger dashboard alarm

        db.commit()

        labels = {
            "completed":       f"✅ Départ à {now.strftime('%H:%M')} — {duration}h travaillées",
            "early_checkout":  f"⚠️ Départ anticipé à {now.strftime('%H:%M')} — {duration}h (visible sur dashboard)",
            "missed_checkout": f"🔴 Hors créneau à {now.strftime('%H:%M')} — {duration}h travaillées",
        }
        return {
            "event":            "check_out",
            "checkout_status":  checkout_status,
            "needs_attention":  checkout_status in ATTENTION_STATUSES,
            "work_duration":    duration,
            "message":          f"Au revoir {intern.first_name} ! {labels[checkout_status]}",
        }

    # ── CASE C: Both already recorded — nothing to do ────────────────────
    return {
        "event":   "already_complete",
        "message": f"Pointage déjà complet pour aujourd'hui ({intern.first_name})",
    }


# ── /admin/mark-absences ──────────────────────────────────────────────────────

@app.post("/admin/mark-absences", tags=["Administration"])
def mark_absences(db: Session = Depends(get_db)):
    """
    Auto-record 'absent' for every intern with no scan today.
    Call once at end of day (e.g. cron at 18:00, or a dashboard button).

    Interns who scanned but missed checkout already have a record —
    this endpoint does not touch them.
    """
    now   = now_local()
    today = now.date()

    # Collect intern IDs that already have a record today
    scanned_today = {
        row.intern_id
        for row in db.query(DailyStatus.intern_id).filter(
            DailyStatus.date >= datetime(today.year, today.month, today.day),
            DailyStatus.date <  datetime(today.year, today.month, today.day, 23, 59, 59),
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
                needs_attention=True,   # absent always triggers dashboard alarm
            ))
            absent_count += 1

    db.commit()
    return {
        "message": f"✅ {absent_count} stagiaire(s) marqué(s) absent(s) pour {today}",
        "date":    str(today),
        "count":   absent_count,
    }


# ── OTHER ROUTES (unchanged) ──────────────────────────────────────────────────

@app.get("/interns")
def list_interns(db: Session = Depends(get_db)):
    return db.query(Intern).all()


@app.get("/dashboard/history", response_model=list[DailyStatusOut])
def get_dashboard_data(db: Session = Depends(get_db)):
    return db.query(DailyStatus).all()


@app.post("/interns/add", tags=["Administration"])
def add_new_intern(intern_data: InternCreate, db: Session = Depends(get_db)):
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
        print(f"❌ REAL ERROR: {e}")  # ← this will show in uvicorn terminal
        raise HTTPException(
            status_code=500,
            detail=str(e)  # ← this will show in browser
        )

@app.get("/departments")
def list_departments(db: Session = Depends(get_db)):
    return db.query(Department).all()

@app.delete("/interns/{intern_id}", tags=["Administration"])
def delete_intern(intern_id: str, db: Session = Depends(get_db)):
    intern = db.query(Intern).filter(Intern.id == intern_id).first()
    if not intern:
        raise HTTPException(status_code=404, detail="Stagiaire non trouvé")
    db.delete(intern)
    db.commit()
    return {"message": f"Stagiaire {intern.first_name} supprimé"}