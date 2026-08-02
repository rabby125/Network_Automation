"""
create_admin.py
-----------------
প্রথমবার প্রজেক্ট সেটআপ করার সময় এই script রান করে
একটা admin user তৈরি করে নিবেন।

চালানোর নিয়ম (project root থেকে):
    python create_admin.py
"""

from app.database.database import SessionLocal, engine, Base
from app.models.admin import Admin
from app.models.device import Device  # noqa: F401  (Base.metadata তে যোগ হওয়ার জন্য দরকার)
from app.services.auth_service import hash_password

# টেবিল না থাকলে তৈরি করে দিবে (SQL ফাইল দিয়ে আগেই বানিয়ে থাকলে সমস্যা নেই)
Base.metadata.create_all(bind=engine)

db = SessionLocal()

username = input("Admin Username দিন: ").strip()
password = input("Admin Password দিন: ").strip()

existing = db.query(Admin).filter(Admin.username == username).first()
if existing:
    print(f"❌ '{username}' নামে Admin আগে থেকেই আছে।")
else:
    new_admin = Admin(username=username, password=hash_password(password))
    db.add(new_admin)
    db.commit()
    print(f"✅ Admin '{username}' সফলভাবে তৈরি হয়েছে!")

db.close()
