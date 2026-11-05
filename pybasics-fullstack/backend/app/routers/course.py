import datetime as dt
import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..database import get_db

router = APIRouter(prefix="/api/course", tags=["course"])

COURSE = json.loads((Path(__file__).parent.parent / "content" / "course.json").read_text(encoding="utf-8"))
COURSE_BY_DAY = {d["day"]: d for d in COURSE}
TOTAL_DAYS = len(COURSE)


def _today():
    return dt.date.today()


def _ensure_start(user: models.User, db: Session) -> dt.date:
    if user.course_start_date is None:
        user.course_start_date = _today()
        db.add(user)
        db.commit()
        db.refresh(user)
    return user.course_start_date


def _unlocked_day_count(user: models.User, db: Session) -> int:
    start = _ensure_start(user, db)
    diff = (_today() - start).days
    return max(1, min(TOTAL_DAYS, diff + 1))


def _completed_days(user: models.User, db: Session) -> set[int]:
    rows = db.query(models.LessonCompletion.day).filter(models.LessonCompletion.user_id == user.id).all()
    return {r[0] for r in rows}


def course_is_complete(user: models.User, db: Session) -> bool:
    return len(_completed_days(user, db)) >= TOTAL_DAYS


@router.get("/status", response_model=schemas.CourseStatusResponse)
def status(user: models.User = Depends(security.get_current_user), db: Session = Depends(get_db)):
    start = _ensure_start(user, db)
    unlocked = _unlocked_day_count(user, db)
    done = _completed_days(user, db)
    lessons = []
    for lsn in COURSE:
        day = lsn["day"]
        if day in done:
            st = "done"
        elif day <= unlocked:
            st = "available"
        else:
            st = "locked"
        unlocks_on = None
        if st == "locked":
            unlocks_on = (start + dt.timedelta(days=day - 1)).isoformat()
        lessons.append(schemas.LessonSummary(day=day, title=lsn["title"], status=st, unlocks_on=unlocks_on))
    return schemas.CourseStatusResponse(
        lessons=lessons, completed_count=len(done), total=TOTAL_DAYS,
        course_complete=len(done) >= TOTAL_DAYS,
    )


@router.get("/day/{day}", response_model=schemas.LessonContentResponse)
def get_day(day: int, user: models.User = Depends(security.get_current_user), db: Session = Depends(get_db)):
    lsn = COURSE_BY_DAY.get(day)
    if not lsn:
        raise HTTPException(status_code=404, detail="No such lesson.")
    unlocked = _unlocked_day_count(user, db)
    if day > unlocked:
        raise HTTPException(status_code=403, detail="This lesson hasn't unlocked yet.")
    quiz_public = [{"q": q["q"], "options": q["options"]} for q in lsn["quiz"]]
    already = day in _completed_days(user, db)
    return schemas.LessonContentResponse(
        day=day, title=lsn["title"], read=lsn["read"], code=lsn["code"], codeNote=lsn["codeNote"],
        query=lsn["query"], quiz=quiz_public, already_completed=already,
    )


@router.post("/day/{day}/submit", response_model=schemas.LessonQuizResult)
def submit_day(day: int, body: schemas.LessonQuizSubmit,
                user: models.User = Depends(security.get_current_user), db: Session = Depends(get_db)):
    lsn = COURSE_BY_DAY.get(day)
    if not lsn:
        raise HTTPException(status_code=404, detail="No such lesson.")
    unlocked = _unlocked_day_count(user, db)
    if day > unlocked:
        raise HTTPException(status_code=403, detail="This lesson hasn't unlocked yet.")
    quiz = lsn["quiz"]
    if len(body.answers) != len(quiz):
        raise HTTPException(status_code=400, detail=f"Expected {len(quiz)} answers.")
    results = []
    score = 0
    for ans, q in zip(body.answers, quiz):
        ok = ans == q["correct"]
        if ok:
            score += 1
        results.append({"correct": ok, "correct_index": q["correct"], "explain": q["explain"]})
    passed = score == len(quiz)
    if passed:
        existing = db.query(models.LessonCompletion).filter(
            models.LessonCompletion.user_id == user.id, models.LessonCompletion.day == day
        ).first()
        if not existing:
            db.add(models.LessonCompletion(user_id=user.id, day=day))
            db.commit()
    return schemas.LessonQuizResult(score=score, total=len(quiz), passed=passed, results=results)
