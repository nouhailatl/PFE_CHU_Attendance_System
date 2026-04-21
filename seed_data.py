from dotenv import load_dotenv
load_dotenv()
from database import SessionLocal, Intern, DailyStatus, Department
from datetime import datetime, timedelta
import uuid
import random

db = SessionLocal()

# IDs des départements déjà créés
departements = [d.id for d in db.query(Department).all()]

if not departements:
    print("❌ No departments found! Run seed_departments.py first.")
    db.close()
    exit()

# 40 stagiaires fictifs
stagiaires = [
    ("Ahmed", "Benali"), ("Sara", "Idrissi"), ("Youssef", "Chaoui"),
    ("Nadia", "Tazi"), ("Omar", "Filali"), ("Hiba", "Alami"),
    ("Karim", "Bennani"), ("Leila", "Chraibi"), ("Amine", "Fassi"),
    ("Zineb", "Berrada"), ("Mehdi", "Lahlou"), ("Salma", "Kettani"),
    ("Hamza", "Ghazi"), ("Rim", "Sqalli"), ("Tarik", "Ouazzani"),
    ("Dounia", "Mernissi"), ("Bilal", "Zemmouri"), ("Hajar", "Naciri"),
    ("Khalid", "Benhaddou"), ("Fatima", "Rahali"), ("Ayoub", "Senhaji"),
    ("Meryem", "Tahiri"), ("Soufiane", "Bargach"), ("Imane", "Bensouda"),
    ("Rachid", "Lazrak"), ("Samira", "Ouali"), ("Nabil", "Benmoussa"),
    ("Widad", "Fassi"), ("Jawad", "Tahiri"), ("Houda", "Lamrani"),
    ("Adil", "Skalli"), ("Nawal", "Benkirane"), ("Fouad", "Sefrioui"),
    ("Ghita", "Tazi"), ("Saad", "Chraibi"), ("Loubna", "Alaoui"),
    ("Mouad", "Bennis"), ("Asma", "Zaki"), ("Ilyas", "Rhazi"),
    ("Kenza", "Boutaleb")
]

# Profils de comportement
profils = ["regulier", "regulier", "regulier", "retard", "retard", "risque", "absent"]

debut = datetime.now() - timedelta(days=60)

for prenom, nom in stagiaires:
    intern_id = str(uuid.uuid4())
    dept_id = random.choice(departements)
    profil = random.choice(profils)

    intern = Intern(
        id=intern_id,
        first_name=prenom,
        last_name=nom,
        department_id=dept_id
    )
    db.add(intern)
    db.commit()

    # Générer 60 jours de pointage
    for i in range(60):
        jour = debut + timedelta(days=i)
        if jour.weekday() >= 5:  # Skip weekend
            continue

        # Comportement selon profil
        if profil == "regulier":
            present = random.random() > 0.05
        elif profil == "retard":
            present = random.random() > 0.10
        elif profil == "risque":
            present = random.random() > 0.35
        else:  # absent
            present = random.random() > 0.55

        if not present:
            continue

        # Heure d'arrivée
        if profil == "retard":
            arrivee = jour.replace(hour=9, minute=random.randint(0, 59))
            statut = "Retard"
        else:
            arrivee = jour.replace(hour=8, minute=random.randint(30, 55))
            statut = "Présent"

        depart = jour.replace(hour=random.randint(15, 16), minute=random.randint(0, 59))
        duree = round((depart - arrivee).total_seconds() / 3600, 2)

        entry = DailyStatus(
            intern_id=intern_id,
            date=jour,
            arrival_time=arrivee,
            departure_time=depart,
            status=statut,
            work_duration=duree
        )
        db.add(entry)

    db.commit()

print("✅ 40 stagiaires fictifs créés avec historique de 60 jours !")
db.close()