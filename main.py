from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database import engine, Base
from routers import subjects, lectures, cards, questions, prints, auth
from auth import get_current_user
from database import SessionLocal

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="MedPass", description="医学部定期試験対策Webアプリ")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(subjects.router, prefix="/subjects", tags=["subjects"])
app.include_router(lectures.router, prefix="/lectures", tags=["lectures"])
app.include_router(cards.router, prefix="/cards", tags=["cards"])
app.include_router(questions.router, prefix="/questions", tags=["questions"])
app.include_router(prints.router, prefix="/prints", tags=["prints"])


@app.get("/")
async def dashboard(request: Request):
    from models import Subject, Lecture, Card, Question, Attempt

    db = SessionLocal()
    try:
        user = get_current_user(request, db)
        if not user:
            return templates.TemplateResponse("auth/login.html", {
                "request": request,
                "error": None
            })

        # Get statistics for this user
        total_subjects = db.query(Subject).filter(Subject.user_id == user.id).count()
        total_lectures = db.query(Lecture).join(Subject).filter(Subject.user_id == user.id).count()
        total_cards = db.query(Card).join(Lecture).join(Subject).filter(Subject.user_id == user.id).count()
        total_questions = db.query(Question).join(Card).join(Lecture).join(Subject).filter(Subject.user_id == user.id).count()

        # Get recent subjects with their lectures
        subjects = db.query(Subject).filter(Subject.user_id == user.id).order_by(Subject.created_at.desc()).limit(5).all()

        # Calculate pass probability based on attempts
        from sqlalchemy import func
        user_attempts = db.query(Attempt).join(Question).join(Card).join(Lecture).join(Subject).filter(
            Subject.user_id == user.id
        )
        total_attempts = user_attempts.count()

        if total_attempts > 0:
            avg_score = user_attempts.with_entities(func.avg(Attempt.score)).scalar() or 0
            pass_probability = min(100, max(0, int(avg_score * 10)))
        else:
            pass_probability = 0

        # Get next 5 questions to study (questions with lowest scores or no attempts)
        next_questions = db.query(Question).join(Card).join(Lecture).join(Subject).outerjoin(Attempt).filter(
            Subject.user_id == user.id
        ).group_by(Question.id).order_by(
            func.coalesce(func.avg(Attempt.score), 0).asc()
        ).limit(5).all()

        return templates.TemplateResponse("index.html", {
            "request": request,
            "user": user,
            "total_subjects": total_subjects,
            "total_lectures": total_lectures,
            "total_cards": total_cards,
            "total_questions": total_questions,
            "subjects": subjects,
            "pass_probability": pass_probability,
            "next_questions": next_questions
        })
    finally:
        db.close()
