from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv
load_dotenv(BACKEND_ROOT / ".env")

"""
seed_admins.py — Create test accounts for each role
====================================================

This script creates admin accounts for all four roles with test credentials.
Safe to run multiple times (skips existing users).
"""
from database import SessionLocal, Admin, Department
from auth import hash_password, AdminRole

db = SessionLocal()

# Test accounts with easy passwords for testing
TEST_ACCOUNTS = [
    {
        "username": "dfri",
        "password": "dfri1234",
        "role": AdminRole.DFRI,
        "department_id": None,
        "label": "Directeur IT (accès total)"
    },
    {
        "username": "directeur",
        "password": "dir1234",
        "role": AdminRole.DIRECTEUR,
        "department_id": None,
        "label": "Directeur (lecture seule)"
    },
    {
        "username": "chef_cardiologie",
        "password": "chef1234",
        "role": AdminRole.CHEF_SERVICE,
        "department_id": None,  # Will be assigned below
        "label": "Chef de Service - Cardiologie"
    },
    {
        "username": "secretaire",
        "password": "sec1234",
        "role": AdminRole.SECRETAIRE,
        "department_id": None,
        "label": "Secrétaire (vue globale)"
    }
]

print("🔐 Initializing test admin accounts...\n")

# Get first department for Chef de Service
depts = db.query(Department).all()
if depts:
    dept_id = depts[0].id
    dept_name = depts[0].name
else:
    print("⚠️  No departments found. Run seed_departments.py first.")
    db.close()
    exit(1)

created_count = 0
skipped_count = 0

for acc in TEST_ACCOUNTS:
    # Skip if already exists
    existing = db.query(Admin).filter(Admin.username == acc["username"]).first()
    if existing:
        print(f"⏭️  '{acc['username']}' already exists — skipping")
        skipped_count += 1
        continue
    
    # Assign department for Chef de Service
    if acc["role"] == AdminRole.CHEF_SERVICE:
        acc["department_id"] = dept_id
    
    new_admin = Admin(
        username=acc["username"],
        hashed_password=hash_password(acc["password"]),
        role=acc["role"].value,
        department_id=acc["department_id"]
    )
    
    db.add(new_admin)
    db.commit()
    
    dept_label = f" ({dept_name})" if acc["department_id"] else ""
    print(f"✅ Created: {acc['username']:<25} | {acc['label']}{dept_label}")
    print(f"   Password: {acc['password']}")
    print()
    
    created_count += 1

print(f"\n📊 Summary:")
print(f"   Created: {created_count}")
print(f"   Skipped: {skipped_count}")
print(f"\n🎯 Test Credentials:")
print(f"   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print(f"   DFRI:")
print(f"      Username: dfri")
print(f"      Password: dfri1234")
print(f"      Access: Tout (lecture + écriture + audit)")
print(f"\n   DIRECTEUR:")
print(f"      Username: directeur")
print(f"      Password: dir1234")
print(f"      Access: Tout (lecture seule) + Journal d'audit")
print(f"\n   CHEF DE SERVICE ({dept_name}):")
print(f"      Username: chef_cardiologie")
print(f"      Password: chef1234")
print(f"      Access: Son département seulement + Administration (interns)")
print(f"\n   SECRÉTAIRE:")
print(f"      Username: secretaire")
print(f"      Password: sec1234")
print(f"      Access: Vue Globale + Alertes + Export Excel")
print(f"   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

db.close()
print("\n✨ Done!")
