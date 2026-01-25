import os
from datetime import datetime
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models import Lecture, Card, Question, Print, Subject
from services.pdf_generator import generate_lecture_pdf
from auth import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Ensure prints directory exists
PRINTS_DIR = "prints_output"
os.makedirs(PRINTS_DIR, exist_ok=True)


@router.get("/lecture/{lecture_id}")
async def generate_print(request: Request, lecture_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    lecture = db.query(Lecture).join(Subject).filter(Lecture.id == lecture_id, Subject.user_id == user.id).first()
    if not lecture:
        return RedirectResponse(url="/lectures", status_code=302)

    # Get cards and questions for this lecture
    cards = db.query(Card).filter(Card.lecture_id == lecture_id).order_by(Card.importance.desc()).all()

    # Generate PDF
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"lecture_{lecture_id}_{timestamp}.pdf"
    pdf_path = os.path.join(PRINTS_DIR, filename)

    generate_lecture_pdf(lecture, cards, pdf_path)

    # Save print record
    print_record = Print(lecture_id=lecture_id, pdf_path=pdf_path)
    db.add(print_record)
    db.commit()

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"{lecture.title}_まとめ.pdf"
    )


@router.get("/history")
async def print_history(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    prints = db.query(Print).join(Lecture).join(Subject).filter(
        Subject.user_id == user.id
    ).order_by(Print.created_at.desc()).all()

    return templates.TemplateResponse("prints/history.html", {
        "request": request,
        "prints": prints,
        "user": user
    })


@router.get("/download/{print_id}")
async def download_print(request: Request, print_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    print_record = db.query(Print).join(Lecture).join(Subject).filter(
        Print.id == print_id, Subject.user_id == user.id
    ).first()

    if not print_record or not os.path.exists(print_record.pdf_path):
        return RedirectResponse(url="/prints/history", status_code=302)

    return FileResponse(
        print_record.pdf_path,
        media_type="application/pdf",
        filename=f"medpass_print_{print_id}.pdf"
    )
