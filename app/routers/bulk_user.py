"""
routers/bulk_user.py
-----------------------
Search Filters (Group/Zone/Device) অনুযায়ী একসাথে একাধিক ডিভাইসে
User Create / Remove করার জন্য নতুন, আলাদা API।

⚠️ Design Note:
এই ফাইলটা সম্পূর্ণ নতুন এবং isolated -- existing single-device
create/edit/delete (app/routers/user.py) বা vendor automation
(app/automation/*.py) এর কোনো কোড এখানে পরিবর্তন করা হয়নি, শুধু
app/services/ssh_service.py এর existing ফাংশনগুলো (যেগুলো নিজে থেকেই
duplicate check + action + verify করে) reuse করা হয়েছে।

প্রতিটা ডিভাইসে একটার পর একটা (sequential) SSH কানেকশন যায়, একটা
ডিভাইস ফেইল করলেও বাকিগুলো চলতে থাকে -- প্রতিটার আলাদা ফলাফল রিটার্ন হয়।

🧪 Test Mode / Dry Run: payload.dry_run = True হলে প্রতিটা ডিভাইসে SSH
কানেক্ট + existence check হবে, কিন্তু আসল create/delete কমান্ড কোনো
ডিভাইসেই পাঠানো হবে না -- কোনো ডিভাইসে পরিবর্তন হবে না।
"""

from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.device import Device
from app.automation.ssh import SSHConnectionError
from app.services.dependencies import require_write
from app.services import ssh_service
from app.services.ssh_service import DeviceActionError

router = APIRouter(prefix="/api/bulk-user", tags=["Bulk User"])


# ==========================================================
# Request Schema
# ==========================================================

class BulkUserRequest(BaseModel):
    groups: Optional[List[str]] = []
    zones: Optional[List[str]] = []
    devices: Optional[List[str]] = []   # hostname list (same as search filter)
    username: str
    password: Optional[str] = None      # only needed for create
    dry_run: bool = False               # 🧪 Test Mode: if True, no device will be changed
    group: str = "full"                 # only applies to MikroTik Create (read/write/full)
    address: Optional[str] = None       # only applies to MikroTik Create (optional)


def _filtered_devices(db: Session, payload: BulkUserRequest) -> List[Device]:
    query = db.query(Device)

    if payload.groups:
        query = query.filter(Device.group_name.in_(payload.groups))

    if payload.zones:
        query = query.filter(Device.zone.in_(payload.zones))

    if payload.devices:
        query = query.filter(Device.hostname.in_(payload.devices))

    return query.all()


# ==========================================================
# POST /api/bulk-user/create
# ==========================================================

@router.post("/create")
def bulk_create_user(
    payload: BulkUserRequest,
    db: Session = Depends(get_db),
    admin=Depends(require_write),
):
    """
    Filter এ যতগুলো ডিভাইস মিলবে, প্রতিটায় user create করার চেষ্টা করবে।
    আগে থেকে থাকলে (duplicate) সেই ডিভাইসে skip করবে, error দিলে সেটাও
    আলাদাভাবে রিপোর্ট করবে।
    """

    if not payload.username:
        return {"success": False, "detail": "Username is required.", "results": []}

    if not payload.password:
        return {"success": False, "detail": "Password is required.", "results": []}

    devices = _filtered_devices(db, payload)

    results = []

    for device in devices:

        entry = {
            "device_id": device.id,
            "hostname": device.hostname,
            "group_name": device.group_name,
            "zone": device.zone,
        }

        try:
            result = ssh_service.create_user_on_device(
                device,
                payload.username,
                payload.password,
                dry_run=payload.dry_run,
                group=payload.group,
                address=payload.address,
            )

            if result["dry_run"]:
                entry["status"] = "would_create"
                entry["message"] = "🧪 Would be created (Test Mode, no device change)"
            else:
                entry["status"] = "created" if result["verified"] else "verify_failed"
                entry["message"] = "✅ Created" if result["verified"] else "⚠️ Verify Failed"

        except DeviceActionError:
            entry["status"] = "already_exists"
            entry["message"] = "⚠️ Already exists (Skipped)"

        except SSHConnectionError as e:
            entry["status"] = "error"
            entry["message"] = f"❌ {str(e)}"

        results.append(entry)

    created = sum(1 for r in results if r["status"] == "created")
    would_create = sum(1 for r in results if r["status"] == "would_create")
    skipped = sum(1 for r in results if r["status"] == "already_exists")
    errored = sum(1 for r in results if r["status"] == "error")

    ssh_service.log_activity(
        db,
        (
            f"🧪 [TEST MODE] Bulk Create '{payload.username}' -> {len(devices)} devices: "
            f"{would_create} would be created, {skipped} already existed, {errored} errors"
            if payload.dry_run else
            f"Bulk Create '{payload.username}' -> {len(devices)} devices: "
            f"{created} created, {skipped} already existed, {errored} errors"
        ),
        admin_username=admin.get("sub"),
        action="bulk_create",
        result=(
            f"dry_run_would_create:{would_create}_skipped:{skipped}_error:{errored}"
            if payload.dry_run else
            f"created:{created}_skipped:{skipped}_error:{errored}"
        ),
    )

    return {
        "success": True,
        "count": len(results),
        "created": created,
        "would_create": would_create,
        "skipped": skipped,
        "errored": errored,
        "dry_run": payload.dry_run,
        "results": results,
    }


# ==========================================================
# POST /api/bulk-user/delete
# ==========================================================

@router.post("/delete")
def bulk_delete_user(
    payload: BulkUserRequest,
    db: Session = Depends(get_db),
    admin=Depends(require_write),
):
    """
    Filter এ যতগুলো ডিভাইস মিলবে, প্রতিটা থেকে user delete করার চেষ্টা করবে।
    ডিভাইসে user না থাকলে সেটা skip করবে (error না দিয়ে)।
    """

    if not payload.username:
        return {"success": False, "detail": "Username is required.", "results": []}

    devices = _filtered_devices(db, payload)

    results = []

    for device in devices:

        entry = {
            "device_id": device.id,
            "hostname": device.hostname,
            "group_name": device.group_name,
            "zone": device.zone,
        }

        try:
            result = ssh_service.delete_user_on_device(
                device, payload.username, dry_run=payload.dry_run
            )

            if result["dry_run"]:
                entry["status"] = "would_delete"
                entry["message"] = "🧪 Would be removed (Test Mode, no device change)"
            else:
                entry["status"] = "deleted" if result["verified"] else "verify_failed"
                entry["message"] = "✅ Removed" if result["verified"] else "⚠️ Verify Failed"

        except DeviceActionError:
            entry["status"] = "not_found"
            entry["message"] = "ℹ️ Not found (Skipped)"

        except SSHConnectionError as e:
            entry["status"] = "error"
            entry["message"] = f"❌ {str(e)}"

        results.append(entry)

    deleted = sum(1 for r in results if r["status"] == "deleted")
    would_delete = sum(1 for r in results if r["status"] == "would_delete")
    skipped = sum(1 for r in results if r["status"] == "not_found")
    errored = sum(1 for r in results if r["status"] == "error")

    ssh_service.log_activity(
        db,
        (
            f"🧪 [TEST MODE] Bulk Remove '{payload.username}' -> {len(devices)} devices: "
            f"{would_delete} would be removed, {skipped} not found, {errored} errors"
            if payload.dry_run else
            f"Bulk Remove '{payload.username}' -> {len(devices)} devices: "
            f"{deleted} removed, {skipped} not found, {errored} errors"
        ),
        admin_username=admin.get("sub"),
        action="bulk_delete",
        result=(
            f"dry_run_would_delete:{would_delete}_skipped:{skipped}_error:{errored}"
            if payload.dry_run else
            f"deleted:{deleted}_skipped:{skipped}_error:{errored}"
        ),
    )

    return {
        "success": True,
        "count": len(results),
        "deleted": deleted,
        "would_delete": would_delete,
        "skipped": skipped,
        "errored": errored,
        "dry_run": payload.dry_run,
        "results": results,
    }