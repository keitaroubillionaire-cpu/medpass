from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


# Subject schemas
class SubjectBase(BaseModel):
    name: str


class SubjectCreate(SubjectBase):
    pass


class Subject(SubjectBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Lecture schemas
class LectureBase(BaseModel):
    title: str
    content: Optional[str] = ""
    slide_count: Optional[int] = 0


class LectureCreate(LectureBase):
    subject_id: int


class Lecture(LectureBase):
    id: int
    subject_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Card schemas
class CardBase(BaseModel):
    theme: str
    summary: Optional[str] = ""
    importance: Optional[int] = 2


class CardCreate(CardBase):
    lecture_id: int


class Card(CardBase):
    id: int
    lecture_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Question schemas
class QuestionBase(BaseModel):
    question_text: str
    answer_200: Optional[str] = ""
    rubric: Optional[str] = ""
    source_slide: Optional[int] = None
    is_past_exam: Optional[bool] = False


class QuestionCreate(QuestionBase):
    card_id: int


class Question(QuestionBase):
    id: int
    card_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Attempt schemas
class AttemptBase(BaseModel):
    score: int


class AttemptCreate(AttemptBase):
    question_id: int


class Attempt(AttemptBase):
    id: int
    question_id: int
    attempted_at: datetime

    class Config:
        from_attributes = True


# Print schemas
class PrintBase(BaseModel):
    pdf_path: str


class PrintCreate(PrintBase):
    lecture_id: int


class Print(PrintBase):
    id: int
    lecture_id: int
    created_at: datetime

    class Config:
        from_attributes = True
