from sqlalchemy import create_engine, Column, String, DateTime, ForeignKey, Float, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
import uuid
from datetime import datetime
import os
from dotenv import load_dotenv

# 1. CHARGER le .env EN PREMIER
load_dotenv()

# 2. RÉCUPÉRER l'URL (Neon ou SQLite en secours)
DATABASE_URL = os.getenv("DATABASE_URL")

# Si on est sur Neon, on s'assure d'utiliser le bon préfixe pour SQLAlchemy
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Fallback si le .env est mal lu
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./hospital_stage.db"

# 3. CRÉATION DE L'ENGINE
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- MODÈLES ---

class Department(Base):
    __tablename__ = "departments"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, nullable=False)

class Intern(Base):
    __tablename__ = "interns"
    id = Column(String, primary_key=True) # Correspond à l'UUID du QR code
    first_name = Column(String)
    last_name = Column(String)
    department_id = Column(String, ForeignKey("departments.id"))

class AttendanceEvent(Base):
    __tablename__ = "attendance_events"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    intern_id = Column(String, ForeignKey("interns.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)
    type = Column(String) # "check-in" ou "check-out"

class DailyStatus(Base):
    __tablename__ = "daily_status"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    intern_id = Column(String, ForeignKey("interns.id"))
    date = Column(DateTime, default=datetime.utcnow)
    arrival_time = Column(DateTime, nullable=True)
    departure_time = Column(DateTime, nullable=True)
    status = Column(String) 
    work_duration = Column(Float, default=0.0)
    checkin_status  = Column(String,  nullable=True)
    checkout_status = Column(String,  nullable=True)
    needs_attention = Column(Boolean, default=False)

# 4. CRÉATION DES TABLES
Base.metadata.create_all(bind=engine)
print(f"✅ Connecté à : {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else 'SQLite local'}")