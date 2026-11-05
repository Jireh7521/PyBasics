from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.database import Base, get_db
from app.main import app
from app.routers.course import COURSE_BY_DAY
from app.sandbox import run_user_code


def _signup(client):
    response = client.post(
        "/api/auth/signup",
        json={
            "username": "learner_one",
            "password": "python-pass-123",
            "full_name": "Taylor Learner",
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _complete_course(session_factory, username):
    db = session_factory()
    try:
        user = db.query(models.User).filter_by(username=username).one()
        db.add_all(
            [
                models.LessonCompletion(user_id=user.id, day=day)
                for day in COURSE_BY_DAY
            ]
        )
        db.commit()
    finally:
        db.close()


def test_signup_login_and_authenticated_profile(app_client):
    client, _ = app_client

    token = _signup(client)
    profile = client.get("/api/auth/me", headers=_auth(token))

    assert profile.status_code == 200
    assert profile.json()["username"] == "learner_one"
    assert profile.json()["full_name"] == "Taylor Learner"

    login = client.post(
        "/api/auth/login",
        json={"username": "learner_one", "password": "python-pass-123"},
    )
    assert login.status_code == 200
    assert login.json()["access_token"]


def test_signup_rejects_invalid_details_and_duplicate_user(app_client):
    client, _ = app_client

    invalid = client.post(
        "/api/auth/signup",
        json={"username": "x", "password": "123", "full_name": "Taylor"},
    )
    assert invalid.status_code == 422

    _signup(client)
    duplicate = client.post(
        "/api/auth/signup",
        json={
            "username": "learner_one",
            "password": "python-pass-123",
            "full_name": "Another Learner",
        },
    )
    assert duplicate.status_code == 400


def test_course_requires_authentication_and_hides_answer_key(app_client):
    client, _ = app_client

    assert client.get("/api/course/status").status_code == 401

    token = _signup(client)
    lesson = client.get("/api/course/day/1", headers=_auth(token))

    assert lesson.status_code == 200
    assert lesson.json()["day"] == 1
    assert lesson.json()["quiz"]
    assert all("correct" not in question for question in lesson.json()["quiz"])


def test_course_quiz_records_progress_only_after_passing(app_client):
    client, _ = app_client
    token = _signup(client)
    headers = _auth(token)

    lesson = client.get("/api/course/day/1", headers=headers).json()
    correct_answers = [question["correct"] for question in COURSE_BY_DAY[1]["quiz"]]

    result = client.post(
        "/api/course/day/1/submit",
        headers=headers,
        json={"answers": correct_answers},
    )

    assert result.status_code == 200
    assert result.json()["passed"] is True

    status = client.get("/api/course/status", headers=headers)
    assert status.status_code == 200
    assert status.json()["completed_count"] == 1
    assert status.json()["lessons"][0]["status"] == "done"


def test_exam_is_locked_until_course_is_complete(app_client):
    client, _ = app_client
    token = _signup(client)

    response = client.post("/api/exam/level/1/start", headers=_auth(token))

    assert response.status_code == 403


def test_exam_question_does_not_expose_answer_key_and_certificate_is_gated(app_client):
    client, session_factory = app_client
    token = _signup(client)
    _complete_course(session_factory, "learner_one")

    start = client.post("/api/exam/level/1/start", headers=_auth(token))
    assert start.status_code == 200

    public_question = start.json()["question"]
    assert "correct" not in public_question
    assert "expected" not in public_question

    db = session_factory()
    try:
        user = db.query(models.User).filter_by(username="learner_one").one()
        attempt = (
            db.query(models.ExamAttempt)
            .filter_by(user_id=user.id, level=1)
            .one()
        )
        assert "correct" in attempt.questions_json[0]
    finally:
        db.close()

    certificate = client.get("/api/exam/certificate", headers=_auth(token))
    assert certificate.status_code == 200
    assert certificate.json()["eligible"] is False



def test_exam_grades_an_answer_against_server_stored_key(app_client):
    client, session_factory = app_client
    token = _signup(client)
    _complete_course(session_factory, "learner_one")

    start = client.post("/api/exam/level/1/start", headers=_auth(token))
    assert start.status_code == 200
    attempt_id = start.json()["attempt_id"]

    db = session_factory()
    try:
        attempt = db.query(models.ExamAttempt).filter_by(id=attempt_id).one()
        correct_option = attempt.questions_json[0]["correct"]
    finally:
        db.close()

    answer = client.post(
        f"/api/exam/attempt/{attempt_id}/answer/mcq",
        headers=_auth(token),
        json={"selected": correct_option},
    )

    assert answer.status_code == 200
    assert answer.json()["correct"] is True
    assert answer.json()["score"] == 1
    assert answer.json()["finished"] is False

def test_sandbox_rejects_oversized_submission_before_execution():
    result = run_user_code("x" * 4001)

    assert result["ok"] is False
    assert result["vars"] == {}
    assert "4000 characters" in result["error"]
