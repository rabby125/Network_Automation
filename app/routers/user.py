"""
routers/user.py
-----------------
Create / Edit / Delete / Verify API — ডিভাইসের উপর সরাসরি অ্যাকশন নেয়।

ফিক্স নোট: এখন create/edit/delete নিজেই server-side এ duplicate check এবং
verify করে, ফলাফলে 'verified' field থাকে যেটা সত্যিকারের প্রমাণ (frontend
এর উপর নির্ভর করে না)।

🧪 Test Mode / Dry Run: payload.dry_run = True হলে ডিভাইসে SSH কানেক্ট হয়ে
duplicate/existence check হবে (তাই কানেকশন আসলেই কাজ করে কিনা সেটাও বোঝা
যাবে), কিন্তু আসল create/edit/delete কমান্ড ডিভাইসে পাঠানো হবে না -- ডিভাইসে
কোনো পরিবর্তন হবে না।
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.device import Device
from app.automation.ssh import SSHConnectionError
from app.services.dependencies import (
    require_read,
    require_write,
)
from app.services import ssh_service
from app.services.ssh_service import DeviceActionError

router = APIRouter(prefix="/api/user", tags=["User CRUD"])


# ---------------- Schemas ----------------
class UserActionRequest(BaseModel):
    device_id: int
    username: str
    password: str | None = None
    dry_run: bool = False  # 🧪 Test Mode: if True, no real change made on device
    group: str = "full"    # only applies to MikroTik Create (read/write/full)
    address: str | None = None  # only applies to MikroTik Create, Allowed Address (optional)


def _get_device_or_404(db: Session, device_id: int) -> Device:
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found.")
    return device


# ---------------- Create ----------------
@router.post("/create")
def create_user(
    payload: UserActionRequest,
    db: Session = Depends(get_db),
    admin=Depends(require_write),
):
    device = _get_device_or_404(db, payload.device_id)
    if not payload.password:
        raise HTTPException(status_code=400, detail="Password is required.")

    try:
        result = ssh_service.create_user_on_device(
            device,
            payload.username,
            payload.password,
            dry_run=payload.dry_run,
            group=payload.group,
            address=payload.address,
        )
    except DeviceActionError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except SSHConnectionError as e:
        raise HTTPException(status_code=502, detail=str(e))

    if result["dry_run"]:
        message = (
            f"🧪 [TEST MODE] User '{payload.username}' could be created on '{device.hostname}' "
            f"(no change made on device)"
        )
        log_result = "dry_run"
    else:
        message = (
            f"User '{payload.username}' was created on '{device.hostname}' "
            + ("(Verified ✅)" if result["verified"] else "(⚠️ Verify Failed)")
        )
        log_result = "success" if result["verified"] else "verify_failed"

    ssh_service.log_activity(
        db,
        message,
        admin_username=admin.get("sub"),
        device_hostname=device.hostname,
        action="create",
        result=log_result,
    )
    return {"success": True, **result}


# ---------------- Edit ----------------
@router.post("/edit")
def edit_user(
    payload: UserActionRequest,
    db: Session = Depends(get_db),
    admin=Depends(require_write),
):
    device = _get_device_or_404(db, payload.device_id)
    if not payload.password:
        raise HTTPException(status_code=400, detail="New Password is required.")

    try:
        result = ssh_service.edit_user_on_device(
            device,
            payload.username,
            payload.password,
            dry_run=payload.dry_run,
            group=payload.group,
            address=payload.address,
        )
    except DeviceActionError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except SSHConnectionError as e:
        raise HTTPException(status_code=502, detail=str(e))

    if result["dry_run"]:
        message = (
            f"🧪 [TEST MODE] User '{payload.username}' could be edited on '{device.hostname}' "
            f"(no change made on device)"
        )
        log_result = "dry_run"
    else:
        message = (
            f"User '{payload.username}' was edited on '{device.hostname}' "
            + ("(Verified ✅)" if result["verified"] else "(⚠️ Verify Failed)")
        )
        log_result = "success" if result["verified"] else "verify_failed"

    ssh_service.log_activity(
        db,
        message,
        admin_username=admin.get("sub"),
        device_hostname=device.hostname,
        action="edit",
        result=log_result,
    )
    return {"success": True, **result}


# ---------------- Delete ----------------
@router.post("/delete")
def delete_user(
    payload: UserActionRequest,
    db: Session = Depends(get_db),
    admin=Depends(require_write),
):
    device = _get_device_or_404(db, payload.device_id)

    try:
        result = ssh_service.delete_user_on_device(
            device, payload.username, dry_run=payload.dry_run
        )
    except DeviceActionError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except SSHConnectionError as e:
        raise HTTPException(status_code=502, detail=str(e))

    if result["dry_run"]:
        message = (
            f"🧪 [TEST MODE] User '{payload.username}' could be deleted from '{device.hostname}' "
            f"(no change made on device)"
        )
        log_result = "dry_run"
    else:
        message = (
            f"User '{payload.username}' was deleted from '{device.hostname}' "
            + ("(Verified ✅)" if result["verified"] else "(⚠️ Verify Failed)")
        )
        log_result = "success" if result["verified"] else "verify_failed"

    ssh_service.log_activity(
        db,
        message,
        admin_username=admin.get("sub"),
        device_hostname=device.hostname,
        action="delete",
        result=log_result,
    )
    return {"success": True, **result}


# ---------------- Verify (ম্যানুয়ালি আবার চেক করার জন্য, ঐচ্ছিক) ----------------
@router.post("/verify")
def verify_user(
    payload: UserActionRequest,
    db: Session = Depends(get_db),
    admin=Depends(require_read),
):
    device = _get_device_or_404(db, payload.device_id)

    try:
        exists, raw_output = ssh_service.verify_user_on_device(
            device, payload.username
        )
    except SSHConnectionError as e:
        raise HTTPException(status_code=502, detail=str(e))

    ssh_service.log_activity(
        db,
        f"'{payload.username}' manually verified ({device.hostname}) -> "
        + ("Found" if exists else "Not found"),
        admin_username=admin.get("sub"),
        device_hostname=device.hostname,
        action="verify",
        result="found" if exists else "not_found",
    )
    return {"success": True, "exists": exists, "raw_output": raw_output}