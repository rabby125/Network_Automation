"""
services/crypto_service.py
----------------------------
devices.ssh_password এখন আর plain text এ সেভ হয় না -- এই ফাইল দিয়ে
এনক্রিপ্ট/ডিক্রিপ্ট করা হয় (Fernet symmetric encryption ব্যবহার করে,
'cryptography' লাইব্রেরির অংশ)।

⚠️ গুরুত্বপূর্ণ: FERNET_KEY টা .env এ থাকা লাগবে, নাহলে অ্যাপ চালু হবে না।
Key তৈরি করার কমান্ড (README এও লেখা আছে):

    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

import os
from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv

load_dotenv()

FERNET_KEY = os.getenv("FERNET_KEY")

if not FERNET_KEY:
    raise RuntimeError(
        "❌ FERNET_KEY .env ফাইলে পাওয়া যায়নি! এটা ছাড়া SSH password এনক্রিপ্ট/ডিক্রিপ্ট করা যাবে না।\n"
        "নিচের কমান্ড দিয়ে একটা key বানিয়ে .env ফাইলে FERNET_KEY=... হিসেবে বসান:\n\n"
        "    python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"\n"
    )

_fernet = Fernet(FERNET_KEY.encode())


def encrypt_secret(plain_text: str) -> str:
    """SSH Password/Username সেভ করার আগে এনক্রিপ্ট করে"""
    return _fernet.encrypt(plain_text.encode()).decode()


def decrypt_secret(encrypted_text: str) -> str:
    """ডাটাবেজ থেকে পড়ার সময় ডিক্রিপ্ট করে আসল password ফেরত দেয়"""
    try:
        return _fernet.decrypt(encrypted_text.encode()).decode()
    except InvalidToken:
        # পুরনো ডাটা যদি এখনো plain text এ থাকে (migration না করলে),
        # সেক্ষেত্রে ভুল না দিয়ে raw value ফেরত দিচ্ছি -- migration script
        # চালিয়ে নেওয়ার পর এই fallback আর লাগবে না।
        return encrypted_text
