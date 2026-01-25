import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

# Use PostgreSQL if DATABASE_URL is set, otherwise SQLite
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Fix for Render's postgres:// URL (SQLAlchemy requires postgresql://)
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    engine = create_engine(DATABASE_URL)
else:
    # Local development with SQLite
    SQLALCHEMY_DATABASE_URL = "sqlite:///./medpass.db"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
