"""
Past exams router.
Handles past exam PDF upload and management.
"""

from fastapi import APIRouter, Depends, Request, Form, UploadFile, File
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models import Subject, Lecture, Card, Question
from auth import get_current_user
from services.pdf_extractor import extract_text_from_pdf
from services.past_exam_parser import (
    parse_past_exam_pdf,
    parse_past_exam_image,
    match_question_to_card,
    is_api_configured,
    is_supported_image,
    get_media_type
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/")
async def past_exams_home(request: Request, db: Session = Depends(get_db)):
    """Past exams upload page."""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    # Get user's subjects
    subjects = db.query(Subject).filter(Subject.user_id == user.id).all()

    # Get past exam questions count per subject
    subject_stats = []
    for subject in subjects:
        past_exam_count = db.query(Question).join(Card).join(Lecture).filter(
            Lecture.subject_id == subject.id,
            Question.is_past_exam == True
        ).count()

        total_questions = db.query(Question).join(Card).join(Lecture).filter(
            Lecture.subject_id == subject.id
        ).count()

        subject_stats.append({
            "subject": subject,
            "past_exam_count": past_exam_count,
            "total_questions": total_questions
        })

    return templates.TemplateResponse("past_exams/home.html", {
        "request": request,
        "user": user,
        "subject_stats": subject_stats,
        "api_configured": is_api_configured()
    })


@router.get("/upload/{subject_id}")
async def upload_page(request: Request, subject_id: int, db: Session = Depends(get_db)):
    """Past exam upload page for a specific subject."""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    subject = db.query(Subject).filter(
        Subject.id == subject_id,
        Subject.user_id == user.id
    ).first()

    if not subject:
        return RedirectResponse(url="/past-exams", status_code=302)

    # Get lectures for this subject (to select which lecture to attach questions to)
    lectures = db.query(Lecture).filter(Lecture.subject_id == subject_id).all()

    return templates.TemplateResponse("past_exams/upload.html", {
        "request": request,
        "user": user,
        "subject": subject,
        "lectures": lectures,
        "api_configured": is_api_configured()
    })


@router.post("/upload/{subject_id}")
async def upload_past_exam(
    request: Request,
    subject_id: int,
    exam_file: UploadFile = File(...),
    lecture_id: int = Form(None),
    db: Session = Depends(get_db)
):
    """Upload and parse past exam PDF or image."""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    subject = db.query(Subject).filter(
        Subject.id == subject_id,
        Subject.user_id == user.id
    ).first()

    if not subject:
        return RedirectResponse(url="/past-exams", status_code=302)

    filename = exam_file.filename.lower()
    is_pdf = filename.endswith('.pdf')
    is_image = is_supported_image(filename)

    # Validate file type
    if not is_pdf and not is_image:
        return RedirectResponse(
            url=f"/past-exams/upload/{subject_id}?error=invalid_file",
            status_code=302
        )

    if not is_api_configured():
        return RedirectResponse(
            url=f"/past-exams/upload/{subject_id}?error=api_not_configured",
            status_code=302
        )

    try:
        # Read file bytes
        file_bytes = await exam_file.read()

        # Parse based on file type
        if is_pdf:
            # Extract text from PDF
            extracted_text, page_count = extract_text_from_pdf(file_bytes)

            if not extracted_text or len(extracted_text.strip()) < 50:
                return RedirectResponse(
                    url=f"/past-exams/upload/{subject_id}?error=no_text",
                    status_code=302
                )

            # Parse questions using AI
            parsed_questions = parse_past_exam_pdf(extracted_text)
        else:
            # Parse image using Vision API
            media_type = get_media_type(exam_file.filename)
            parsed_questions = parse_past_exam_image(file_bytes, media_type)

        if not parsed_questions:
            return RedirectResponse(
                url=f"/past-exams/upload/{subject_id}?error=parse_failed",
                status_code=302
            )

        # Get existing cards for matching
        if lecture_id:
            cards = db.query(Card).filter(Card.lecture_id == lecture_id).all()
        else:
            cards = db.query(Card).join(Lecture).filter(
                Lecture.subject_id == subject_id
            ).all()

        # If no lecture specified and no cards exist, create a default lecture
        if not lecture_id and not cards:
            default_lecture = Lecture(
                subject_id=subject_id,
                title="過去問（自動作成）",
                content=""
            )
            db.add(default_lecture)
            db.commit()
            lecture_id = default_lecture.id

        # Create questions
        created_count = 0
        for q_data in parsed_questions:
            # Try to match to existing card
            matched_card_id = match_question_to_card(q_data["theme"], cards)

            if matched_card_id:
                card_id = matched_card_id
            else:
                # Create new card for this question
                target_lecture_id = lecture_id
                if not target_lecture_id:
                    # Use first available lecture
                    first_lecture = db.query(Lecture).filter(
                        Lecture.subject_id == subject_id
                    ).first()
                    if first_lecture:
                        target_lecture_id = first_lecture.id
                    else:
                        # Create default lecture
                        new_lecture = Lecture(
                            subject_id=subject_id,
                            title="過去問（自動作成）",
                            content=""
                        )
                        db.add(new_lecture)
                        db.commit()
                        target_lecture_id = new_lecture.id

                new_card = Card(
                    lecture_id=target_lecture_id,
                    theme=q_data["theme"] or "過去問",
                    summary="",
                    importance=q_data["importance"]
                )
                db.add(new_card)
                db.commit()
                card_id = new_card.id

            # Create question
            question = Question(
                card_id=card_id,
                question_text=q_data["question_text"],
                answer_200=q_data["answer"],
                rubric="",
                is_past_exam=True
            )
            db.add(question)
            created_count += 1

        db.commit()

        return RedirectResponse(
            url=f"/past-exams/result?subject_id={subject_id}&count={created_count}",
            status_code=302
        )

    except ValueError as e:
        return RedirectResponse(
            url=f"/past-exams/upload/{subject_id}?error=pdf_error",
            status_code=302
        )
    except Exception as e:
        print(f"Error uploading past exam: {e}")
        return RedirectResponse(
            url=f"/past-exams/upload/{subject_id}?error=upload_error",
            status_code=302
        )


@router.get("/result")
async def upload_result(
    request: Request,
    subject_id: int,
    count: int,
    db: Session = Depends(get_db)
):
    """Show upload result."""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    subject = db.query(Subject).filter(
        Subject.id == subject_id,
        Subject.user_id == user.id
    ).first()

    return templates.TemplateResponse("past_exams/result.html", {
        "request": request,
        "user": user,
        "subject": subject,
        "count": count
    })
