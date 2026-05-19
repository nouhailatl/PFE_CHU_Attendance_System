from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv
load_dotenv(BACKEND_ROOT / ".env")

from dotenv import load_dotenv
load_dotenv()
from database import SessionLocal, Intern, Department

db = SessionLocal()

# 1. On crée le département
dept = Department(name="Urgences")
db.add(dept)
db.commit()
db.refresh(dept)

# 2. On t'ajoute officiellement
moi = Intern(
    id="eaea29cd-decb-437f-b3a4-00485df8f30c", 
    first_name="Nouhaila", 
    last_name="Touil",
    department_id=dept.id
)
db.add(moi)
db.commit()
db.close()
print("Tu es officiellement enregistrée dans la base !")