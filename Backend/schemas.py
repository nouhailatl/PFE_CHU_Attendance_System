# schemas.py
from pydantic import BaseModel
from typing import Optional
from enum import Enum as PyEnum


class FiliereEnum(str, PyEnum):
    """4 main academic pathways in CHU training programs."""
    MEDICINE = "medicine"
    NURSE = "nurse"
    TECH_SANTE_LAB_BIOLOGY = "tech_sante_lab_biology"
    ADMINISTRATIVE = "administrative"

    # Legacy labels kept so old clients and existing rows remain readable.
    MEDICALE_LEGACY = "Médicale"
    INFIRMIERE_LEGACY = "Infirmière"
    TECHNIQUES_SANTE_LEGACY = "Techniques Santé/Lab"
    ADMINISTRATIVE_LEGACY = "Administrative"


class LoginRequest(BaseModel):
    username: str
    password: str

class InternCreate(BaseModel):
    first_name: str
    last_name: str
    department_id: str
    cne: Optional[str] = None
    annee: Optional[int] = None
    groupe: Optional[str] = None

    # Legacy fields (deprecated, for backward compatibility)
    type: Optional[str] = None
    school: Optional[str] = None
    specialty: Optional[str] = None
    
    # New filière-related fields
    filiere: Optional[FiliereEnum] = None
    specialite_id: Optional[str] = None
    etablissement_id: Optional[str] = None

    start_date: str | None = None
    end_date: str | None = None


class CreateAdminRequest(BaseModel):
     username: str
     password: str
     role: str                    # "dfri" | "directeur" | "chef_service" | "secretaire"
     department_id: str | None    # required only if role == "chef_service"
     email: str | None = None

class InternUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    department_id: Optional[str] = None
    cne: Optional[str] = None
    annee: Optional[int] = None
    groupe: Optional[str] = None
    
    # Legacy fields (deprecated)
    type: Optional[str] = None
    school: Optional[str] = None
    specialty: Optional[str] = None
    
    # New filière-related fields
    filiere: Optional[FiliereEnum] = None
    specialite_id: Optional[str] = None
    etablissement_id: Optional[str] = None
    
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class ChangePasswordRequest(BaseModel):
     current_password: str
     new_password: str

class RotationCreate(BaseModel):
     intern_id: str
     department_id: str
     periode_num: int
     date_debut: str
     date_fin: str
     annee_univ: str = "2025-2026"

class DepartmentParentUpdate(BaseModel):
     parent_id: Optional[str] = None
