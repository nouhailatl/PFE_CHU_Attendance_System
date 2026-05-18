"""
seed_all_chefs.py — Connection-safe generation for ALL department chiefs
=============================================================================
"""
import re
from dotenv import load_dotenv
load_dotenv()

from database import SessionLocal, Admin, Department
from auth import hash_password, AdminRole

def slugify(text: str) -> str:
    """Helper to convert department names into clean username segments."""
    text = text.lower()
    text = re.sub(r'[éèêë]', 'e', text)
    text = re.sub(r'[àâä]', 'a', text)
    text = re.sub(r'[îï]', 'i', text)
    text = re.sub(r'[ôö]', 'o', text)
    text = re.sub(r'[ûüù]', 'u', text)
    text = re.sub(r'[ç]', 'c', text)
    text = re.sub(r'[^a-z0-9\s_-]', '', text)
    text = re.sub(r'[\s_-]+', '_', text)
    return text.strip('_')

db = SessionLocal()

print("🏨 Fetching all departments and existing admins from the database...")
try:
    departments = db.query(Department).all()
    
    # FETCH ALL EXISTING USERNAMES ONCE AT THE START (Prevents connection drops)
    existing_admins = db.query(Admin.username).all()
    existing_usernames_db = {user[0] for user in existing_admins}
    
except Exception as e:
    print(f"❌ Failed to fetch initial data: {e}")
    db.close()
    exit(1)

if not departments:
    print("⚠️ No departments found.")
    db.close()
    exit(1)

print(f"found {len(departments)} departments. Processing locally...\n")

# Track usernames we intend to add during THIS script execution loop
seen_in_batch = set()

created_count = 0
skipped_count = 0

for dept in departments:
    base_slug = slugify(dept.name)
    base_username = f"chef_{base_slug}"
    username = base_username
    
    # 1. If the exact base username already exists in the DB, skip it entirely
    if base_username in existing_usernames_db:
        print(f"⏭️  '{base_username}' already exists in DB — skipping")
        skipped_count += 1
        continue

    # 2. Handle duplicates inside the loop (e.g., your two Réanimation Urgence B variants)
    counter = 1
    while username in seen_in_batch or username in existing_usernames_db:
        counter += 1
        username = f"{base_username}_{counter}"

    password = f"pass_{base_slug}" 
    role_value = getattr(AdminRole.CHEF_SERVICE, 'value', 'chef_service')

    # 3. Add to tracking set and session memory
    seen_in_batch.add(username)
    
    new_chef = Admin(
        username=username,
        hashed_password=hash_password(password),
        role=role_value, 
        department_id=dept.id
    )
    
    db.add(new_chef)
    created_count += 1
    
    collision_flag = " ⚠️ (Renamed due to duplicate text)" if counter > 1 else ""
    print(f"✅ Ready: {username:<35} | Dept: {dept.name}{collision_flag}")

# 4. Single secure commit at the end
if created_count > 0:
    print("\n💾 Committing batch changes to cloud database...")
    try:
        db.commit()
        print(f"\n📊 Generation Summary:")
        print(f"   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"   Total Accounts Created: {created_count}")
        print(f"   Total Accounts Skipped: {skipped_count}")
        print(f"   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    except Exception as e:
        db.rollback()
        print(f"❌ Commit failed: {e}")
    finally:
        db.close()
else:
    print("\nℹ️ No new accounts needed to be created.")
    db.close()

print("\n✨ Done!")