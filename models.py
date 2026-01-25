from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    username = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    subjects = relationship("Subject", back_populates="user", cascade="all, delete-orphan")


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="subjects")
    lectures = relationship("Lecture", back_populates="subject", cascade="all, delete-orphan")


class Lecture(Base):
    __tablename__ = "lectures"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, default="")
    slide_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    subject = relationship("Subject", back_populates="lectures")
    cards = relationship("Card", back_populates="lecture", cascade="all, delete-orphan")
    prints = relationship("Print", back_populates="lecture", cascade="all, delete-orphan")


class Card(Base):
    __tablename__ = "cards"

    id = Column(Integer, primary_key=True, index=True)
    lecture_id = Column(Integer, ForeignKey("lectures.id"), nullable=False)
    theme = Column(String(200), nullable=False)
    summary = Column(Text, default="")
    importance = Column(Integer, default=2)  # 1-3
    created_at = Column(DateTime, default=datetime.utcnow)

    lecture = relationship("Lecture", back_populates="cards")
    questions = relationship("Question", back_populates="card", cascade="all, delete-orphan")


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    card_id = Column(Integer, ForeignKey("cards.id"), nullable=False)
    question_text = Column(Text, nullable=False)
    answer_200 = Column(Text, default="")
    rubric = Column(Text, default="")
    source_slide = Column(Integer, nullable=True)
    is_past_exam = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    card = relationship("Card", back_populates="questions")
    attempts = relationship("Attempt", back_populates="question", cascade="all, delete-orphan")


class Attempt(Base):
    __tablename__ = "attempts"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    score = Column(Integer, default=0)
    attempted_at = Column(DateTime, default=datetime.utcnow)

    question = relationship("Question", back_populates="attempts")


class Print(Base):
    __tablename__ = "prints"

    id = Column(Integer, primary_key=True, index=True)
    lecture_id = Column(Integer, ForeignKey("lectures.id"), nullable=False)
    pdf_path = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    lecture = relationship("Lecture", back_populates="prints")
