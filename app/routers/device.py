"""
routers/device.py
-------------------
Dashboard এর "Create Device" ফর্ম থেকে নতুন ডিভাইস যোগ করার API।
এতদিন phpMyAdmin দিয়ে করতে হচ্ছিল, এখন থেকে Dashboard থেকেই করা যাবে।
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.device import Device
from app.services.dependencies import (
    require_read,
    require_write,
    require_super,
)
from app.services import ssh_service
from app.services.crypto_service import encrypt_secret

router = APIRouter(prefix="/api/device", tags=["Device"])


class DeviceCreateRequest(BaseModel):
    group_name: str
    zone: str
    vendor: str
    hostname: str
    ip_address: str
    ssh_username: str
    ssh_password: str
    ssh_port: int = 22


@router.post("/create")
def create_device(
    payload: DeviceCreateRequest,
    db: Session = Depends(get_db),
    admin=Depends(require_super),
):
    """নতুন ডিভাইস তৈরি করে devices টেবিলে যোগ করে"""

    existing = (
        db.query(Device)
        .filter(Device.ip_address == payload.ip_address, Device.ssh_port == payload.ssh_port)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"This IP ({payload.ip_address}) and Port already belong to '{existing.hostname}'.",
        )

    device = Device(
        group_name=payload.group_name,
        zone=payload.zone,
        vendor=payload.vendor,
        hostname=payload.hostname,
        ip_address=payload.ip_address,
        ssh_username=payload.ssh_username,
        ssh_password=encrypt_secret(payload.ssh_password),  # ⚠️ এখন এনক্রিপ্ট করে সেভ হয়
        ssh_port=payload.ssh_port,
    )
    db.add(device)
    db.commit()
    db.refresh(device)

    ssh_service.log_activity(
        db,
        f"New device '{device.hostname}' ({device.group_name}/{device.zone}) was added",
        admin_username=admin.get("sub"),
        device_hostname=device.hostname,
        action="create_device",
        result="success",
    )

    return {"success": True, "device_id": device.id}

# =====================================================
# Device List API
# =====================================================

@router.get("/list")
def list_devices(
    db: Session = Depends(get_db),
    admin=Depends(require_read),
):
    """
    Dashboard-এ সব Device দেখাবে।
    """

    devices = (
        db.query(Device)
        .order_by(Device.group_name, Device.zone, Device.hostname)
        .all()
    )

    return {
        "devices": [
            {
                "id": d.id,
                "group_name": d.group_name,
                "zone": d.zone,
                "vendor": d.vendor,
                "hostname": d.hostname,
                "ip_address": d.ip_address,
                "ssh_port": d.ssh_port,
                "status": d.status,
            }
            for d in devices
        ]
    }


# =====================================================
# Device Delete API
# =====================================================

class DeviceDeleteRequest(BaseModel):
    device_id: int


@router.post("/delete")
def delete_device(
    payload: DeviceDeleteRequest,
    db: Session = Depends(get_db),
    admin=Depends(require_super),
):
    """
    ডিভাইসটা শুধু আমাদের ডাটাবেজ (devices টেবিল) থেকে মুছে ফেলে -- ডিভাইসের
    ভিতরে (রাউটার/সুইচে) কোনো SSH কানেকশন যায় না, ওখানে থাকা user গুলো
    device এ যেভাবে আছে সেভাবেই থাকবে, শুধু আমাদের সিস্টেমের ট্র্যাকিং থেকে
    বাদ যাবে। তাই এটা সম্পূর্ণ safe।
    """

    device = (
        db.query(Device)
        .filter(Device.id == payload.device_id)
        .first()
    )

    if not device:
        raise HTTPException(status_code=404, detail="Device not found.")

    hostname = device.hostname
    group_zone = f"{device.group_name}/{device.zone}"

    db.delete(device)
    db.commit()

    ssh_service.log_activity(
        db,
        f"Device '{hostname}' ({group_zone}) removed from database "
        f"(tracking only, no change made on the device)",
        admin_username=admin.get("sub"),
        device_hostname=hostname,
        action="delete_device",
        result="success",
    )

    return {"success": True, "detail": f"Device '{hostname}' has been removed."}


# =====================================================
# Device Update (Edit) API -- শুধু super_admin
# =====================================================

class DeviceUpdateRequest(BaseModel):
    device_id: int
    group_name: str
    zone: str
    vendor: str
    hostname: str
    ip_address: str
    ssh_username: str
    ssh_password: str | None = None   # leave empty to keep old password unchanged
    ssh_port: int = 22


@router.post("/update")
def update_device(
    payload: DeviceUpdateRequest,
    db: Session = Depends(get_db),
    admin=Depends(require_super),
):
    """
    ডাটাবেজে থাকা ডিভাইসের তথ্য এডিট করে। এটাও শুধু আমাদের ডাটাবেজে
    পরিবর্তন করে -- ডিভাইসে (রাউটার/সুইচে) কোনো SSH কানেকশন যায় না,
    তাই delete_device এর মতোই সম্পূর্ণ safe।
    """

    device = (
        db.query(Device)
        .filter(Device.id == payload.device_id)
        .first()
    )

    if not device:
        raise HTTPException(status_code=404, detail="Device not found.")

    # একই IP+Port এ অন্য কোনো ডিভাইস আগে থেকে আছে কিনা (নিজেকে বাদ দিয়ে)
    duplicate = (
        db.query(Device)
        .filter(
            Device.ip_address == payload.ip_address,
            Device.ssh_port == payload.ssh_port,
            Device.id != payload.device_id,
        )
        .first()
    )
    if duplicate:
        raise HTTPException(
            status_code=400,
            detail=f"This IP ({payload.ip_address}) and Port already belong to '{duplicate.hostname}'.",
        )

    device.group_name = payload.group_name
    device.zone = payload.zone
    device.vendor = payload.vendor
    device.hostname = payload.hostname
    device.ip_address = payload.ip_address
    device.ssh_username = payload.ssh_username
    device.ssh_port = payload.ssh_port

    if payload.ssh_password:
        device.ssh_password = encrypt_secret(payload.ssh_password)

    db.commit()

    ssh_service.log_activity(
        db,
        f"Device '{device.hostname}' ({device.group_name}/{device.zone}) details were edited",
        admin_username=admin.get("sub"),
        device_hostname=device.hostname,
        action="update_device",
        result="success",
    )

    return {"success": True, "detail": f"Device '{device.hostname}' has been updated."}