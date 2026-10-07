import datetime as dt
import random

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..database import get_db
from ..content.exam_mcq import MCQ_POOLS
from ..content.exam_code import CODE_POOLS
from ..sandbox import run_user_code, values_equal
from .course import course_is_complete

router = APIRouter(prefix="/api/exam", tags=["exam"])

PASS_RATIO = 0.75

LEVELS = [
    {"level": 1, "name": "Level 1", "difficulty": "Beginner", "count": 10, "type": "mcq",
     "pools": ["T_arithmetic", "T_type", "T_boolean"]},
    {"level": 2, "name": "Level 2", "difficulty": "Basic", "count": 10, "type": "mcq",
     "pools": ["T_arithmetic", "T_type", "T_boolean", "T_string", "T_conversion"]},
    {"level": 3, "name": "Level 3", "difficulty": "Intermediate", "count": 10, "type": "mcq",
     "pools": ["T_arithmetic", "T_type", "T_boolean", "T_string", "T_conversion", "T_list", "T_conditional"]},
    {"level": 4, "name": "Level 4", "difficulty": "Advanced", "count": 10, "type": "code",
     "pools": ["C_arith", "C_divmod", "C_string", "C_list", "C_convert", "C_dict", "C_bool"]},
    {"level": 5, "name": "Level 5", "difficulty": "Expert", "count": 10, "type": "code",
     "pools": ["H_arith", "H_string", "H_list", "H_dict", "H_cond", "H_mix"]},
]
LEVELS_BY_ID = {lv["level"]: lv for lv in LEVELS}


def _level_progress_map(user: models.User, db: Session) -> dict[int, models.LevelProgress]:
    rows = db.query(models.LevelProgress).filter(models.LevelProgress.user_id == user.id).all()
    return {r.level: r for r in rows}


def _level_status(level: int, progress: dict, course_done: bool) -> str:
    if level == 1:
        if not course_done:
            return "locked"
    else:
        prev = progress.get(level - 1)
        if not prev or not prev.passed:
            return "locked"
    cur = progress.get(level)
    if cur and cur.passed:
        return "passed"
    return "available"


def _public_question(q: dict, qtype: str) -> dict:
    if qtype == "mcq":
        return {"topic": q["topic"], "q": q["q"], "code": q.get("code")}
    return {"topic": q["topic"], "kind": "code", "q": q["q"], "starter": q["starter"]}


@router.get("/overview", response_model=schemas.ExamOverviewResponse)
def overview(user: models.User = Depends(security.get_current_user), db: Session = Depends(get_db)):
    course_done = course_is_complete(user, db)
    progress = _level_progress_map(user, db)
    levels = []
    for lv in LEVELS:
        st = _level_status(lv["level"], progress, course_done)
        best = progress.get(lv["level"])
        levels.append(schemas.LevelSummary(
            level=lv["level"], name=lv["name"], difficulty=lv["difficulty"], count=lv["count"], type=lv["type"],
            status=st, best_score=(best.best_score if best else None),
        ))
    cert_ready = all((progress.get(i) and progress[i].passed) for i in range(1, 6))
    return schemas.ExamOverviewResponse(course_complete=course_done, levels=levels, certificate_ready=cert_ready)


@router.post("/level/{level}/start", response_model=schemas.StartAttemptResponse)
def start_level(level: int, user: models.User = Depends(security.get_current_user), db: Session = Depends(get_db)):
    lv = LEVELS_BY_ID.get(level)
    if not lv:
        raise HTTPException(status_code=404, detail="No such level.")
    course_done = course_is_complete(user, db)
    progress = _level_progress_map(user, db)
    if _level_status(level, progress, course_done) == "locked":
        raise HTTPException(status_code=403, detail="This level is locked.")

    # abandon any stale in-progress attempts of this level for this user
    db.query(models.ExamAttempt).filter(
        models.ExamAttempt.user_id == user.id, models.ExamAttempt.level == level,
        models.ExamAttempt.status == "in_progress",
    ).update({"status": "abandoned"})

    pool_fns = [(MCQ_POOLS if lv["type"] == "mcq" else CODE_POOLS)[name] for name in lv["pools"]]
    questions = [random.choice(pool_fns)() for _ in range(lv["count"])]

    attempt = models.ExamAttempt(
        user_id=user.id, level=level, questions_json=questions,
        current_index=0, score=0, first_try_remaining=True, status="in_progress",
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    return schemas.StartAttemptResponse(
        attempt_id=attempt.id, level=level, type=lv["type"], total=lv["count"],
        question_index=0, question=_public_question(questions[0], lv["type"]),
    )


def _get_active_attempt(attempt_id: int, user: models.User, db: Session) -> models.ExamAttempt:
    attempt = db.query(models.ExamAttempt).filter(
        models.ExamAttempt.id == attempt_id, models.ExamAttempt.user_id == user.id,
    ).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="No such attempt.")
    if attempt.status != "in_progress":
        raise HTTPException(status_code=409, detail="This attempt is no longer active. Start the level again.")
    return attempt


@router.post("/attempt/{attempt_id}/abandon")
def abandon(attempt_id: int, user: models.User = Depends(security.get_current_user), db: Session = Depends(get_db)):
    attempt = db.query(models.ExamAttempt).filter(
        models.ExamAttempt.id == attempt_id, models.ExamAttempt.user_id == user.id,
    ).first()
    if attempt and attempt.status == "in_progress":
        attempt.status = "abandoned"
        db.add(attempt)
        db.commit()
    return {"ok": True}


def _finish_attempt(attempt: models.ExamAttempt, db: Session) -> dict:
    lv = LEVELS_BY_ID[attempt.level]
    attempt.status = "finished"
    attempt.finished_at = dt.datetime.utcnow()
    db.add(attempt)

    passed_now = (attempt.score / lv["count"]) >= PASS_RATIO
    row = db.query(models.LevelProgress).filter(
        models.LevelProgress.user_id == attempt.user_id, models.LevelProgress.level == attempt.level,
    ).first()
    if not row:
        row = models.LevelProgress(user_id=attempt.user_id, level=attempt.level, best_score=0, passed=False)
    row.best_score = max(row.best_score, attempt.score)
    row.passed = row.passed or passed_now
    db.add(row)
    db.commit()
    return {"passed": row.passed, "best_score": row.best_score}


@router.post("/attempt/{attempt_id}/answer/mcq", response_model=schemas.AnswerResult)
def answer_mcq(attempt_id: int, body: schemas.McqAnswerSubmit,
                user: models.User = Depends(security.get_current_user), db: Session = Depends(get_db)):
    attempt = _get_active_attempt(attempt_id, user, db)
    lv = LEVELS_BY_ID[attempt.level]
    if lv["type"] != "mcq":
        raise HTTPException(status_code=400, detail="This attempt is not a multiple-choice level.")
    q = attempt.questions_json[attempt.current_index]
    correct = body.selected == q["correct"]
    if correct:
        attempt.score += 1
    attempt.current_index += 1
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    finished = attempt.current_index >= lv["count"]
    result = schemas.AnswerResult(
        correct=correct, finished=finished, score=attempt.score, total=lv["count"],
        explain=q["explain"], correct_option=q["correct"], question_index=attempt.current_index,
    )
    if finished:
        _finish_attempt(attempt, db)
    else:
        nxt = attempt.questions_json[attempt.current_index]
        result.next_question = _public_question(nxt, "mcq")
    return result


@router.post("/attempt/{attempt_id}/answer/code", response_model=schemas.AnswerResult)
def answer_code(attempt_id: int, body: schemas.CodeAnswerSubmit,
                 user: models.User = Depends(security.get_current_user), db: Session = Depends(get_db)):
    attempt = _get_active_attempt(attempt_id, user, db)
    lv = LEVELS_BY_ID[attempt.level]
    if lv["type"] != "code":
        raise HTTPException(status_code=400, detail="This attempt is not a code level.")
    q = attempt.questions_json[attempt.current_index]

    run = run_user_code(body.code)
    var_results = []
    all_ok = run["ok"]
    if run["ok"]:
        for key, want in q["expected"].items():
            got = run["vars"].get(key, "__missing__")
            ok = got != "__missing__" and values_equal(got, want)
            all_ok = all_ok and ok
            var_results.append({"name": key, "correct": ok})

    if not all_ok:
        attempt.first_try_remaining = False
        db.add(attempt)
        db.commit()
        return schemas.AnswerResult(
            correct=False, finished=False, score=attempt.score, total=lv["count"],
            var_results=var_results, error=run["error"], question_index=attempt.current_index,
        )

    if attempt.first_try_remaining:
        attempt.score += 1
    attempt.current_index += 1
    attempt.first_try_remaining = True
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    finished = attempt.current_index >= lv["count"]
    result = schemas.AnswerResult(
        correct=True, finished=finished, score=attempt.score, total=lv["count"],
        explain=q["explain"], var_results=[{"name": k, "correct": True} for k in q["expected"]],
        question_index=attempt.current_index,
    )
    if finished:
        _finish_attempt(attempt, db)
    else:
        nxt = attempt.questions_json[attempt.current_index]
        result.next_question = _public_question(nxt, "code")
    return result


@router.get("/certificate", response_model=schemas.CertificateResponse)
def certificate(user: models.User = Depends(security.get_current_user), db: Session = Depends(get_db)):
    progress = _level_progress_map(user, db)
    eligible = all((progress.get(i) and progress[i].passed) for i in range(1, 6))
    total_score = sum((progress.get(i).best_score if progress.get(i) else 0) for i in range(1, 6))
    total_questions = sum(lv["count"] for lv in LEVELS)
    sig = db.query(models.AppSetting).filter(models.AppSetting.key == "director_signature").first()
    return schemas.CertificateResponse(
        full_name=user.full_name, issued_date=dt.date.today().isoformat(),
        total_score=total_score, total_questions=total_questions, eligible=eligible,
        signature_url=(sig.value if sig else None),
    )


@router.post("/certificate/signature")
def upload_signature(body: schemas.SignatureUpload, user: models.User = Depends(security.get_current_user), db: Session = Depends(get_db)):
    if not body.data_url.startswith("data:image/"):
        raise HTTPException(status_code=400, detail="Please upload an image file.")
    if len(body.data_url) > 3_000_000:
        raise HTTPException(status_code=400, detail="That image is too large.")
    row = db.query(models.AppSetting).filter(models.AppSetting.key == "director_signature").first()
    if not row:
        row = models.AppSetting(key="director_signature", value=body.data_url)
    else:
        row.value = body.data_url
    db.add(row)
    db.commit()
    return {"ok": True}
