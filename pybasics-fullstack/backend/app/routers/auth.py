from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..database import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup", response_model=schemas.TokenResponse)
def signup(body: schemas.SignupRequest, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.username == body.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="That username is already taken.")
    user = models.User(
        username=body.username,
        full_name=body.full_name,
        password_hash=security.hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = security.create_access_token(user.id)
    return schemas.TokenResponse(access_token=token, full_name=user.full_name, username=user.username)


@router.post("/login", response_model=schemas.TokenResponse)
def login(body: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == body.username.strip()).first()
    if not user or not security.verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect username or password.")
    token = security.create_access_token(user.id)
    return schemas.TokenResponse(access_token=token, full_name=user.full_name, username=user.username)


@router.get("/me", response_model=schemas.MeResponse)
def me(user: models.User = Depends(security.get_current_user)):
    return schemas.MeResponse(username=user.username, full_name=user.full_name, created_at=user.created_at)
