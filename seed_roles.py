# seed_roles.py
from dotenv import load_dotenv
load_dotenv()
from database import SessionLocal, Admin
from auth import hash_password

db = SessionLocal()

comptes = [
    {"username": "secretaire_1",  "password": "Secr3taire!", "role": "secretaire",  "department_id": None},
    {"username": "chef_cardio",   "password": "ChefC4rdio!", "role": "supervisor",  "department_id": "UUID_CARDIO"},
    {"username": "directeur",     "password": "Dir3cteur!",  "role": "directeur",   "department_id": None},
]

for c in comptes:
    existing = db.query(Admin).filter(Admin.username == c["username"]).first()
    if not existing:
        db.add(Admin(
            username=c["username"],
            hashed_password=hash_password(c["password"]),
            role=c["role"],
            department_id=c["department_id"]
        ))
        print(f"✅ {c['username']} créé")
    else:
        print(f"⏭️  {c['username']} existe déjà")

db.commit()
db.close()