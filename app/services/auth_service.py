"""
services/auth_service.py
--------------------------
Password hashing + JWT token তৈরি ও যাচাই করার জন্য সব ফাংশন এখানে।
"""

import os
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError(
        "❌ SECRET_KEY .env ফাইলে পাওয়া যায়নি! আগে এখানে একটা hardcoded fallback "
        "secret ছিল যেটা নিরাপদ ছিল না -- এখন সেটা বাদ দেওয়া হয়েছে।\n"
        "নিচের কমান্ড দিয়ে একটা র‍্যান্ডম secret বানিয়ে .env ফাইলে SECRET_KEY=... বসান:\n\n"
        "    python -c \"import secrets; print(secrets.token_hex(32))\"\n"
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Password কে bcrypt দিয়ে hash করে"""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Login এর সময় password মিলিয়ে দেখে"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Login সফল হলে JWT token তৈরি করে"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """Token যাচাই করে, ভুল/মেয়াদ শেষ হলে None রিটার্ন করে"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
