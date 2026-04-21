from sqlalchemy import create_engine, Column, String, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Float
import uuid
from datetime import datetime
from sqlalchemy import Boolean

# Pour le test, on utilise SQLite (un fichier local), 
# mais vous passerez à PostgreSQL plus tard comme prévu [cite: 41]
DATABASE_URL = "sqlite:///./hospital_stage.db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Department(Base):
    __tablename__ = "departments"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, nullable=False) # Ex: Urgences

class Intern(Base):
    __tablename__ = "interns"
    # L'ID ici doit correspondre à l'UUID du QR code ! [cite: 23]
    id = Column(String, primary_key=True) 
    first_name = Column(String)
    last_name = Column(String)
    department_id = Column(String, ForeignKey("departments.id"))

class AttendanceEvent(Base):
    __tablename__ = "attendance_events"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    intern_id = Column(String, ForeignKey("interns.id"))
    timestamp = Column(DateTime, default=datetime.utcnow) # L'heure du scan
    type = Column(String) # "check-in" ou "check-out" [cite: 27]2

class DailyStatus(Base):
    __tablename__ = "daily_status"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    intern_id = Column(String, ForeignKey("interns.id"))
    date = Column(DateTime, default=datetime.utcnow)
    arrival_time = Column(DateTime, nullable=True)
    departure_time = Column(DateTime, nullable=True)
    status = Column(String) # "Présent", "Absent", "Retard"
    work_duration = Column(Float, default=0.0) # Heures travaillées
    checkin_status  = Column(String,  nullable=True)   # punctuality detail
    checkout_status = Column(String,  nullable=True)   # checkout detail
    needs_attention = Column(Boolean, default=False)   # dashboard alarm flag

    # Cette ligne crée physiquement les tables dans le fichier .db
Base.metadata.create_all(bind=engine)
print("✅ La base de données et les tables ont été créées avec succès !")