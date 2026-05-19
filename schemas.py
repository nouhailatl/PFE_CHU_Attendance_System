# schemas.py
from pydantic import BaseModel
from typing import Optional

class LoginRequest(BaseModel):
    username: str
    password: str

class InternCreate(BaseModel):
    first_name: str
    last_name: str
    department_id: str
    start_date: str | None = None
    end_date: str | None = None

class CreateAdminRequest(BaseModel):
     username: str
     password: str
     role: str                    # "dfri" | "directeur" | "chef_service" | "secretaire"
     department_id: str | None    # required only if role == "chef_service"

class ChangePasswordRequest(BaseModel):
     current_password: str
     new_password: str
