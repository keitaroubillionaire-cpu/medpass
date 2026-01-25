from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models import Subject, User
from auth import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/")
async def list_subjects(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    subjects = db.query(Subject).filter(Subject.user_id == user.id).order_by(Subject.created_at.desc()).all()
    return templates.TemplateResponse("subjects/list.html", {
        "request": request,
        "subjects": subjects,
        "user": user
    })


@router.get("/{subject_id}")
async def subject_detail(request: Request, subject_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    subject = db.query(Subject).filter(Subject.id == subject_id, Subject.user_id == user.id).first()
    if not subject:
        return RedirectResponse(url="/subjects", status_code=302)
    return templates.TemplateResponse("subjects/detail.html", {
        "request": request,
        "subject": subject,
        "user": user
    })


@router.post("/create")
async def create_subject(request: Request, name: str = Form(...), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    subject = Subject(name=name, user_id=user.id)
    db.add(subject)
    db.commit()
    return RedirectResponse(url="/subjects", status_code=302)


@router.post("/{subject_id}/delete")
async def delete_subject(request: Request, subject_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    subject = db.query(Subject).filter(Subject.id == subject_id, Subject.user_id == user.id).first()
    if subject:
        db.delete(subject)
        db.commit()
    return RedirectResponse(url="/subjects", status_code=302)
