"""
database.py
------------
এই ফাইলটা MySQL এর সাথে কানেকশন তৈরি করে এবং
SQLAlchemy Session সবার জন্য সরবরাহ করে।
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# .env ফাইল থেকে config লোড করা হচ্ছে
load_dotenv()

DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "network_automation")

# MySQL connection URL (pymysql driver ব্যবহার করা হচ্ছে)
DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# Engine তৈরি
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,   # কানেকশন মরে গেলে auto reconnect করবে
    pool_recycle=3600,
)

# Session তৈরি করার factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# সব Model এর Base Class
Base = declarative_base()


def get_db():
    """
    FastAPI Dependency হিসেবে ব্যবহার হবে।
    প্রতিটা রিকোয়েস্টে একটা নতুন session দিবে, শেষে close করে দিবে।

    routers এর মধ্যে এভাবে ব্যবহার করবেন:

        from fastapi import Depends
        from app.database.database import get_db

        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
