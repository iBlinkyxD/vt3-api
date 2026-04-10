import os

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime, timedelta
import random

from sqlalchemy.orm import Session

from database import get_db

from models.user import User
from models.company import Company
from models.opportunity import Opportunity

from schemas.user import UserCreate

from utils.security import hash_password, verify_password
from utils.jwt import create_access_token

router = APIRouter()

COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN") or None  # None = no domain attr (localhost-friendly)


def _set_auth_cookie(response: Response, token: str):
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="none" if COOKIE_SECURE else "lax",
        max_age=86400,  # 24 h, matches JWT expiry
        domain=COOKIE_DOMAIN,
        path="/",
    )

@router.post("/register")
def register(response: Response, data: UserCreate, db: Session = Depends(get_db)):

    # check if email exists
    existing = db.query(User).filter(User.email == data.user.email).first()

    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # create company
    company = Company(
        name=data.company.name,
        website=data.company.website,
        industry=data.company.industry,
        stage=data.company.stage,
        year_founded=data.company.year_founded
    )

    db.add(company)
    db.commit()
    db.refresh(company)

    # create fundraising opportunity
    opportunity = Opportunity(
        company_id=company.id,
        current_valuation=data.fundraising.current_valuation,
        fundraising_round=data.fundraising.current_round,
        target_raise=data.fundraising.target_raise,
        typical_check_size=data.fundraising.typical_check_size,
        first_investor_passed=data.fundraising.first_investor_passed
    )

    db.add(opportunity)
    db.commit()

    # hash password
    hashed_password = hash_password(data.user.password)

    # create user — auto-verified (no email verification required)
    user = User(
        first_name=data.user.first_name,
        last_name=data.user.last_name,
        email=data.user.email,
        phone=data.user.phone,
        password=hashed_password,
        role=data.user.role,
        company_id=company.id,

        is_active=True,
        is_verified=True,
        is_admin=False
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # Assign 8-digit zero-padded public ID based on the auto-generated primary key
    user.public_id = f"{user.id:08d}"
    db.commit()

    # Return token so the client can log in immediately
    token = create_access_token(user.id)
    _set_auth_cookie(response, token)

    return {
        "access_token": token,
        "token_type": "bearer",
        "message": "Account created successfully"
    }

@router.post("/login")
def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):

    db_user = db.query(User).filter(User.email == form_data.username).first()

    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(form_data.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not db_user.is_active:
        raise HTTPException(status_code=403, detail="Account not active")

    token = create_access_token(db_user.id)
    _set_auth_cookie(response, token)

    return {
        "access_token": token,
        "token_type": "bearer"
    }


@router.post("/logout")
def logout(response: Response):
    # Use set_cookie with max_age=0 rather than delete_cookie — this is
    # guaranteed to clear the cookie because it uses the exact same attributes
    # that were used when setting it, so the browser matches and expires it.
    response.set_cookie(
        key="access_token",
        value="",
        max_age=0,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="none" if COOKIE_SECURE else "lax",
        domain=COOKIE_DOMAIN,
        path="/",
    )
    return {"message": "Logged out"}

@router.post("/verify-email")
def verify_email(email: str, code: str, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.is_verified:
        return {"message": "Account already verified"}

    if user.verification_code != code:
        raise HTTPException(status_code=400, detail="Invalid code")

    if user.verification_expires < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Code expired")

    user.is_verified = True
    user.verification_code = None
    user.verification_expires = None

    db.commit()

    return {"message": "Email verified successfully"}

@router.post("/resend-verification")
async def resend_verification(email: str, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_verified:
        raise HTTPException(status_code=400, detail="Account already verified")

    # generate new code
    code = str(random.randint(100000, 999999))

    user.verification_code = code
    user.verification_expires = datetime.utcnow() + timedelta(minutes=10)
    db.commit()

    await send_verification_email(user.email, code)

    return {"message": "Verification email resent"}