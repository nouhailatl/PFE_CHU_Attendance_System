from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import SessionLocal, Intern, DailyStatus 
from pydantic import BaseModel
from datetime import datetime, time 
import uuid

app = FastAPI(title="Plateforme de Pointage CHU")

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
    # ... (ton code de scan est parfait, pas de changement ici)
    pass

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