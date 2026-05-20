from sqlalchemy import create_engine, Column, String, DateTime, ForeignKey, Float, Boolean, Integer, Text, text
from sqlalchemy.orm import declarative_base, sessionmaker
import uuid
from datetime import datetime
import os
from dotenv import load_dotenv


# 1. Load .env FIRST before reading any env variable
load_dotenv()

# 2. Get DATABASE_URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

# Fix Neon/Heroku postgres:// → postgresql:// (SQLAlchemy requires the latter)
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Fallback to local SQLite if .env is missing or empty
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./hospital_stage.db"

# 3. Create engine
is_postgres = DATABASE_URL.startswith("postgresql")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    connect_args={"connect_timeout": 10, "options": "-c timezone=UTC"} if is_postgres else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()



# --- MODELS ---

class Department(Base):
    __tablename__ = "departments"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, nullable=False)


class Intern(Base):
    __tablename__ = "interns"
    id = Column(String, primary_key=True)  # matches the QR code UUID
    first_name = Column(String)
    last_name = Column(String)
    department_id = Column(String, ForeignKey("departments.id"))
    start_date = Column(String, nullable=True)
    end_date = Column(String, nullable=True)
    cne        = Column(String, nullable=True)
    annee      = Column(Integer, nullable=True)
    groupe     = Column(String, nullable=True)
    intern_type = Column(String, nullable=True)
    school     = Column(String, nullable=True)
    archived   = Column(Boolean, default=False, server_default="0")


class AttendanceEvent(Base):
    __tablename__ = "attendance_events"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    intern_id = Column(String, ForeignKey("interns.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)
    type = Column(String)  # "check-in" or "check-out"

class DailyStatus(Base):
    __tablename__ = "daily_status"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    intern_id = Column(String, ForeignKey("interns.id"))
    date = Column(DateTime, default=datetime.utcnow)
    arrival_time = Column(DateTime, nullable=True)
    departure_time = Column(DateTime, nullable=True)
    status = Column(String)
    work_duration = Column(Float, default=0.0)
    checkin_status  = Column(String, nullable=True)
    checkout_status = Column(String, nullable=True)
    needs_attention = Column(Boolean, default=False)



# 4. Create all tables

class Admin(Base):
    __tablename__ = "admins"
    id              = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username        = Column(String, unique=True, nullable=False)
    email           = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    role            = Column(String, nullable=False)
    department_id   = Column(String, ForeignKey("departments.id"), nullable=True)


class NotificationSetting(Base):
    __tablename__ = "notification_settings"
    id = Column(String, primary_key=True, default="default")
    enabled = Column(Boolean, default=False, server_default="0")
    channel = Column(String, default="email")
    recipient_email = Column(String, nullable=True)
    webhook_url = Column(Text, nullable=True)
    smtp_host = Column(String, nullable=True)
    smtp_port = Column(Integer, nullable=True)
    smtp_username = Column(String, nullable=True)
    smtp_password = Column(String, nullable=True)
    smtp_from_email = Column(String, nullable=True)
    absence_days = Column(Integer, default=3, server_default="3")
    stage_end_hours = Column(Integer, default=48, server_default="48")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NotificationLog(Base):
    __tablename__ = "notification_logs"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type = Column(String, nullable=False)
    intern_id = Column(String, ForeignKey("interns.id"), nullable=True)
    department_id = Column(String, ForeignKey("departments.id"), nullable=True)
    dedupe_key = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    channel = Column(String, nullable=False)
    recipient = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="pending")
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)
print(f"[OK] Connected to: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else 'SQLite local'}")
