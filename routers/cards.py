from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models import Card, Lecture, Subject, Question
from auth import get_current_user
from services.question_generator import generate_question_from_card, is_api_configured

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


@router.post("/{card_id}/generate-question")
async def generate_question(request: Request, card_id: int, db: Session = Depends(get_db)):
    """Generate a question from card using AI."""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    card = db.query(Card).join(Lecture).join(Subject).filter(
        Card.id == card_id, Subject.user_id == user.id
    ).first()

    if not card:
        return RedirectResponse(url="/cards", status_code=302)

    if not is_api_configured():
        return RedirectResponse(url=f"/questions?card_id={card_id}&error=api_not_configured", status_code=302)

    # Generate question using AI
    question_data = generate_question_from_card(card.theme, card.summary)

    if not question_data or not question_data.get("question_text"):
        return RedirectResponse(url=f"/questions?card_id={card_id}&error=generation_failed", status_code=302)

    # Create question in database
    question = Question(
        card_id=card_id,
        question_text=question_data["question_text"],
        answer_200=question_data.get("answer_200", ""),
        rubric=question_data.get("rubric", ""),
        is_past_exam=False
    )
    db.add(question)
    db.commit()

    return RedirectResponse(url=f"/questions?card_id={card_id}", status_code=302)


@router.get("/{card_id}/api-status")
async def check_api_status(request: Request, card_id: int, db: Session = Depends(get_db)):
    """Check if Anthropic API is configured."""
    user = get_current_user(request, db)
    if not user:
        return {"configured": False}

    return {"configured": is_api_configured()}
