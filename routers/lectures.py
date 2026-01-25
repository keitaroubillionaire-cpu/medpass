from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models import Lecture, Subject
from auth import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/")
async def list_lectures(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    lectures = db.query(Lecture).join(Subject).filter(Subject.user_id == user.id).order_by(Lecture.created_at.desc()).all()
    return templates.TemplateResponse("lectures/list.html", {
        "request": request,
        "lectures": lectures,
        "user": user
    })


@router.get("/{lecture_id}")
async def lecture_detail(request: Request, lecture_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    lecture = db.query(Lecture).join(Subject).filter(Lecture.id == lecture_id, Subject.user_id == user.id).first()
    if not lecture:
        return RedirectResponse(url="/lectures", status_code=302)
    return templates.TemplateResponse("lectures/detail.html", {
        "request": request,
        "lecture": lecture,
        "user": user
    })


@router.get("/{lecture_id}/input")
async def lecture_input(request: Request, lecture_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    lecture = db.query(Lecture).join(Subject).filter(Lecture.id == lecture_id, Subject.user_id == user.id).first()
    if not lecture:
        return RedirectResponse(url="/lectures", status_code=302)
    return templates.TemplateResponse("lectures/input.html", {
        "request": request,
        "lecture": lecture,
        "user": user
    })


@router.post("/create")
async def create_lecture(
    request: Request,
    subject_id: int = Form(...),
    title: str = Form(...),
    slide_count: int = Form(0),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    # Verify subject belongs to user
    subject = db.query(Subject).filter(Subject.id == subject_id, Subject.user_id == user.id).first()
    if not subject:
        return RedirectResponse(url="/subjects", status_code=302)

    lecture = Lecture(subject_id=subject_id, title=title, slide_count=slide_count)
    db.add(lecture)
    db.commit()
    return RedirectResponse(url=f"/subjects/{subject_id}", status_code=302)


@router.post("/{lecture_id}/update-content")
async def update_lecture_content(
    request: Request,
    lecture_id: int,
    content: str = Form(...),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    lecture = db.query(Lecture).join(Subject).filter(Lecture.id == lecture_id, Subject.user_id == user.id).first()
    if lecture:
        lecture.content = content
        db.commit()
    return RedirectResponse(url=f"/lectures/{lecture_id}", status_code=302)


@router.post("/{lecture_id}/delete")
async def delete_lecture(request: Request, lecture_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    lecture = db.query(Lecture).join(Subject).filter(Lecture.id == lecture_id, Subject.user_id == user.id).first()
    if lecture:
        subject_id = lecture.subject_id
        db.delete(lecture)
        db.commit()
        return RedirectResponse(url=f"/subjects/{subject_id}", status_code=302)
    return RedirectResponse(url="/lectures", status_code=302)
