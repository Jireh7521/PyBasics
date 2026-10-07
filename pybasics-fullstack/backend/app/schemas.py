from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


class SignupRequest(BaseModel):
    username: str
    password: str
    full_name: str

    @field_validator("username")
    @classmethod
    def username_ok(cls, v):
        v = v.strip()
        if not (3 <= len(v) <= 30):
            raise ValueError("Username must be 3-30 characters.")
        if not all(c.isalnum() or c in "_-." for c in v):
            raise ValueError("Username can only contain letters, numbers, _ - .")
        return v

    @field_validator("password")
    @classmethod
    def password_ok(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters.")
        return v

    @field_validator("full_name")
    @classmethod
    def full_name_ok(cls, v):
        v = " ".join(v.strip().split())
        if len(v.split(" ")) < 2:
            raise ValueError("Please enter your full name (first and last) \u2014 it will appear on your certificate.")
        if len(v) > 60:
            raise ValueError("That name is too long \u2014 please keep it under 60 characters.")
        return v


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    full_name: str
    username: str


class MeResponse(BaseModel):
    username: str
    full_name: str
    created_at: datetime


class LessonSummary(BaseModel):
    day: int
    title: str
    status: str  # "locked" | "available" | "done"
    unlocks_on: Optional[str] = None


class CourseStatusResponse(BaseModel):
    lessons: list[LessonSummary]
    completed_count: int
    total: int
    course_complete: bool


class LessonContentResponse(BaseModel):
    day: int
    title: str
    read: str
    code: str
    codeNote: str
    query: str
    quiz: list[dict]  # questions WITHOUT 'correct' -- stripped before sending
    already_completed: bool


class LessonQuizSubmit(BaseModel):
    answers: list[int]


class LessonQuizResult(BaseModel):
    score: int
    total: int
    passed: bool
    results: list[dict]  # per-question {correct: bool, correct_index: int, explain: str}


class LevelSummary(BaseModel):
    level: int
    name: str
    difficulty: str
    count: int
    type: str
    status: str  # "locked" | "available" | "passed"
    best_score: Optional[int] = None


class ExamOverviewResponse(BaseModel):
    course_complete: bool
    levels: list[LevelSummary]
    certificate_ready: bool


class StartAttemptResponse(BaseModel):
    attempt_id: int
    level: int
    type: str
    total: int
    question_index: int
    question: dict  # sanitized -- no 'correct'/'expected'


class McqAnswerSubmit(BaseModel):
    selected: int


class CodeAnswerSubmit(BaseModel):
    code: str


class AnswerResult(BaseModel):
    correct: bool
    finished: bool
    score: int
    total: int
    explain: Optional[str] = None
    correct_option: Optional[int] = None
    var_results: Optional[list[dict]] = None
    error: Optional[str] = None
    next_question: Optional[dict] = None
    question_index: Optional[int] = None


class FinishAttemptResponse(BaseModel):
    level: int
    score: int
    total: int
    passed: bool
    next_level_unlocked: Optional[int] = None


class CertificateResponse(BaseModel):
    full_name: str
    issued_date: str
    total_score: int
    total_questions: int
    eligible: bool
    signature_url: Optional[str] = None


class SignatureUpload(BaseModel):
    data_url: str
