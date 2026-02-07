"""
Study mode router.
Provides flashcard-style learning interface.
"""

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import Question, Card, Lecture, Subject, Attempt
from auth import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/")
async def study_home(request: Request, db: Session = Depends(get_db)):
    """Study mode home - select what to study."""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    # Get subjects with question counts
    subjects = db.query(Subject).filter(Subject.user_id == user.id).all()

    subject_stats = []
    for subject in subjects:
        question_count = db.query(Question).join(Card).join(Lecture).filter(
            Lecture.subject_id == subject.id
        ).count()

        if question_count > 0:
            subject_stats.append({
                "subject": subject,
                "question_count": question_count
            })

    # Get total question count
    total_questions = db.query(Question).join(Card).join(Lecture).join(Subject).filter(
        Subject.user_id == user.id
    ).count()

    return templates.TemplateResponse("study/home.html", {
        "request": request,
        "user": user,
        "subject_stats": subject_stats,
        "total_questions": total_questions
    })


@router.get("/session")
async def study_session(
    request: Request,
    subject_id: int = None,
    lecture_id: int = None,
    mode: str = "all",
    db: Session = Depends(get_db)
):
    """Start or continue a study session."""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    # Build query based on filters
    query = db.query(Question).join(Card).join(Lecture).join(Subject).filter(
        Subject.user_id == user.id
    )

    if subject_id:
        query = query.filter(Subject.id == subject_id)
    if lecture_id:
        query = query.filter(Lecture.id == lecture_id)

    # Apply mode filters
    if mode == "weak":
        # Questions with low scores (< 7) or not attempted
        subquery = db.query(
            Attempt.question_id,
            func.max(Attempt.score).label("best_score")
        ).group_by(Attempt.question_id).subquery()

        query = query.outerjoin(subquery, Question.id == subquery.c.question_id).filter(
            (subquery.c.best_score < 7) | (subquery.c.best_score == None)
        )
    elif mode == "unattempted":
        # Questions never attempted
        attempted_ids = db.query(Attempt.question_id).distinct()
        query = query.filter(~Question.id.in_(attempted_ids))
    elif mode == "high_importance":
        # Only high importance cards
        query = query.filter(Card.importance == 3)

    # Order by importance (desc) then random
    questions = query.order_by(Card.importance.desc(), func.random()).all()

    if not questions:
        return templates.TemplateResponse("study/no_questions.html", {
            "request": request,
            "user": user,
            "subject_id": subject_id,
            "lecture_id": lecture_id,
            "mode": mode
        })

    # Get current question index from session or start at 0
    current_index = 0

    return templates.TemplateResponse("study/session.html", {
        "request": request,
        "user": user,
        "questions": questions,
        "current_index": current_index,
        "current_question": questions[0],
        "total_count": len(questions),
        "subject_id": subject_id,
        "lecture_id": lecture_id,
        "mode": mode,
        "show_answer": False
    })


@router.get("/session/{question_id}")
async def study_question(
    request: Request,
    question_id: int,
    show_answer: bool = False,
    subject_id: int = None,
    lecture_id: int = None,
    mode: str = "all",
    current_index: int = 0,
    total_count: int = 0,
    db: Session = Depends(get_db)
):
    """View a specific question in study mode."""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    question = db.query(Question).join(Card).join(Lecture).join(Subject).filter(
        Question.id == question_id,
        Subject.user_id == user.id
    ).first()

    if not question:
        return RedirectResponse(url="/study", status_code=302)

    # Get best score for this question
    best_attempt = db.query(Attempt).filter(
        Attempt.question_id == question_id
    ).order_by(Attempt.score.desc()).first()

    return templates.TemplateResponse("study/question.html", {
        "request": request,
        "user": user,
        "question": question,
        "show_answer": show_answer,
        "best_score": best_attempt.score if best_attempt else None,
        "subject_id": subject_id,
        "lecture_id": lecture_id,
        "mode": mode,
        "current_index": current_index,
        "total_count": total_count
    })


@router.post("/session/{question_id}/score")
async def record_score(
    request: Request,
    question_id: int,
    score: int = Form(...),
    next_question_id: int = Form(None),
    subject_id: int = Form(None),
    lecture_id: int = Form(None),
    mode: str = Form("all"),
    current_index: int = Form(0),
    total_count: int = Form(0),
    db: Session = Depends(get_db)
):
    """Record score and move to next question."""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    # Verify question belongs to user
    question = db.query(Question).join(Card).join(Lecture).join(Subject).filter(
        Question.id == question_id,
        Subject.user_id == user.id
    ).first()

    if question:
        # Record attempt
        attempt = Attempt(question_id=question_id, score=score)
        db.add(attempt)
        db.commit()

    # Move to next question or finish
    if next_question_id:
        params = f"?show_answer=false&subject_id={subject_id or ''}&lecture_id={lecture_id or ''}&mode={mode}&current_index={current_index + 1}&total_count={total_count}"
        return RedirectResponse(url=f"/study/session/{next_question_id}{params}", status_code=302)
    else:
        # Session complete
        return RedirectResponse(url="/study/complete", status_code=302)


@router.get("/complete")
async def study_complete(request: Request, db: Session = Depends(get_db)):
    """Study session complete page."""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    return templates.TemplateResponse("study/complete.html", {
        "request": request,
        "user": user
    })
