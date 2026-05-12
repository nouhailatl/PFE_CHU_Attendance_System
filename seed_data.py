"""
seed_data.py — additive top-up to 150 interns.
================================================
Safe to run against a live Neon DB with existing data.

What it does:
  1. Counts current interns in the DB.
  2. If already >= 150, exits without touching anything.
  3. Otherwise seeds (150 - current_count) NEW interns only,
     with balanced behavioral profiles drawn from the remaining quota.
  4. Never touches existing interns or their attendance records.

Profile target distribution (applied only to the NEW interns added):
  regulier  40%
  retard    25%
  risque    25%
  absent    10%
"""
from dotenv import load_dotenv
load_dotenv()

from database import SessionLocal, Intern, DailyStatus, Department
from datetime import datetime, timedelta, time as dtime
import uuid
import random

# ── Reproducibility ───────────────────────────────────────────────────────────
# Different seed from original run so new UUIDs / names don't collide.
random.seed(99)

TARGET_TOTAL = 150

db = SessionLocal()

# ── How many do we still need? ────────────────────────────────────────────────
current_count = db.query(Intern).count()
to_add = TARGET_TOTAL - current_count

if to_add <= 0:
    print(f"✅ Already {current_count} interns in DB — nothing to add.")
    db.close()
    exit()

print(f"📊 Current interns : {current_count}")
print(f"🎯 Target          : {TARGET_TOTAL}")
print(f"➕ Will add        : {to_add} new interns\n")

# ── Departments ───────────────────────────────────────────────────────────────
departements = [d.id for d in db.query(Department).all()]
if not departements:
    print("❌ No departments found! Run seed_departments.py first.")
    db.close()
    exit()

# ── Name pool ─────────────────────────────────────────────────────────────────
PRENOMS_M = [
    "Ahmed", "Youssef", "Omar", "Karim", "Amine", "Mehdi", "Hamza", "Tarik",
    "Bilal", "Khalid", "Rachid", "Nabil", "Jawad", "Adil", "Fouad", "Saad",
    "Mouad", "Ilyas", "Soufiane", "Ayoub", "Zakaria", "Reda", "Hicham",
    "Ismail", "Othmane", "Badr", "Marouane", "Driss", "Younes", "Faisal",
    "Anas", "Nassim", "Tariq", "Walid", "Ziad", "Sami", "Ryad", "Ayman",
]
PRENOMS_F = [
    "Sara", "Nadia", "Hiba", "Leila", "Zineb", "Salma", "Rim", "Dounia",
    "Hajar", "Fatima", "Meryem", "Imane", "Samira", "Widad", "Houda",
    "Nawal", "Ghita", "Loubna", "Asma", "Kenza", "Hafsa", "Siham",
    "Chaimae", "Ikram", "Boutaina", "Nour", "Layla", "Rania", "Amina",
    "Yasmine", "Manal", "Ibtissam", "Oumaima", "Soukaina", "Basma",
]
NOMS = [
    "Benali", "Idrissi", "Chaoui", "Tazi", "Filali", "Alami", "Bennani",
    "Chraibi", "Fassi", "Berrada", "Lahlou", "Kettani", "Ghazi", "Sqalli",
    "Ouazzani", "Mernissi", "Zemmouri", "Naciri", "Benhaddou", "Rahali",
    "Senhaji", "Tahiri", "Bargach", "Bensouda", "Lazrak", "Ouali",
    "Benmoussa", "Lamrani", "Skalli", "Benkirane", "Sefrioui", "Alaoui",
    "Bennis", "Zaki", "Rhazi", "Boutaleb", "Bouzid", "Hafidi", "Maarouf",
    "Benouda", "Sekkat", "Raissouni", "Tahir", "Benomar", "Benchekroun",
    "Moussaoui", "Benabdallah", "Laraichi", "Berraho", "Zouiten",
]


def gen_name():
    if random.random() < 0.5:
        return random.choice(PRENOMS_M), random.choice(NOMS)
    return random.choice(PRENOMS_F), random.choice(NOMS)


# ── Profile distribution for the new batch ────────────────────────────────────
def build_profile_list(n: int) -> list:
    """
    Build a shuffled list of n profile strings respecting target ratios.
    Rounding error is absorbed into 'regulier'.
    """
    counts = {
        "regulier": max(1, round(n * 0.40)),
        "retard":   max(1, round(n * 0.25)),
        "risque":   max(1, round(n * 0.25)),
        "absent":   max(1, round(n * 0.10)),
    }
    diff = n - sum(counts.values())
    counts["regulier"] += diff      # diff can be negative — that's fine

    profiles = []
    for profil, cnt in counts.items():
        profiles.extend([profil] * max(0, cnt))
    random.shuffle(profiles)
    return profiles


# ── Behavioral params ─────────────────────────────────────────────────────────
PRESENCE_P = {
    "regulier": 0.96,
    "retard":   0.88,
    "risque":   0.65,
    "absent":   0.40,
}

ARRIVAL_PARAMS = {          # (mean_hour, mean_minute, std_minutes)
    "regulier": (8, 38,  6),
    "retard":   (9, 15, 20),
    "risque":   (9,  0, 35),
    "absent":   (9,  5, 15),
}

DEPARTURE_PARAMS = {        # (mean_hour, std_minutes)
    "regulier": (16, 15),
    "retard":   (15, 20),
    "risque":   (15, 40),
    "absent":   (15, 25),
}

DEBUT = datetime.now() - timedelta(days=90)


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def gen_arrival(profil: str, jour: datetime) -> datetime:
    mh, mm, std = ARRIVAL_PARAMS[profil]
    total = clamp(mh * 60 + mm + random.gauss(0, std), 7 * 60, 12 * 60)
    h, m  = divmod(int(total), 60)
    return jour.replace(hour=h, minute=m, second=random.randint(0, 59),
                        microsecond=0)


def gen_departure(profil: str, arrival: datetime) -> datetime:
    mh, std = DEPARTURE_PARAMS[profil]
    total   = clamp(mh * 60 + random.gauss(0, std), 13 * 60, 19 * 60)
    h, m    = divmod(int(total), 60)
    dep     = arrival.replace(hour=h, minute=m, second=random.randint(0, 59),
                               microsecond=0)
    if (dep - arrival).total_seconds() < 2 * 3600:
        dep = arrival + timedelta(hours=2, minutes=random.randint(0, 30))
    return dep


def resolve_checkin_status(arrival: datetime) -> str:
    t = arrival.time()
    if t <= dtime(9, 35):  return "on_time"
    if t <= dtime(10, 10): return "late"
    return "missed_checkin"


def resolve_checkout_status(departure: datetime) -> str:
    t = departure.time()
    if t < dtime(15, 0):   return "early_checkout"
    if t <= dtime(17, 0):  return "completed"
    return "missed_checkout"


ATTENTION = {"missed_checkin", "early_checkout", "missed_checkout"}

# ── Seed loop ─────────────────────────────────────────────────────────────────
profiles      = build_profile_list(to_add)
added         = 0
records       = 0
profile_tally = {p: 0 for p in ["regulier", "retard", "risque", "absent"]}

for profil in profiles:
    prenom, nom = gen_name()
    intern_id   = str(uuid.uuid4())
    dept_id     = random.choice(departements)

    db.add(Intern(
        id=intern_id,
        first_name=prenom,
        last_name=nom,
        department_id=dept_id,
    ))
    db.flush()      # persist intern row before FK-referencing attendance rows

    for i in range(90):
        jour = DEBUT + timedelta(days=i)
        if jour.weekday() >= 5:     # skip weekends
            continue

        present = random.random() < PRESENCE_P[profil]

        if not present:
            db.add(DailyStatus(
                id=str(uuid.uuid4()),
                intern_id=intern_id,
                date=jour.replace(hour=0, minute=0, second=0, microsecond=0),
                arrival_time=None,
                departure_time=None,
                status="absent",
                checkin_status=None,
                checkout_status=None,
                work_duration=0.0,
                needs_attention=True,
            ))
            records += 1
            continue

        arrival   = gen_arrival(profil, jour)
        departure = gen_departure(profil, arrival)
        duration  = round((departure - arrival).total_seconds() / 3600, 2)
        ci        = resolve_checkin_status(arrival)
        co        = resolve_checkout_status(departure)
        status    = ci if ci in ATTENTION else (co if co in ATTENTION else ci)

        db.add(DailyStatus(
            id=str(uuid.uuid4()),
            intern_id=intern_id,
            date=jour.replace(hour=0, minute=0, second=0, microsecond=0),
            arrival_time=arrival,
            departure_time=departure,
            status=status,
            checkin_status=ci,
            checkout_status=co,
            work_duration=duration,
            needs_attention=(status in ATTENTION),
        ))
        records += 1

    db.commit()
    added += 1
    profile_tally[profil] += 1

    if added % 25 == 0:
        print(f"  → {added}/{to_add} nouveaux stagiaires ajoutés…")

db.close()

print(f"\n✅ Done.")
print(f"   {added} new interns added  ({records} attendance rows)")
print(f"   Total interns now : {current_count + added}")
print(f"\n   Profile breakdown of new batch:")
for p, c in profile_tally.items():
    print(f"     {p:<12} {c:>4}")