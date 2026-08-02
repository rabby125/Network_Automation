"""
models/admin.py
-----------------
Admin টেবিলের SQLAlchemy Model (Login System এর জন্য)
"""

from sqlalchemy import Column, Integer, String, DateTime, Enum
from sqlalchemy.sql import func
from app.database.database import Base


class Admin(Base):
    __tablename__ = "admin"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    username = Column(String(50), unique=True, nullable=False, index=True)

    password = Column(String(255), nullable=False)

    role = Column(
        Enum("read", "write", "super_admin", name="admin_role"),
        nullable=False,
        default="read",
    )

    created_at = Column(DateTime(timezone=False), server_default=func.now())

    def __repr__(self):
        return f"<Admin id={self.id} username={self.username}>"