import os

import bcrypt
from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.database import get_db
from app.models import User


router = APIRouter(tags=["authentication"])

SERVICE_USER_ROLE = "service_user"
MONITORING_ROLES = {"monitoring", "admin", "super_admin"}
ACCOUNT_ACTIVE = "ACTIVE"
ACCOUNT_PENDING = "PENDING"


def get_templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def get_current_user(request: Request, db: Session) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.query(User).filter(User.id == user_id).first()


def is_service_user(user: User | None) -> bool:
    return bool(user and user.role == SERVICE_USER_ROLE)


def is_monitoring_user(user: User | None) -> bool:
    return bool(user and user.role in MONITORING_ROLES)


def get_registration_status() -> str:
    auto_approve = os.getenv("SERVICE_USER_AUTO_APPROVE", "false").lower() == "true"
    return ACCOUNT_ACTIVE if auto_approve else ACCOUNT_PENDING


def redirect_after_login(user: User) -> str:
    if is_monitoring_user(user):
        return "/admin/dashboard"
    return "/dashboard"


def render_register(
    request: Request,
    templates: Jinja2Templates,
    *,
    error: str | None = None,
    success: str | None = None,
    form_data: dict | None = None,
    status_code: int = status.HTTP_200_OK,
):
    return templates.TemplateResponse(
        request,
        "register.html",
        {
            "request": request,
            "error": error,
            "success": success,
            "form_data": form_data or {},
        },
        status_code=status_code,
    )


def render_login(
    request: Request,
    templates: Jinja2Templates,
    *,
    login_type: str,
    error: str | None = None,
    success: str | None = None,
    form_data: dict | None = None,
    status_code: int = status.HTTP_200_OK,
):
    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "request": request,
            "error": error,
            "success": success,
            "login_type": login_type,
            "form_data": form_data or {},
        },
        status_code=status_code,
    )


@router.get("/register")
def register_page(request: Request, templates: Jinja2Templates = Depends(get_templates)):
    return render_register(request, templates)


@router.post("/register")
def register_user(
    request: Request,
    company_name: str = Form(...),
    email: str = Form(...),
    business_id: str = Form(...),
    pic_name: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
    templates: Jinja2Templates = Depends(get_templates),
):
    company_name = company_name.strip()
    email = email.strip().lower()
    business_id = business_id.strip()
    pic_name = pic_name.strip()

    form_data = {
        "company_name": company_name,
        "email": email,
        "business_id": business_id,
        "pic_name": pic_name,
    }

    if not all([company_name, email, business_id, pic_name]):
        return render_register(
            request,
            templates,
            error="Semua data perusahaan wajib diisi.",
            form_data=form_data,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if "@" not in email:
        return render_register(
            request,
            templates,
            error="Email tidak valid.",
            form_data=form_data,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if len(password) < 8:
        return render_register(
            request,
            templates,
            error="Kata sandi minimal 8 karakter.",
            form_data=form_data,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        return render_register(
            request,
            templates,
            error="Email sudah terdaftar.",
            form_data=form_data,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    account_status = get_registration_status()
    user = User(
        username=email,
        company_name=company_name,
        email=email,
        business_id=business_id,
        pic_name=pic_name,
        password_hash=hash_password(password),
        role=SERVICE_USER_ROLE,
        account_status=account_status,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    if account_status == ACCOUNT_ACTIVE:
        request.session.clear()
        request.session["user_id"] = user.id
        request.session["role"] = user.role
        request.session["username"] = user.pic_name or user.company_name or user.email
        log_audit_event(db, request, user.id, "login")
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    return render_register(
        request,
        templates,
        success="Pendaftaran berhasil. Akun Anda menunggu verifikasi petugas sebelum bisa digunakan.",
    )


@router.get("/login")
def login_redirect():
    return RedirectResponse(url="/login/pengguna-jasa", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/login/pengguna-jasa")
def service_login_page(request: Request, templates: Jinja2Templates = Depends(get_templates)):
    return render_login(request, templates, login_type="service_user")


@router.post("/login/pengguna-jasa")
def service_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
    templates: Jinja2Templates = Depends(get_templates),
):
    email = email.strip().lower()
    form_data = {"email": email}
    user = (
        db.query(User)
        .filter(User.email == email, User.role == SERVICE_USER_ROLE)
        .first()
    )

    if not user or not verify_password(password, user.password_hash):
        return render_login(
            request,
            templates,
            login_type="service_user",
            error="Email atau kata sandi tidak valid.",
            form_data=form_data,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    if user.account_status != ACCOUNT_ACTIVE:
        return render_login(
            request,
            templates,
            login_type="service_user",
            error="Akun Anda masih menunggu verifikasi petugas.",
            form_data=form_data,
            status_code=status.HTTP_403_FORBIDDEN,
        )

    request.session.clear()
    request.session["user_id"] = user.id
    request.session["role"] = user.role
    request.session["username"] = user.pic_name or user.company_name or user.email
    log_audit_event(db, request, user.id, "login")

    return RedirectResponse(url=redirect_after_login(user), status_code=status.HTTP_303_SEE_OTHER)


@router.get("/login/petugas")
def monitoring_login_page(request: Request, templates: Jinja2Templates = Depends(get_templates)):
    return render_login(request, templates, login_type="monitoring")


@router.post("/login/petugas")
def monitoring_login(
    request: Request,
    identifier: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
    templates: Jinja2Templates = Depends(get_templates),
):
    identifier = identifier.strip()
    form_data = {"identifier": identifier}
    user = (
        db.query(User)
        .filter(
            User.role.in_(MONITORING_ROLES),
            or_(User.username == identifier, User.email == identifier.lower()),
        )
        .first()
    )

    if not user or not verify_password(password, user.password_hash):
        return render_login(
            request,
            templates,
            login_type="monitoring",
            error="Akun petugas atau kata sandi tidak valid.",
            form_data=form_data,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    if user.account_status != ACCOUNT_ACTIVE:
        return render_login(
            request,
            templates,
            login_type="monitoring",
            error="Akun petugas belum aktif.",
            form_data=form_data,
            status_code=status.HTTP_403_FORBIDDEN,
        )

    request.session.clear()
    request.session["user_id"] = user.id
    request.session["role"] = user.role
    request.session["username"] = user.username or user.pic_name or user.email
    log_audit_event(db, request, user.id, "login")

    return RedirectResponse(url=redirect_after_login(user), status_code=status.HTTP_303_SEE_OTHER)


@router.get("/logout")
def logout_user(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


def get_session_secret() -> str:
    return os.getenv("SESSION_SECRET_KEY", "change-this-session-secret-in-production")


def session_uses_https() -> bool:
    return os.getenv("SESSION_HTTPS_ONLY", "false").lower() == "true"
