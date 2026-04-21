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