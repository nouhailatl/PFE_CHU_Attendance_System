from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import SessionLocal, Intern, DailyStatus 
from pydantic import BaseModel
from datetime import datetime, time 
import uuid
from fastapi.staticfiles import StaticFiles



app = FastAPI(title="Plateforme de Pointage CHU")

app.mount("/static", StaticFiles(directory="."), name="static")

# Configuration CORS
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
    department_id: int

# --- ROUTES ---

@app.post("/scan")
def register_scan(request: ScanRequest, db: Session = Depends(get_db)):
    # 1. Check the intern exists
    intern = db.query(Intern).filter(Intern.id == request.intern_id).first()
    if not intern:
        raise HTTPException(status_code=404, detail="Stagiaire introuvable")

    now = datetime.utcnow()
    today = now.date()

    # 2. Get or create today's DailyStatus
    daily = db.query(DailyStatus).filter(
        DailyStatus.intern_id == request.intern_id,
        DailyStatus.date >= datetime(today.year, today.month, today.day)
    ).first()

    if not daily:
        # First scan of the day = check-in
        daily = DailyStatus(
            id=str(uuid.uuid4()),
            intern_id=request.intern_id,
            date=now,
            arrival_time=now,
            status="Présent",
            work_duration=0.0
        )
        db.add(daily)
        db.commit()
        return {"message": f"✅ Bonjour {intern.first_name} ! Arrivée enregistrée à {now.strftime('%H:%M')}"}
    
    elif daily.arrival_time and not daily.departure_time:
        # Second scan = check-out
        duration = (now - daily.arrival_time).total_seconds() / 3600
        daily.departure_time = now
        daily.work_duration = round(duration, 2)
        db.commit()
        return {"message": f"👋 Au revoir {intern.first_name} ! Départ à {now.strftime('%H:%M')} — {daily.work_duration}h travaillées"}
    
    else:
        return {"message": f"ℹ️ Pointage déjà complet pour aujourd'hui ({intern.first_name})"}

@app.get("/interns")
def list_interns(db: Session = Depends(get_db)):
    return db.query(Intern).all()

@app.get("/dashboard/history")
def get_dashboard_data(db: Session = Depends(get_db)):
    return db.query(DailyStatus).all()

@app.post("/interns/add", tags=["Administration"])
def add_new_intern(intern_data: InternCreate, db: Session = Depends(get_db)):
    new_uuid = str(uuid.uuid4())
    
    new_intern = Intern(
        id=new_uuid,
        first_name=intern_data.first_name,
        last_name=intern_data.last_name,
        department_id=intern_data.department_id
    )
    
    try:
        db.add(new_intern)
        db.commit()
        db.refresh(new_intern)
        
        # CORRECTION ICI : On renvoie "id" pour que le HTML le trouve facilement
        return {
            "message": "Stagiaire ajouté avec succès",
            "id": new_uuid, 
            "full_name": f"{new_intern.first_name} {new_intern.last_name}"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Erreur de base de données (Vérifiez que DB Browser est fermé)")

@app.delete("/interns/{intern_id}", tags=["Administration"])
def delete_intern(intern_id: str, db: Session = Depends(get_db)):
    intern = db.query(Intern).filter(Intern.id == intern_id).first()
    if not intern:
        raise HTTPException(status_code=404, detail="Stagiaire non trouvé")
    
    db.delete(intern)
    db.commit()
    return {"message": f"Stagiaire {intern.first_name} supprimé"}