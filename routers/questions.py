from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models import Question, Card, Lecture, Subject, Attempt
from auth import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/")
async def list_questions(request: Request, card_id: int = None, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    if card_id:
        card = db.query(Card).join(Lecture).join(Subject).filter(Card.id == card_id, Subject.user_id == user.id).first()
        if not card:
            return RedirectResponse(url="/cards", status_code=302)
        questions = db.query(Question).filter(Question.card_id == card_id).all()
    else:
        questions = db.query(Question).join(Card).join(Lecture).join(Subject).filter(Subject.user_id == user.id).order_by(Question.created_at.desc()).all()
        card = None

    return templates.TemplateResponse("questions/list.html", {
        "request": request,
        "questions": questions,
        "card": card,
        "user": user
    })


@router.post("/create")
async def create_question(
    request: Request,
    card_id: int = Form(...),
    question_text: str = Form(...),
    answer_200: str = Form(""),
    rubric: str = Form(""),
    source_slide: int = Form(None),
    is_past_exam: bool = Form(False),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    # Verify card belongs to user
    card = db.query(Card).join(Lecture).join(Subject).filter(Card.id == card_id, Subject.user_id == user.id).first()
    if not card:
        return RedirectResponse(url="/cards", status_code=302)

    question = Question(
        card_id=card_id,
        question_text=question_text,
        answer_200=answer_200,
        rubric=rubric,
        source_slide=source_slide,
        is_past_exam=is_past_exam
    )
    db.add(question)
    db.commit()
    return RedirectResponse(url=f"/questions?card_id={card_id}", status_code=302)


@router.post("/{question_id}/update")
async def update_question(
    request: Request,
    question_id: int,
    question_text: str = Form(...),
    answer_200: str = Form(""),
    rubric: str = Form(""),
    source_slide: int = Form(None),
    is_past_exam: bool = Form(False),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    question = db.query(Question).join(Card).join(Lecture).join(Subject).filter(
        Question.id == question_id, Subject.user_id == user.id
    ).first()

    if question:
        question.question_text = question_text
        question.answer_200 = answer_200
        question.rubric = rubric
        question.source_slide = source_slide
        question.is_past_exam = is_past_exam
        db.commit()
        return RedirectResponse(url=f"/questions?card_id={question.card_id}", status_code=302)
    return RedirectResponse(url="/questions", status_code=302)


@router.post("/{question_id}/delete")
async def delete_question(request: Request, question_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    question = db.query(Question).join(Card).join(Lecture).join(Subject).filter(
        Question.id == question_id, Subject.user_id == user.id
    ).first()

    if question:
        card_id = question.card_id
        db.delete(question)
        db.commit()
        return RedirectResponse(url=f"/questions?card_id={card_id}", status_code=302)
    return RedirectResponse(url="/questions", status_code=302)


@router.post("/{question_id}/attempt")
async def record_attempt(
    request: Request,
    question_id: int,
    score: int = Form(...),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    question = db.query(Question).join(Card).join(Lecture).join(Subject).filter(
        Question.id == question_id, Subject.user_id == user.id
    ).first()

    if question:
        attempt = Attempt(question_id=question_id, score=score)
        db.add(attempt)
        db.commit()
        return RedirectResponse(url=f"/questions?card_id={question.card_id}", status_code=302)
    return RedirectResponse(url="/questions", status_code=302)
