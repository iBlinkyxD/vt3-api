import os

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from pydantic import BaseModel
import random

from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
import requests as http_requests

from sqlalchemy.orm import Session

from database import get_db

from models.user import User
from models.company import Company
from models.opportunity import Opportunity

from schemas.user import UserCreate

from utils.security import hash_password, verify_password
from utils.jwt import create_access_token
from utils.email import send_verification_email

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")

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

    # Generate verification code
    code = str(random.randint(100000, 999999))
    expires = datetime.utcnow() + timedelta(minutes=10)

    # Create user — unverified until email confirmed
    user = User(
        first_name=data.user.first_name,
        last_name=data.user.last_name,
        email=data.user.email,
        phone=data.user.phone,
        password=hashed_password,
        role=data.user.role,
        company_id=company.id,

        is_active=False,
        is_verified=False,
        is_admin=False,

        verification_code=code,
        verification_expires=expires,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # Assign 8-digit zero-padded public ID
    user.public_id = f"{user.id:08d}"
    db.commit()

    # Send verification email (sync Resend call)
    try:
        send_verification_email(user.email, code)
    except Exception:
        pass  # don't block registration if email fails; user can resend

    return {
        "email": user.email,
        "message": "Account created. Check your email for the verification code."
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
def verify_email(email: str, code: str, response: Response, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_verified:
        # Already verified — just issue a token so the client can proceed
        token = create_access_token(user.id)
        _set_auth_cookie(response, token)
        return {"access_token": token, "token_type": "bearer"}

    if user.verification_code != code:
        raise HTTPException(status_code=400, detail="Invalid code")

    if user.verification_expires < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Code expired")

    user.is_verified = True
    user.is_active = True
    user.verification_code = None
    user.verification_expires = None

    db.commit()

    token = create_access_token(user.id)
    _set_auth_cookie(response, token)

    return {"access_token": token, "token_type": "bearer", "message": "Email verified successfully"}

@router.post("/resend-verification")
def resend_verification(email: str, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_verified:
        raise HTTPException(status_code=400, detail="Account already verified")

    code = str(random.randint(100000, 999999))
    user.verification_code = code
    user.verification_expires = datetime.utcnow() + timedelta(minutes=10)
    db.commit()

    try:
        send_verification_email(user.email, code)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to send email")

    return {"message": "Verification email resent"}


class GoogleAuthRequest(BaseModel):
    code: str  # Authorization code from the frontend (auth-code flow)


@router.post("/google")
def google_auth(body: GoogleAuthRequest, response: Response, db: Session = Depends(get_db)):
    # Exchange the authorization code for tokens
    token_response = http_requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": body.code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
            "redirect_uri": "postmessage",  # required for auth-code flow from JS
            "grant_type": "authorization_code",
        },
    )
    if token_response.status_code != 200:
        raise HTTPException(status_code=401, detail="Failed to exchange Google code")

    id_token_str = token_response.json().get("id_token")
    if not id_token_str:
        raise HTTPException(status_code=401, detail="No ID token in Google response")

    # Verify the ID token
    try:
        info = google_id_token.verify_oauth2_token(
            id_token_str,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=10,
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {e}")

    email      = info.get("email")
    first_name = info.get("given_name", "")
    last_name  = info.get("family_name", "")
    avatar_url = info.get("picture")

    if not email:
        raise HTTPException(status_code=400, detail="Google account has no email")

    # Find or create user
    user = db.query(User).filter(User.email == email).first()

    if not user:
        # Create a minimal user — no company/opportunity rows required for Google sign-in
        user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            avatar_url=avatar_url,
            password=None,
            role="founder",
            is_active=True,
            is_verified=True,  # Google already verified the email
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user.public_id = f"{user.id:08d}"
        db.commit()
    else:
        # Update avatar if changed
        if avatar_url and user.avatar_url != avatar_url:
            user.avatar_url = avatar_url
            db.commit()

    token = create_access_token(user.id)
    _set_auth_cookie(response, token)

    return {"access_token": token, "token_type": "bearer", "is_new_user": not bool(user.public_id)}