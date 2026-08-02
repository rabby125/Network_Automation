"""
main.py
--------
FastAPI অ্যাপের মূল Entry Point।
এখান থেকেই সব Router যুক্ত হয় এবং Server চালু হয়।

চালানোর নিয়ম (project root থেকে):
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database.database import Base, engine
from app.models import admin as admin_model, device as device_model, activity_log as activity_log_model  # noqa: F401  Base.metadata তে যোগ করার জন্য

from app.routers import auth, search, user, device, admin, bulk_user
from app.services.auth_service import decode_access_token

# ডাটাবেজ টেবিল না থাকলে তৈরি করে দিবে
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Network Automation Tool")

# Static ফাইল (CSS/JS) mount করা
app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

# Router যুক্ত করা
app.include_router(auth.router)
app.include_router(search.router)
app.include_router(user.router)
app.include_router(device.router)
app.include_router(admin.router)  # ⚠️ ফিক্স: আগে এটা বাদ পড়েছিল, Create Device API কাজ করত না
app.include_router(bulk_user.router)  # ⚠️ ফিক্স: এটাও বাদ পড়েছিল, Bulk Create/Remove User API কাজ করত না


@app.get("/")
def root():
    """হোমপেজে গেলে সরাসরি Dashboard এ (login না থাকলে Login এ) পাঠিয়ে দিবে"""
    return RedirectResponse(url="/dashboard")


@app.get("/dashboard")
def dashboard_page(request: Request):
    """
    Dashboard পেজ। এখানে API এর মতো 401 JSON error না দিয়ে,
    সরাসরি Login পেজে Redirect করে দেওয়া হচ্ছে (কারণ এটা ব্রাউজার পেজ)।
    """
    token = request.cookies.get("access_token")
    payload = decode_access_token(token) if token else None

    if not payload:
        return RedirectResponse(url="/login")

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "username": payload.get("sub", "Admin"),
            "role": payload.get("role"),
        },
    )