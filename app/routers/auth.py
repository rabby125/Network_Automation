"""
routers/auth.py
-----------------
Login System:
 - GET  /login   -> Login পেজ দেখাবে
 - POST /login   -> Username/Password চেক করে JWT token cookie তে বসাবে
 - GET  /logout  -> Cookie মুছে বের করে দিবে
 - POST /api/admin/change-password -> Settings থেকে নিজের Password পরিবর্তন
"""

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.admin import Admin
from app.services.auth_service import verify_password, hash_password, create_access_token
from app.services.dependencies import get_current_admin

router = APIRouter(tags=["Authentication"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    """Login ফর্ম দেখাবে"""
    return templates.TemplateResponse(
        "login.html", {"request": request, "error": None}
    )


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Username/Password যাচাই করে, ঠিক থাকলে Dashboard এ পাঠাবে"""

    admin = db.query(Admin).filter(Admin.username == username).first()

    # username না পেলে অথবা password না মিললে -> error দেখাবে
    if not admin or not verify_password(password, admin.password):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid Username or Password!"},
            status_code=401,
        )

    # Token তৈরি করে cookie তে বসানো হচ্ছে
    token = create_access_token(
        data={
            "sub": admin.username,
            "admin_id": admin.id,
            "role": admin.role,
        }
    )

    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,      # JavaScript থেকে অ্যাক্সেস করা যাবে না -> নিরাপদ
        max_age=60 * 60 * 2,  # ২ ঘণ্টা
        samesite="lax",
    )
    return response


@router.get("/logout")
def logout():
    """Logout করলে cookie মুছে login পেজে পাঠাবে"""
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("access_token")
    return response


# ---------------- Settings: Password পরিবর্তন ----------------
class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/api/admin/change-password")
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    """লগইন করা Admin নিজের Password পরিবর্তন করতে পারবে"""

    admin_row = db.query(Admin).filter(Admin.id == admin.get("admin_id")).first()

    if not admin_row or not verify_password(payload.current_password, admin_row.password):
        raise HTTPException(
            status_code=401,
            detail="Current Password is incorrect."
        )

    if len(payload.new_password) < 4:
        raise HTTPException(
            status_code=400,
            detail="New Password must be at least 4 characters."
        )

    admin_row.password = hash_password(payload.new_password)

    db.commit()

    return {
        "success": True
    }