"""
routers/search.py
-----------------
Search API + Cascading Filters

Group
  ↓
Zone
  ↓
Device
  ↓
Username Search
"""

from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.device import Device
from app.models.activity_log import ActivityLog
from app.services.dependencies import require_read
from app.services import ssh_service


router = APIRouter(prefix="/api", tags=["Search"])


# ==========================================================
# Search Request
# ==========================================================

class SearchRequest(BaseModel):
    groups: Optional[List[str]] = []
    zones: Optional[List[str]] = []
    devices: Optional[List[str]] = []
    username: str


# ==========================================================
# GET /api/filters
# ==========================================================

@router.get("/filters")
def get_filters(
    db: Session = Depends(get_db),
    admin=Depends(require_read),
):
    """
    প্রথমে Group load হবে।
    সাথে সব Zone এবং Device initial data পাঠাবে।
    """

    groups = (
        db.query(Device.group_name)
        .distinct()
        .order_by(Device.group_name)
        .all()
    )

    zones = (
        db.query(Device.zone)
        .distinct()
        .order_by(Device.zone)
        .all()
    )

    devices = (
        db.query(
            Device.id,
            Device.hostname,
            Device.group_name,
            Device.zone,
        )
        .order_by(Device.hostname)
        .all()
    )

    # Cascading এর জন্য group -> zones এবং (group,zone) -> devices ম্যাপ তৈরি করা হচ্ছে
    zones_by_group = {}
    devices_by_zone = {}

    for row in devices:
        zones_by_group.setdefault(row.group_name, set()).add(row.zone)

        key = f"{row.group_name}|||{row.zone}"
        devices_by_zone.setdefault(key, []).append(
            {"id": row.id, "hostname": row.hostname}
        )

    # set -> sorted list এ কনভার্ট করা হচ্ছে (JSON এ set পাঠানো যায় না)
    zones_by_group = {
        group: sorted(zone_set)
        for group, zone_set in zones_by_group.items()
    }

    return {
        "groups": [row[0] for row in groups],

        "zones": [row[0] for row in zones],

        "devices": [
            {
                "id": row.id,
                "hostname": row.hostname,
                "group_name": row.group_name,
                "zone": row.zone,
            }
            for row in devices
        ],

        "zones_by_group": zones_by_group,

        "devices_by_zone": devices_by_zone,
    }


# ==========================================================
# GET /api/filters/zones
# ==========================================================

@router.get("/filters/zones")
def get_zones(
    group: Optional[List[str]] = None,
    db: Session = Depends(get_db),
    admin=Depends(require_read),
):
    """
    Group অনুযায়ী Zone load করবে।

    Example:

    /api/filters/zones

    অথবা

    /api/filters/zones?group=Circle%20Home
    """

    query = db.query(Device.zone).distinct()

    if group:
        query = query.filter(
            Device.group_name.in_(group)
        )

    zones = (
        query
        .order_by(Device.zone)
        .all()
    )

    return {
        "zones": [row[0] for row in zones]
    }


# ==========================================================
# GET /api/filters/devices
# ==========================================================

@router.get("/filters/devices")
def get_devices(
    group: Optional[List[str]] = None,
    zone: Optional[List[str]] = None,
    db: Session = Depends(get_db),
    admin=Depends(require_read),
):
    """
    Group + Zone অনুযায়ী Device load করবে।
    """

    query = db.query(Device)

    if group:
        query = query.filter(
            Device.group_name.in_(group)
        )

    if zone:
        query = query.filter(
            Device.zone.in_(zone)
        )

    devices = (
        query
        .order_by(Device.hostname)
        .all()
    )

    return {
        "devices": [
            {
                "id": device.id,
                "hostname": device.hostname,
                "group_name": device.group_name,
                "zone": device.zone,
            }
            for device in devices
        ]
    }


# ==========================================================
# POST /api/search
# ==========================================================

@router.post("/search")
def search_user(
    payload: SearchRequest,
    db: Session = Depends(get_db),
    admin=Depends(require_read),
):
    """
    Group + Zone + Device + Username দিয়ে
    নির্দিষ্ট Device-এ SSH করে User খুঁজবে।
    """

    query = db.query(Device)

    # Group
    if payload.groups:
        query = query.filter(
            Device.group_name.in_(payload.groups)
        )

    # Zone
    if payload.zones:
        query = query.filter(
            Device.zone.in_(payload.zones)
        )

    # Device
    if payload.devices:
        query = query.filter(
            Device.hostname.in_(payload.devices)
        )

    devices = query.all()

    results = []

    for device in devices:

        result = ssh_service.search_user_on_device(
            device,
            payload.username
        )

        result["username"] = payload.username

        results.append(result)

    # Activity Log
    ssh_service.log_activity(
        db,
        f"Search '{payload.username}' -> "
        f"checked {len(devices)} devices",
        admin_username=admin.get("sub"),
        action="search",
        result=f"{len(devices)}_devices",
    )

    return {
        "count": len(results),
        "results": results,
    }


# ==========================================================
# GET /api/activity-log
# ==========================================================

@router.get("/activity-log")
def get_activity_log(
    db: Session = Depends(get_db),
    admin=Depends(require_read),
):
    """
    সর্বশেষ ২০টা Activity Log দেখাবে।
    """

    logs = (
        db.query(ActivityLog)
        .order_by(ActivityLog.id.desc())
        .limit(20)
        .all()
    )

    return {
        "logs": [
            {
                "time": (
                    log.created_at.strftime("%H:%M")
                    if log.created_at
                    else ""
                ),
                "message": log.message,
            }
            for log in logs
        ]
    }