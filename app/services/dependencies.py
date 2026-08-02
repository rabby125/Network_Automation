"""
services/dependencies.py
--------------------------
Protected route গুলোতে ব্যবহার করার জন্য common dependency।
Cookie থেকে JWT token পড়ে, Admin login করা আছে কিনা চেক করে।
"""

from fastapi import Request, HTTPException, status
from app.services.auth_service import decode_access_token


def get_current_admin(request: Request) -> dict:
    """
    Cookie থেকে JWT Token পড়ে।
    Valid হলে payload return করে।
    """

    token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login required",
        )

    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired",
        )

    return payload


# ----------------------------------------------------
# Read Permission
# ----------------------------------------------------
def require_read(request: Request):
    admin = get_current_admin(request)

    if admin.get("role") not in ["read", "write", "super_admin"]:
        raise HTTPException(
            status_code=403,
            detail="Permission denied."
        )

    return admin


# ----------------------------------------------------
# Write Permission
# ----------------------------------------------------
def require_write(request: Request):
    admin = get_current_admin(request)

    if admin.get("role") not in ["write", "super_admin"]:
        raise HTTPException(
            status_code=403,
            detail="Write permission required."
        )

    return admin


# ----------------------------------------------------
# Super Admin Permission
# ----------------------------------------------------
def require_super(request: Request):
    admin = get_current_admin(request)

    if admin.get("role") != "super_admin":
        raise HTTPException(
            status_code=403,
            detail="Super Admin only."
        )

    return admin