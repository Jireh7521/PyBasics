import datetime as dt

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Date, ForeignKey, JSON, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship

from .database import Base


def utcnow():
    return dt.datetime.utcnow()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    full_name = Column(String(80), nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=utcnow)
    course_start_date = Column(Date, nullable=True)  # set the first time they open the class

    lesson_completions = relationship("LessonCompletion", back_populates="user", cascade="all, delete-orphan")
    level_progress = relationship("LevelProgress", back_populates="user", cascade="all, delete-orphan")
    exam_attempts = relationship("ExamAttempt", back_populates="user", cascade="all, delete-orphan")


class LessonCompletion(Base):
    __tablename__ = "lesson_completions"
    __table_args__ = (UniqueConstraint("user_id", "day", name="uq_user_day"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    day = Column(Integer, nullable=False)
    completed_at = Column(DateTime, default=utcnow)

    user = relationship("User", back_populates="lesson_completions")


class LevelProgress(Base):
    __tablename__ = "level_progress"
    __table_args__ = (UniqueConstraint("user_id", "level", name="uq_user_level"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    level = Column(Integer, nullable=False)
    best_score = Column(Integer, default=0)
    passed = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="level_progress")


class ExamAttempt(Base):
    """One attempt at one level. questions_json holds the server-generated
    question set (WITH correct answers) so the frontend never receives them
    until after it answers — grading always happens here, server-side."""
    __tablename__ = "exam_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    level = Column(Integer, nullable=False)
    questions_json = Column(JSON, nullable=False)
    current_index = Column(Integer, default=0)
    score = Column(Integer, default=0)
    first_try_remaining = Column(Boolean, default=True)  # for code levels: was current Q solved first try
    status = Column(String(20), default="in_progress")  # in_progress | finished | abandoned
    started_at = Column(DateTime, default=utcnow)
    finished_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="exam_attempts")


class AppSetting(Base):
    """Small global key/value store — used for the director's signature image
    (a data: URL), shared across every user/device rather than per-browser."""
    __tablename__ = "app_settings"

    key = Column(String(50), primary_key=True)
    value = Column(Text, nullable=True)
