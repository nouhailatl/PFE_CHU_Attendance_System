from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv
load_dotenv(BACKEND_ROOT / ".env")

from dotenv import load_dotenv
load_dotenv()
from database import SessionLocal, Department

db = SessionLocal()

deps = ["Cardiologie", "Pédiatrie", "Chirurgie", "Neurologie"]
for nom in deps:
    d = Department(name=nom)
    db.add(d)

db.commit()

tous = db.query(Department).all()
for d in tous:
    print(f"ID: {d.id} | Nom: {d.name}")