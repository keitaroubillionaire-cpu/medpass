import os
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models import User
from auth import get_password_hash, verify_password, create_access_token, get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Check if running on production (Render sets this)
IS_PRODUCTION = os.getenv("RENDER", False)


def set_auth_cookie(response: RedirectResponse, token: str):
    """Set authentication cookie with proper settings for production/development."""
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=30 * 24 * 60 * 60,  # 30 days
        samesite="lax",
        secure=bool(IS_PRODUCTION)  # True on HTTPS (production)
    )
    return response


@router.get("/login")
async def login_page(request: Request):
    user = get_current_user(request, next(get_db()))
    if user:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("auth/login.html", {
        "request": request,
        "error": None
    })


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse("auth/login.html", {
            "request": request,
            "error": "メールアドレスまたはパスワードが正しくありません"
        })

    access_token = create_access_token(data={"sub": user.id})
    response = RedirectResponse(url="/", status_code=303)
    set_auth_cookie(response, access_token)
    return response


@router.get("/register")
async def register_page(request: Request):
    user = get_current_user(request, next(get_db()))
    if user:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("auth/register.html", {
        "request": request,
        "error": None
    })


@router.post("/register")
async def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    db: Session = Depends(get_db)
):
    # Validation
    if password != password_confirm:
        return templates.TemplateResponse("auth/register.html", {
            "request": request,
            "error": "パスワードが一致しません"
        })

    if len(password) < 6:
        return templates.TemplateResponse("auth/register.html", {
            "request": request,
            "error": "パスワードは6文字以上で入力してください"
        })

    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        return templates.TemplateResponse("auth/register.html", {
            "request": request,
            "error": "このメールアドレスは既に登録されています"
        })

    # Create user
    hashed_password = get_password_hash(password)
    user = User(
        email=email,
        username=username,
        hashed_password=hashed_password
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Auto login
    access_token = create_access_token(data={"sub": user.id})
    response = RedirectResponse(url="/", status_code=303)
    set_auth_cookie(response, access_token)
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/auth/login", status_code=302)
    response.delete_cookie(key="access_token")
    return response
