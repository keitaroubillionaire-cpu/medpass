from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models import Card, Lecture, Subject
from auth import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/")
async def list_cards(request: Request, lecture_id: int = None, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    if lecture_id:
        lecture = db.query(Lecture).join(Subject).filter(Lecture.id == lecture_id, Subject.user_id == user.id).first()
        if not lecture:
            return RedirectResponse(url="/lectures", status_code=302)
        cards = db.query(Card).filter(Card.lecture_id == lecture_id).order_by(Card.importance.desc()).all()
    else:
        cards = db.query(Card).join(Lecture).join(Subject).filter(Subject.user_id == user.id).order_by(Card.created_at.desc()).all()
        lecture = None

    return templates.TemplateResponse("cards/list.html", {
        "request": request,
        "cards": cards,
        "lecture": lecture,
        "user": user
    })


@router.post("/create")
async def create_card(
    request: Request,
    lecture_id: int = Form(...),
    theme: str = Form(...),
    summary: str = Form(""),
    importance: int = Form(2),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    # Verify lecture belongs to user
    lecture = db.query(Lecture).join(Subject).filter(Lecture.id == lecture_id, Subject.user_id == user.id).first()
    if not lecture:
        return RedirectResponse(url="/lectures", status_code=302)

    card = Card(lecture_id=lecture_id, theme=theme, summary=summary, importance=importance)
    db.add(card)
    db.commit()
    return RedirectResponse(url=f"/cards?lecture_id={lecture_id}", status_code=302)


@router.post("/{card_id}/update")
async def update_card(
    request: Request,
    card_id: int,
    theme: str = Form(...),
    summary: str = Form(""),
    importance: int = Form(2),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    card = db.query(Card).join(Lecture).join(Subject).filter(Card.id == card_id, Subject.user_id == user.id).first()
    if card:
        card.theme = theme
        card.summary = summary
        card.importance = importance
        db.commit()
        return RedirectResponse(url=f"/cards?lecture_id={card.lecture_id}", status_code=302)
    return RedirectResponse(url="/cards", status_code=302)


@router.post("/{card_id}/delete")
async def delete_card(request: Request, card_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    card = db.query(Card).join(Lecture).join(Subject).filter(Card.id == card_id, Subject.user_id == user.id).first()
    if card:
        lecture_id = card.lecture_id
        db.delete(card)
        db.commit()
        return RedirectResponse(url=f"/cards?lecture_id={lecture_id}", status_code=302)
    return RedirectResponse(url="/cards", status_code=302)
