"""
routers/admin.py
-----------------
Admin Management API

বর্তমানে:
1. Admin List
2. Create Admin
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.admin import Admin
from app.services.auth_service import hash_password
from app.services.dependencies import require_super
from app.services import ssh_service

router = APIRouter(
    prefix="/api/admin",
    tags=["Admin Management"],
)


# =====================================================
# Schemas
# =====================================================

class AdminCreateRequest(BaseModel):
    username: str
    password: str
    role: str


class AdminRoleRequest(BaseModel):
    admin_id: int
    role: str


class AdminResetPasswordRequest(BaseModel):
    admin_id: int
    new_password: str


class AdminDeleteRequest(BaseModel):
    admin_id: int


# =====================================================
# Admin List
# =====================================================

@router.get("/list")
def list_admins(
    db: Session = Depends(get_db),
    admin=Depends(require_super),
):
    admins = db.query(Admin).order_by(Admin.id).all()

    return {
        "count": len(admins),
        "admins": [
            {
                "id": a.id,
                "username": a.username,
                "role": a.role,
                "created_at": a.created_at.strftime("%Y-%m-%d %H:%M"),
                "is_me": a.id == admin.get("admin_id"),
            }
            for a in admins
        ],
    }


# =====================================================
# Create Admin
# =====================================================

@router.post("/create")
def create_admin(
    payload: AdminCreateRequest,
    db: Session = Depends(get_db),
    admin=Depends(require_super),
):
    """
    নতুন Admin তৈরি করবে।
    শুধুমাত্র Super Admin ব্যবহার করতে পারবে।
    """

    # Username আগে থেকেই আছে কিনা
    existing = (
        db.query(Admin)
        .filter(Admin.username == payload.username)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Username already exists.",
        )

    # Password Length Check
    if len(payload.password) < 4:
        raise HTTPException(
            status_code=400,
            detail="Password minimum 4 characters.",
        )

    # Role Validation
    if payload.role not in ["read", "write", "super_admin"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid role.",
        )

    new_admin = Admin(
        username=payload.username,
        password=hash_password(payload.password),
        role=payload.role,
    )

    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)

    ssh_service.log_activity(
        db,
        f"New Admin '{new_admin.username}' was created ({new_admin.role})",
        admin_username=admin.get("sub"),
        action="create_admin",
        result="success",
    )

    return {
        "success": True,
        "admin_id": new_admin.id,
    }

# =====================================================
# Edit Admin Role
# =====================================================

@router.post("/edit-role")
def edit_admin_role(
    payload: AdminRoleRequest,
    db: Session = Depends(get_db),
    admin=Depends(require_super),
):
    """
    Admin এর Role পরিবর্তন করবে।
    শুধুমাত্র Super Admin করতে পারবে।
    """

    target = (
        db.query(Admin)
        .filter(Admin.id == payload.admin_id)
        .first()
    )

    if not target:
        raise HTTPException(
            status_code=404,
            detail="Admin not found.",
        )

    # নিজের Role পরিবর্তন করা যাবে না
    if target.id == admin.get("admin_id"):
        raise HTTPException(
            status_code=400,
            detail="You cannot change your own role.",
        )

    # Role Validation
    if payload.role not in ["read", "write", "super_admin"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid role.",
        )

    # যদি Role একই থাকে
    if target.role == payload.role:
        raise HTTPException(
            status_code=400,
            detail="Role is already assigned.",
        )

    # শেষ Super Admin কে পরিবর্তন করা যাবে না
    if target.role == "super_admin" and payload.role != "super_admin":
        super_count = (
            db.query(Admin)
            .filter(Admin.role == "super_admin")
            .count()
        )

        if super_count <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot change the last Super Admin.",
            )

    target.role = payload.role

    db.commit()

    ssh_service.log_activity(
        db,
        f"Admin '{target.username}' role changed to '{payload.role}'",
        admin_username=admin.get("sub"),
        action="edit_admin_role",
        result="success",
    )

    return {
        "success": True,
    }

# =====================================================
# Reset Admin Password
# =====================================================

@router.post("/reset-password")
def reset_admin_password(
    payload: AdminResetPasswordRequest,
    db: Session = Depends(get_db),
    admin=Depends(require_super),
):
    """
    Super Admin অন্য Admin-এর Password Reset করবে।
    """

    target = (
        db.query(Admin)
        .filter(Admin.id == payload.admin_id)
        .first()
    )

    if not target:
        raise HTTPException(
            status_code=404,
            detail="Admin not found.",
        )

    # নিজের Password এখানে Reset করা যাবে না
    if target.id == admin.get("admin_id"):
        raise HTTPException(
            status_code=400,
            detail="Use Change Password for your own account.",
        )

    # Password Validation
    if len(payload.new_password) < 4:
        raise HTTPException(
            status_code=400,
            detail="Password minimum 4 characters.",
        )

    target.password = hash_password(payload.new_password)

    db.commit()

    ssh_service.log_activity(
        db,
        f"Password reset for Admin '{target.username}'",
        admin_username=admin.get("sub"),
        action="reset_admin_password",
        result="success",
    )

    return {
        "success": True,
    }

# =====================================================
# Delete Admin
# =====================================================

@router.post("/delete")
def delete_admin(
    payload: AdminDeleteRequest,
    db: Session = Depends(get_db),
    admin=Depends(require_super),
):
    """
    শুধুমাত্র Super Admin অন্য Admin Delete করতে পারবে।
    """

    target = (
        db.query(Admin)
        .filter(Admin.id == payload.admin_id)
        .first()
    )

    if not target:
        raise HTTPException(
            status_code=404,
            detail="Admin not found.",
        )

    # নিজের Account Delete করা যাবে না
    if target.id == admin.get("admin_id"):
        raise HTTPException(
            status_code=400,
            detail="You cannot delete your own account.",
        )

    # শেষ Super Admin Delete করা যাবে না
    if target.role == "super_admin":
        super_count = (
            db.query(Admin)
            .filter(Admin.role == "super_admin")
            .count()
        )

        if super_count <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete the last Super Admin.",
            )

    username = target.username

    db.delete(target)
    db.commit()

    ssh_service.log_activity(
        db,
        f"Admin '{username}' deleted",
        admin_username=admin.get("sub"),
        action="delete_admin",
        result="success",
    )

    return {
        "success": True,
        "message": "Admin deleted successfully."
    }