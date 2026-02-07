from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database import engine, Base
from routers import subjects, lectures, cards, questions, prints, auth, study, past_exams
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
app.include_router(study.router, prefix="/study", tags=["study"])
app.include_router(past_exams.router, prefix="/past-exams", tags=["past-exams"])


def calculate_pass_probabilities(db, user_id):
    """
    Calculate pass probabilities for 60/80/90 point thresholds.

    Uses weighted scoring based on:
    - Question scores (0-10)
    - Card importance (1-3, used as weight multiplier)
    - Study coverage (answered vs total questions)
    """
    from models import Subject, Lecture, Card, Question, Attempt
    from sqlalchemy import func

    # Get all questions with their card importance for this user
    questions_with_importance = db.query(
        Question.id,
        Card.importance,
        func.coalesce(func.max(Attempt.score), -1).label('best_score')  # -1 = not attempted
    ).join(Card).join(Lecture).join(Subject).outerjoin(Attempt).filter(
        Subject.user_id == user_id
    ).group_by(Question.id, Card.importance).all()

    if not questions_with_importance:
        return {
            'prob_60': 0,
            'prob_80': 0,
            'prob_90': 0,
            'weighted_score': 0,
            'coverage': 0,
            'studied_count': 0,
            'total_count': 0
        }

    total_weight = 0
    weighted_score_sum = 0
    studied_count = 0

    for q_id, importance, best_score in questions_with_importance:
        weight = importance  # importance 1-3 as weight
        total_weight += weight

        if best_score >= 0:  # Has been attempted
            studied_count += 1
            weighted_score_sum += best_score * weight
        # Unattempted questions contribute 0 to the score

    total_count = len(questions_with_importance)
    coverage = (studied_count / total_count * 100) if total_count > 0 else 0

    # Calculate weighted average score (0-10 scale)
    weighted_avg = (weighted_score_sum / total_weight) if total_weight > 0 else 0

    # Calculate probabilities based on current performance and coverage
    # Formula: probability = (weighted_score / threshold) * coverage_factor
    # Coverage factor: studied questions contribute more certainty
    coverage_factor = min(1.0, studied_count / max(total_count * 0.7, 1))  # 70% coverage = full confidence

    # Convert to probability (0-100%)
    # If weighted_avg >= threshold (6/8/9 for 60/80/90), high probability
    def calc_prob(threshold_score):
        if total_count == 0:
            return 0
        # Base probability from score ratio
        score_ratio = weighted_avg / threshold_score if threshold_score > 0 else 0
        # Adjust by coverage
        raw_prob = score_ratio * coverage_factor * 100
        return min(100, max(0, int(raw_prob)))

    return {
        'prob_60': calc_prob(6),
        'prob_80': calc_prob(8),
        'prob_90': calc_prob(9),
        'weighted_score': round(weighted_avg * 10, 1),  # Convert to 100-point scale
        'coverage': round(coverage, 1),
        'studied_count': studied_count,
        'total_count': total_count
    }


@app.get("/")
async def dashboard(request: Request):
    from models import Subject, Lecture, Card, Question, Attempt
    from sqlalchemy import func

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

        # Calculate pass probabilities (60/80/90)
        pass_stats = calculate_pass_probabilities(db, user.id)

        # Get next 5 questions to study
        # Priority: high importance + low score + not recently attempted
        next_questions = db.query(Question).join(Card).join(Lecture).join(Subject).outerjoin(Attempt).filter(
            Subject.user_id == user.id
        ).group_by(Question.id).order_by(
            # Prioritize: importance DESC, then score ASC (unattempted = 0)
            Card.importance.desc(),
            func.coalesce(func.max(Attempt.score), 0).asc()
        ).limit(5).all()

        # Get uncovered themes (cards with no past exam questions)
        # Subquery to find cards that have at least one past exam question
        cards_with_past_exam = db.query(Card.id).join(Question).filter(
            Question.is_past_exam == True
        ).subquery()

        uncovered_themes = db.query(Card).join(Lecture).join(Subject).filter(
            Subject.user_id == user.id,
            ~Card.id.in_(db.query(cards_with_past_exam))
        ).order_by(Card.importance.desc()).limit(5).all()

        # Calculate past exam coverage per subject
        subject_coverage = []
        user_subjects = db.query(Subject).filter(Subject.user_id == user.id).all()
        for subj in user_subjects:
            total_cards = db.query(Card).join(Lecture).filter(Lecture.subject_id == subj.id).count()
            covered_cards = db.query(Card).join(Lecture).join(Question).filter(
                Lecture.subject_id == subj.id,
                Question.is_past_exam == True
            ).distinct().count()
            if total_cards > 0:
                coverage_pct = int(covered_cards / total_cards * 100)
                subject_coverage.append({
                    'subject': subj,
                    'total_cards': total_cards,
                    'covered_cards': covered_cards,
                    'coverage_pct': coverage_pct
                })

        return templates.TemplateResponse("index.html", {
            "request": request,
            "user": user,
            "total_subjects": total_subjects,
            "total_lectures": total_lectures,
            "total_cards": total_cards,
            "total_questions": total_questions,
            "subjects": subjects,
            "pass_stats": pass_stats,
            "next_questions": next_questions,
            "uncovered_themes": uncovered_themes,
            "subject_coverage": subject_coverage
        })
    finally:
        db.close()
