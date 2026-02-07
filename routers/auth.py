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

def set_auth_cookie(response: RedirectResponse, token: str):
    """Set authentication cookie."""
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=30 * 24 * 60 * 60,  # 30 days
        path="/"
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

    access_token = create_access_token(data={"sub": str(user.id)})
    response = RedirectResponse(url="/", status_code=303)
    set_auth_cookie(response, access_token)
    return response


@router.get("/register")
async def register_page(request: Request):
    # 新規登録は停止中
    return templates.TemplateResponse("auth/register.html", {
        "request": request,
        "error": "新規登録は現在停止しています"
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
    # 新規登録は停止中
    return templates.TemplateResponse("auth/register.html", {
        "request": request,
        "error": "新規登録は現在停止しています"
    })


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/auth/login", status_code=302)
    response.delete_cookie(key="access_token", path="/")
    return response
