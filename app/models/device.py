"""
models/device.py
------------------
Devices টেবিলের SQLAlchemy Model
"""

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.database.database import Base


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    group_name = Column(String(100), nullable=False, index=True)
    zone = Column(String(100), nullable=False, index=True)
    vendor = Column(String(50), nullable=False, index=True)  # MikroTik / Cisco / Huawei ...
    hostname = Column(String(100), nullable=False)
    ip_address = Column(String(45), nullable=False)
    ssh_username = Column(String(100), nullable=False)
    ssh_password = Column(String(255), nullable=False)
    ssh_port = Column(Integer, nullable=False, default=22)
    status = Column(String(20), default="Unknown")

    created_at = Column(DateTime(timezone=False), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=False), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self):
        return f"<Device id={self.id} hostname={self.hostname} vendor={self.vendor}>"
