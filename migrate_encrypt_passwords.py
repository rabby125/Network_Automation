"""
migrate_encrypt_passwords.py
-------------------------------
আপনি যদি আগে phpMyAdmin দিয়ে devices টেবিলে সরাসরি plain-text
ssh_password বসিয়ে থাকেন, তাহলে এই script একবার চালালে সবগুলো
এনক্রিপ্ট হয়ে যাবে।

⚠️ চালানোর আগে অবশ্যই .env এ FERNET_KEY বসিয়ে নিন (README দেখুন)।
⚠️ এই script একবারই চালাবেন। দ্বিতীয়বার চালালে আগে থেকে এনক্রিপ্টেড
ডাটা আবার এনক্রিপ্ট হয়ে ভুল হয়ে যাবে -- তাই নিচে একটা সেফটি চেক আছে।

চালানোর নিয়ম (project root থেকে):
    python migrate_encrypt_passwords.py
"""

from app.database.database import SessionLocal
from app.models.device import Device
from app.services.crypto_service import encrypt_secret, decrypt_secret, _fernet
from cryptography.fernet import InvalidToken

db = SessionLocal()
devices = db.query(Device).all()

updated = 0
skipped = 0

for device in devices:
    # সেফটি চেক: এটা কি আগে থেকেই এনক্রিপ্টেড? (valid Fernet token কিনা টেস্ট করে দেখি)
    try:
        _fernet.decrypt(device.ssh_password.encode())
        skipped += 1
        print(f"⏭  '{device.hostname}' -> আগে থেকেই এনক্রিপ্টেড, বাদ দেওয়া হলো")
        continue
    except (InvalidToken, Exception):
        pass  # এনক্রিপ্টেড না, তাহলে এটা plain text -> এনক্রিপ্ট করব

    plain_password = device.ssh_password
    device.ssh_password = encrypt_secret(plain_password)
    updated += 1
    print(f"✅ '{device.hostname}' -> Password এনক্রিপ্ট করা হলো")

db.commit()
db.close()

print(f"\nমোট {updated}টা ডিভাইসের password এনক্রিপ্ট করা হয়েছে, {skipped}টা আগে থেকেই ঠিক ছিল।")
