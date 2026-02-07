from fastapi import APIRouter, Depends, Request, Form, UploadFile, File
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models import Lecture, Subject, Card
from auth import get_current_user
from services.card_generator import extract_themes_from_content, is_api_configured
from services.pdf_extractor import extract_text_from_pdf

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


@router.post("/{lecture_id}/upload-pdf")
async def upload_pdf(
    request: Request,
    lecture_id: int,
    pdf_file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload PDF and extract text content."""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    lecture = db.query(Lecture).join(Subject).filter(
        Lecture.id == lecture_id, Subject.user_id == user.id
    ).first()

    if not lecture:
        return RedirectResponse(url="/lectures", status_code=302)

    # Validate file type
    if not pdf_file.filename.lower().endswith('.pdf'):
        return RedirectResponse(url=f"/lectures/{lecture_id}?error=pdf_only", status_code=302)

    try:
        # Read PDF bytes
        pdf_bytes = await pdf_file.read()

        # Extract text from PDF
        extracted_text, page_count = extract_text_from_pdf(pdf_bytes)

        # Update lecture content and slide count
        if lecture.content:
            lecture.content = lecture.content + "\n\n" + extracted_text
        else:
            lecture.content = extracted_text
        lecture.slide_count = page_count
        db.commit()

        return RedirectResponse(url=f"/lectures/{lecture_id}", status_code=302)

    except ValueError as e:
        return RedirectResponse(url=f"/lectures/{lecture_id}?error=pdf_error", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/lectures/{lecture_id}?error=upload_error", status_code=302)


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


@router.post("/{lecture_id}/generate-cards")
async def generate_cards(request: Request, lecture_id: int, db: Session = Depends(get_db)):
    """Generate cards automatically from lecture OCR content using Claude API."""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    lecture = db.query(Lecture).join(Subject).filter(
        Lecture.id == lecture_id, Subject.user_id == user.id
    ).first()

    if not lecture:
        return RedirectResponse(url="/lectures", status_code=302)

    if not lecture.content:
        # No content to generate from
        return RedirectResponse(url=f"/lectures/{lecture_id}", status_code=302)

    if not is_api_configured():
        # API not configured
        return RedirectResponse(url=f"/lectures/{lecture_id}", status_code=302)

    # Generate cards using Claude API
    themes = extract_themes_from_content(lecture.content)

    # Create cards in database
    for theme_data in themes:
        card = Card(
            lecture_id=lecture_id,
            theme=theme_data["theme"],
            summary=theme_data["summary"],
            importance=theme_data["importance"]
        )
        db.add(card)

    db.commit()

    return RedirectResponse(url=f"/lectures/{lecture_id}", status_code=302)


@router.get("/{lecture_id}/api-status")
async def check_api_status(request: Request, lecture_id: int, db: Session = Depends(get_db)):
    """Check if Anthropic API is configured."""
    user = get_current_user(request, db)
    if not user:
        return {"configured": False}

    return {"configured": is_api_configured()}
