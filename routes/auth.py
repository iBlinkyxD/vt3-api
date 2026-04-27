import os

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from pydantic import EmailStr as _EmailStr
import random

from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
import requests as http_requests

from sqlalchemy.orm import Session
from sqlalchemy import text

from database import get_db

from models.user import User
from models.company import Company
from models.opportunity import Opportunity
from models.pending_registration import PendingRegistration

from schemas.user import UserCreate

from utils.security import hash_password, verify_password
from utils.jwt import create_access_token
from utils.email import send_verification_email, send_password_reset_email
from jose import jwt, JWTError

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
def register(data: UserCreate, db: Session = Depends(get_db)):
    email = data.user.email.lower().strip()

    # Block if an active (non-deleted) verified account already exists for this email
    if db.query(User).filter(User.email == email, User.is_deleted == False).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    code    = str(random.randint(100000, 999999))
    expires = datetime.utcnow() + timedelta(minutes=10)

    # Store all signup data temporarily — no DB records created yet
    payload = {
        "first_name":        data.user.first_name,
        "last_name":         data.user.last_name,
        "phone":             data.user.phone,
        "password_hash":     hash_password(data.user.password),
        "role":              data.user.role,
        "company_name":      data.company.name,
        "company_website":   data.company.website,
        "company_industry":  data.company.industry,
        "company_stage":     data.company.stage,
        "company_year":      data.company.year_founded,
        "valuation":         data.fundraising.current_valuation,
        "round":             data.fundraising.current_round,
        "target_raise":      data.fundraising.target_raise,
        "check_size":        data.fundraising.typical_check_size,
        "first_investor":    data.fundraising.first_investor_passed,
    }

    pending = db.query(PendingRegistration).filter(PendingRegistration.email == email).first()
    if pending:
        # Replace existing pending record (expired or duplicate attempt)
        pending.code       = code
        pending.expires_at = expires
        pending.data       = payload
    else:
        pending = PendingRegistration(email=email, code=code, expires_at=expires, data=payload)
        db.add(pending)
    db.commit()

    try:
        send_verification_email(email, code)
    except Exception:
        pass  # don't block signup if email fails; user can resend

    return {"email": email, "message": "Check your email for the verification code."}

@router.post("/login")
def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):

    db_user = db.query(User).filter(User.email == form_data.username, User.is_deleted == False).first()

    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(form_data.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not db_user.is_active:
        raise HTTPException(status_code=403, detail="Account not active")

    token = create_access_token(db_user.id, session_version=db_user.session_version or 1)
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
    email = email.lower().strip()

    # If a verified account already exists just issue a token (idempotent)
    existing = db.query(User).filter(User.email == email).first()
    if existing and existing.is_verified:
        token = create_access_token(existing.id, session_version=existing.session_version or 1)
        _set_auth_cookie(response, token)
        return {"access_token": token, "token_type": "bearer"}

    # Look up the pending registration
    pending = db.query(PendingRegistration).filter(PendingRegistration.email == email).first()
    if not pending:
        raise HTTPException(status_code=404, detail="No pending registration found for this email")

    if pending.code != code:
        raise HTTPException(status_code=400, detail="Invalid code")

    if pending.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Code expired. Request a new one.")

    d = pending.data

    # Create company
    company = Company(
        name=d["company_name"],
        website=d.get("company_website"),
        industry=d.get("company_industry"),
        stage=d.get("company_stage"),
        year_founded=d.get("company_year"),
    )
    db.add(company)
    db.commit()
    db.refresh(company)

    # Create opportunity
    opportunity = Opportunity(
        company_id=company.id,
        current_valuation=d.get("valuation"),
        fundraising_round=d.get("round"),
        target_raise=d.get("target_raise"),
        typical_check_size=d.get("check_size"),
        first_investor_passed=d.get("first_investor"),
    )
    db.add(opportunity)
    db.commit()

    # Create user
    user = User(
        first_name=d["first_name"],
        last_name=d["last_name"],
        email=email,
        phone=d.get("phone"),
        password=d["password_hash"],
        role=d.get("role", "founder"),
        company_id=company.id,
        is_active=True,
        is_verified=True,
        is_admin=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Assign public_id from the dedicated sequence (gap-free, independent of DB id)
    seq = db.execute(text("SELECT nextval('public_id_seq')")).scalar()
    user.public_id = f"{seq:08d}"
    db.commit()

    # Clean up pending record
    db.delete(pending)
    db.commit()

    token = create_access_token(user.id, session_version=user.session_version or 1)
    _set_auth_cookie(response, token)

    return {"access_token": token, "token_type": "bearer", "message": "Email verified successfully"}

@router.post("/resend-verification")
def resend_verification(email: str, db: Session = Depends(get_db)):
    email = email.lower().strip()

    pending = db.query(PendingRegistration).filter(PendingRegistration.email == email).first()
    if not pending:
        raise HTTPException(status_code=404, detail="No pending registration found for this email")

    code = str(random.randint(100000, 999999))
    pending.code       = code
    pending.expires_at = datetime.utcnow() + timedelta(minutes=10)
    db.commit()

    try:
        send_verification_email(email, code)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to send email")

    return {"message": "Verification email resent"}


class CorrectEmailRequest(BaseModel):
    old_email: _EmailStr
    new_email: _EmailStr


@router.post("/correct-email")
def correct_email(body: CorrectEmailRequest, db: Session = Depends(get_db)):
    old = body.old_email.lower().strip()
    new = body.new_email.lower().strip()

    if old == new:
        raise HTTPException(status_code=400, detail="New email is the same as the current one.")

    pending = db.query(PendingRegistration).filter(PendingRegistration.email == old).first()
    if not pending:
        raise HTTPException(status_code=404, detail="No pending registration found for that email.")

    # Block if new email already belongs to a verified account or another pending record
    if db.query(User).filter(User.email == new).first():
        raise HTTPException(status_code=409, detail="That email is already in use.")
    if db.query(PendingRegistration).filter(PendingRegistration.email == new).first():
        raise HTTPException(status_code=409, detail="That email is already in use.")

    code = str(random.randint(100000, 999999))
    pending.email      = new
    pending.code       = code
    pending.expires_at = datetime.utcnow() + timedelta(minutes=10)
    db.commit()

    try:
        send_verification_email(new, code)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to send verification email.")

    return {"email": new, "message": "Email updated. Check your inbox for a new code."}


class ForgotPasswordRequest(BaseModel):
    email: _EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM  = "HS256"
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://vt3.ai")


@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()

    # Always return the same response — don't reveal whether the email exists
    if user:
        expire = datetime.utcnow() + timedelta(hours=1)
        token = jwt.encode(
            {"user_id": user.id, "purpose": "password_reset", "exp": expire},
            SECRET_KEY,
            algorithm=ALGORITHM,
        )
        reset_url = f"{FRONTEND_URL}/reset-password?token={token}"
        try:
            send_password_reset_email(user.email, reset_url)
        except Exception:
            pass  # Don't leak errors — log in production

    return {"message": "If that email exists, you'll receive a reset link shortly."}


@router.post("/reset-password")
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(body.token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=400, detail="Reset link is invalid or has expired.")

    if payload.get("purpose") != "password_reset":
        raise HTTPException(status_code=400, detail="Invalid reset token.")

    user = db.query(User).filter(User.id == payload.get("user_id")).first()
    if not user:
        raise HTTPException(status_code=400, detail="User not found.")

    user.password = hash_password(body.new_password)
    db.commit()

    return {"message": "Password updated successfully."}


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
    user = db.query(User).filter(User.email == email, User.is_deleted == False).first()

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
            is_verified=True,
            google_linked=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        seq = db.execute(text("SELECT nextval('public_id_seq')")).scalar()
        user.public_id = f"{seq:08d}"
        db.commit()
    else:
        # Block Google login if the user explicitly disconnected Google from Settings
        if not user.google_linked:
            raise HTTPException(
                status_code=403,
                detail="Google login is not enabled for this account. Sign in with your email and password, then reconnect Google from Settings.",
            )
        # Only set Google avatar if the user has no avatar yet (don't overwrite a custom upload)
        if avatar_url and not user.avatar_url:
            user.avatar_url = avatar_url
        db.commit()

    token = create_access_token(user.id, session_version=user.session_version or 1)
    _set_auth_cookie(response, token)

    return {"access_token": token, "token_type": "bearer", "is_new_user": not bool(user.public_id)}