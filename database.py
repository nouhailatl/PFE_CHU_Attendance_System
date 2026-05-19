from sqlalchemy import create_engine, Column, String, DateTime, ForeignKey, Float, Boolean, Integer
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
    pool_recycle=60,        # ← était 300, mettre 60
    pool_size=1,            # ← ajouter
    max_overflow=0,         # ← ajouter
    connect_args={"connect_timeout": 10, "options": "-c timezone=UTC"} if is_postgres else {}
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
    cne    = Column(String, nullable=True)
    annee  = Column(Integer, nullable=True)
    groupe = Column(String, nullable=True)


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
    hashed_password = Column(String, nullable=False)
    role            = Column(String, nullable=False)
    department_id   = Column(String, ForeignKey("departments.id"), nullable=True)


Base.metadata.create_all(bind=engine)
print(f"[OK] Connected to: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else 'SQLite local'}")
