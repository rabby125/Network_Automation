"""
services/ssh_service.py
-------------------------
এই ফাইলটা হচ্ছে "Python Automation Engine"।

⚠️ ফিক্স নোট (আগের ভার্সনের সমস্যা):
আগে create/edit/delete শুধু action করেই রিটার্ন করত, verify আলাদা করে
frontend (JavaScript) থেকে আরেকটা API কল করে করা হতো। এতে দুইটা সমস্যা ছিল:
  1) দুইবার আলাদা SSH কানেকশন লাগত (স্লো + অপ্রয়োজনীয় লোড)
  2) verify টা "সত্যিকারের প্রমাণ" ছিল না -- frontend চাইলে verify
     বাদ দিয়ে দিতে পারত, backend কখনো নিশ্চিত করত না কাজ সত্যিই হয়েছে কিনা

এখন প্রতিটা create/edit/delete একটাই SSH কানেকশনের ভেতরে:
  search (duplicate/existence check) -> action -> verify (আবার search)
সব করে, এবং ফলাফলে verified/success server-side নিশ্চিত করেই পাঠায়।
"""

from sqlalchemy.orm import Session

from app.automation.ssh import DeviceSession, SSHConnectionError
from app.automation import mikrotik, cisco, huawei, juniper, arista
from app.models.activity_log import ActivityLog

VENDOR_MODULE_MAP = {
    "MikroTik": mikrotik,
    "Cisco": cisco,
    "Huawei": huawei,
    "Juniper": juniper,
    "Arista": arista,
}


class DeviceActionError(Exception):
    """Duplicate user / user not found ইত্যাদি ব্যবসায়িক-লজিক এরর"""
    pass


def get_vendor_module(vendor: str):
    module = VENDOR_MODULE_MAP.get(vendor)
    if not module:
        raise SSHConnectionError(f"No module found for vendor '{vendor}'.")
    return module


def log_activity(
    db: Session,
    message: str,
    admin_username: str = None,
    device_hostname: str = None,
    action: str = None,
    result: str = None,
):
    """Activity Log টেবিলে একটা এন্ট্রি যোগ করে (এখন structured fields সহ)"""
    entry = ActivityLog(
        message=message,
        admin_username=admin_username,
        device_hostname=device_hostname,
        action=action,
        result=result,
    )
    db.add(entry)
    db.commit()


# ------------------------------------------------------------------
# Search: একটা ডিভাইসে গিয়ে user আছে কিনা খুঁজে বের করা
# ------------------------------------------------------------------
def search_user_on_device(device, search_username: str):
    module = get_vendor_module(device.vendor)
    try:
        with DeviceSession(device) as conn:
            exists, raw_output = module.search_user(conn, search_username)
        return {
            "device_id": device.id,
            "hostname": device.hostname,
            "ip_address": device.ip_address,
            "group_name": device.group_name,
            "zone": device.zone,
            "vendor": device.vendor,
            "found": exists,
            "raw_output": raw_output,
            "error": None,
        }
    except SSHConnectionError as e:
        return {
            "device_id": device.id,
            "hostname": device.hostname,
            "ip_address": device.ip_address,
            "group_name": device.group_name,
            "zone": device.zone,
            "vendor": device.vendor,
            "found": False,
            "raw_output": None,
            "error": str(e),
        }


# ------------------------------------------------------------------
# Create -> Duplicate Check + Action + Verify, সব এক কানেকশনে
# ------------------------------------------------------------------
def create_user_on_device(
    device,
    username: str,
    password: str,
    dry_run: bool = False,
    group: str = "full",
    address: str | None = None,
):
    module = get_vendor_module(device.vendor)

    with DeviceSession(device) as conn:
        already_exists, search_output = module.search_user(conn, username)
        if already_exists:
            raise DeviceActionError(
                f"User '{username}' already exists on '{device.hostname}' -- cannot Create again."
            )

        # 🧪 Test Mode: SSH কানেক্ট + Duplicate Check হয়েছে (তাই ডিভাইসে সত্যিই
        # কানেক্ট করা যাচ্ছে কিনা সেটাও যাচাই হয়ে গেলো), কিন্তু আসল Create কমান্ড
        # ডিভাইসে পাঠানো হচ্ছে না -- কোনো পরিবর্তন হবে না।
        if dry_run:
            return {
                "action_output": None,
                "verified": None,
                "verify_output": search_output,
                "dry_run": True,
            }

        # ⚠️ শুধু MikroTik-এ 'group'/'address' concept আছে (RouterOS-এ group
        # বাধ্যতামূলক)। অন্য vendor (Cisco/Huawei/Juniper/Arista) এর
        # create_user() ফাংশনের সিগনেচার আগের মতোই অপরিবর্তিত রাখা হয়েছে।
        if device.vendor == "MikroTik":
            create_output = module.create_user(
                conn, username, password, group=group, address=address
            )
        else:
            create_output = module.create_user(conn, username, password)

        verified_exists, verify_output = module.verify_user(conn, username)

    return {
        "action_output": create_output,
        "verified": verified_exists,   # confirmed by the server itself whether it was really created
        "verify_output": verify_output,
        "dry_run": False,
    }



# ------------------------------------------------------------------
# Edit -> User থাকতে হবে (না থাকলে এরর) + Action + Verify
# ------------------------------------------------------------------
def edit_user_on_device(
    device,
    username: str,
    new_password: str,
    dry_run: bool = False,
    group: str = "full",
    address: str | None = None,
):
    module = get_vendor_module(device.vendor)

    with DeviceSession(device) as conn:
        exists, search_output = module.search_user(conn, username)
        if not exists:
            raise DeviceActionError(
                f"User '{username}' not found on '{device.hostname}' -- cannot Edit."
            )

        # 🧪 Test Mode: Duplicate/Existence Check হয়েছে, আসল Edit কমান্ড পাঠানো হয়নি
        if dry_run:
            return {
                "action_output": None,
                "verified": None,
                "verify_output": search_output,
                "dry_run": True,
            }

        # ⚠️ শুধু MikroTik-এ 'group'/'address' একসাথে বদলানো যায় (Create Form
        # এর মতোই); অন্য vendor (Cisco/Huawei/Juniper/Arista) এর edit_user()
        # ফাংশনের সিগনেচার আগের মতোই অপরিবর্তিত রাখা হয়েছে।
        if device.vendor == "MikroTik":
            edit_output = module.edit_user(conn, username, new_password, group=group, address=address)
        else:
            edit_output = module.edit_user(conn, username, new_password)

        verified_exists, verify_output = module.verify_user(conn, username)

    return {
        "action_output": edit_output,
        "verified": verified_exists,
        "verify_output": verify_output,
        "dry_run": False,
    }


# ------------------------------------------------------------------
# Delete -> User থাকতে হবে + Action + Verify (verify করবে যে সত্যিই মুছে গেছে)
# ------------------------------------------------------------------
def delete_user_on_device(device, username: str, dry_run: bool = False):
    module = get_vendor_module(device.vendor)

    with DeviceSession(device) as conn:
        exists, search_output = module.search_user(conn, username)
        if not exists:
            raise DeviceActionError(
                f"User '{username}' not found on '{device.hostname}' -- nothing to Delete."
            )

        # 🧪 Test Mode: Existence Check হয়েছে, আসল Delete কমান্ড পাঠানো হয়নি
        if dry_run:
            return {
                "action_output": None,
                "verified": None,
                "verify_output": search_output,
                "dry_run": True,
            }

        delete_output = module.delete_user(conn, username)
        still_exists, verify_output = module.verify_user(conn, username)

    return {
        "action_output": delete_output,
        "verified": not still_exists,   # for delete, verified = confirmed no longer exists
        "verify_output": verify_output,
        "dry_run": False,
    }


# ------------------------------------------------------------------
# আলাদা Verify API এর জন্য (ঐচ্ছিক -- ম্যানুয়ালি আবার চেক করতে চাইলে)
# ------------------------------------------------------------------
def verify_user_on_device(device, username: str):
    module = get_vendor_module(device.vendor)
    with DeviceSession(device) as conn:
        exists, raw_output = module.verify_user(conn, username)
    return exists, raw_output