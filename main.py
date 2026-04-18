from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal, Intern, DailyStatus 
from pydantic import BaseModel
from datetime import datetime, time 
import uuid

app = FastAPI(title="Plateforme de Pointage CHU")

# Dépendance pour la base de données
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ScanRequest(BaseModel):
    intern_id: str

@app.post("/scan")
def register_scan(request: ScanRequest, db: Session = Depends(get_db)):
    now = datetime.now()
    current_time = now.time()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 1. Vérifier si le stagiaire existe
    intern = db.query(Intern).filter(Intern.id == request.intern_id).first()
    if not intern:
        raise HTTPException(status_code=404, detail="Stagiaire non trouvé")

    # --- LOGIQUE D'ARRIVÉE (08:30 - 10:00) ---
    if time(8, 30) <= current_time <= time(10, 0):
        already_scanned = db.query(DailyStatus).filter(
            DailyStatus.intern_id == intern.id, 
            DailyStatus.date >= today_start
        ).first()
        
        if already_scanned:
            return {"message": "Déjà scanné ce matin", "status": already_scanned.status}
        
        status = "Présent" if current_time <= time(9, 0) else "Retard"
        new_entry = DailyStatus(
            intern_id=intern.id, 
            arrival_time=now, 
            date=now,
            status=status
        )
        db.add(new_entry)
        db.commit()
        return {"status": "success", "message": f"Check-in réussi ({status}) pour {intern.first_name}"}

    # --- LOGIQUE DE DÉPART (15:00 - 17:00) ---
    elif time(15, 0) <= current_time <= time(17, 0):
        today_record = db.query(DailyStatus).filter(
            DailyStatus.intern_id == intern.id,
            DailyStatus.date >= today_start
        ).first()
        
        if not today_record:
            return {"message": "Erreur : Aucun check-in trouvé pour ce matin."}
        
        if today_record.departure_time:
            return {"message": "Check-out déjà effectué."}

        today_record.departure_time = now
        duration = (now - today_record.arrival_time).total_seconds() / 3600
        today_record.work_duration = round(duration, 2)
        
        db.commit()
        return {"status": "success", "message": f"Check-out validé. Durée : {today_record.work_duration}h"}
    
    # --- HORS CRÉNEAUX ---
    return {"message": "Scan refusé : Le pointage n'est ouvert qu'entre 08h30-10h00 et 15h00-17h00."}

@app.get("/interns")
def list_interns(db: Session = Depends(get_db)):
    return db.query(Intern).all()

# --- UNE SEULE ROUTE POUR LE DASHBOARD ---
@app.get("/dashboard/history")
def get_dashboard_data(db: Session = Depends(get_db)):
    # Cette route renvoie tout l'historique nécessaire au suivi et à la traçabilité
    return db.query(DailyStatus).all()

# 1. On définit ce que l'API doit recevoir (Nom, Prénom, etc.)
class InternCreate(BaseModel):
    first_name: str
    last_name: str
    department_id: int

# 2. On crée la route POST pour l'enregistrement
@app.post("/interns/add", tags=["Administration"])
def add_new_intern(intern_data: InternCreate, db: Session = Depends(get_db)):
    # Génération d'un identifiant unique (UUID)
    new_uuid = str(uuid.uuid4())
    
    # Création de l'objet stagiaire
    new_intern = Intern(
        id=new_uuid,
        first_name=intern_data.first_name,
        last_name=intern_data.last_name,
        department_id=intern_data.department_id
    )
    
    # Sauvegarde dans la base hospital_stage.db
    db.add(new_intern)
    db.commit()  # <-- C'est ça qui valide l'écriture !
    db.refresh(new_intern)
    
    return {
        "message": "Stagiaire ajouté avec succès",
        "intern_id": new_uuid,
        "full_name": f"{new_intern.first_name} {new_intern.last_name}"
    }