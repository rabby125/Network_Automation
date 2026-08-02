"""
models/activity_log.py
------------------------
ফিক্স নোট: আগে শুধু 'message' (একটা টেক্সট লাইন) সেভ হতো, কে করেছে/কোন
ডিভাইসে/কী action/ফলাফল কী -- এসব আলাদা করে বের করা যেত না। এখন structured
fields যোগ করা হলো যাতে পরে filter/report করা সহজ হয়।
"""

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.database.database import Base


class ActivityLog(Base):
    __tablename__ = "activity_log"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    message = Column(String(255), nullable=False)          # মানুষের পড়ার জন্য সামারি লাইন
    admin_username = Column(String(50), nullable=True)      # কোন Admin এই কাজ করেছে
    device_hostname = Column(String(100), nullable=True)    # কোন ডিভাইসে করা হয়েছে
    action = Column(String(30), nullable=True)              # create / edit / delete / verify / search
    result = Column(String(30), nullable=True)               # success / verify_failed / found / not_found

    created_at = Column(DateTime(timezone=False), server_default=func.now())
