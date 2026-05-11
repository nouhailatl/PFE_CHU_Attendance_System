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

class CreateAdminRequest(BaseModel):
     username: str
     password: str
     role: str                    # "super_admin" | "supervisor"
     department_id: str | None    # required if role == "supervisor"

class ChangePasswordRequest(BaseModel):
     current_password: str
     new_password: str
