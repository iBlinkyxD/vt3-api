import os
import httpx
import secrets
import requests as http_requests

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
from pydantic import BaseModel, Field, EmailStr as _EmailStr
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from database import get_db
from utils.auth import get_current_user
from utils.security import hash_password, verify_password
from utils.email import send_email_change_confirmation, send_email_change_notification
from models.user import User
from models.company import Company
from models.opportunity import Opportunity
from schemas.user import UserUpdate, ChangePassword

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://vt3.ai")

router = APIRouter(prefix="/users", tags=["users"])

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
AVATAR_BUCKET = "avatars"

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


def _ensure_public_id(user: User, db: Session) -> str:
    """Lazily assign public_id to users created before this feature."""
    if not user.public_id:
        user.public_id = f"{user.id:08d}"
        db.commit()
    return user.public_id


@router.get("/public/{public_id}")
def get_public_profile(public_id: str, db: Session = Depends(get_db)):
    """Unauthenticated — returns a founder's public profile for display on their public pages."""
    user = db.query(User).filter(User.public_id == public_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Profile not found")
    company = user.company
    return {
        "name": f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email,
        "avatar_url": user.avatar_url,
        "bio": user.bio,
        "company_name": company.name if company else None,
        "industry": company.industry if company else None,
        "stage": company.stage if company else None,
    }


@router.get("/me")
def get_logged_in_user(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    public_id = _ensure_public_id(current_user, db)
    company = current_user.company
    opportunity = company.opportunity if company else None

    return {
        "user": {
            "id": current_user.id,
            "public_id": public_id,
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "email": current_user.email,
            "phone": current_user.phone,
            "role": current_user.role,
            "is_active": current_user.is_active,
            "is_verified": current_user.is_verified,
            "avatar_url": current_user.avatar_url,
            "bio": current_user.bio,
            "subscription_plan": current_user.subscription_plan,
            "subscription_status": current_user.subscription_status or "inactive",
            "has_password": bool(current_user.password),
            "google_linked": bool(current_user.google_linked),
        },
        "company": {
            "id": company.id,
            "name": company.name,
            "website": company.website,
            "industry": company.industry,
            "stage": company.stage,
            "year_founded": company.year_founded,
        } if company else None,
        "fundraising": {
            "current_valuation": opportunity.current_valuation,
            "fundraising_round": opportunity.fundraising_round,
            "target_raise": opportunity.target_raise,
            "typical_check_size": opportunity.typical_check_size,
            "first_investor_passed": opportunity.first_investor_passed,
        } if opportunity else None,
    }


@router.post("/me/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="File must be a JPEG, PNG, WebP, or GIF image")

    file_data = await file.read()
    if len(file_data) > 5 * 1024 * 1024:  # 5 MB limit
        raise HTTPException(status_code=400, detail="Image must be under 5 MB")

    ext = (file.filename or "avatar").rsplit(".", 1)[-1].lower()
    path = f"{current_user.id}/avatar.{ext}"

    # Upload directly via Supabase Storage REST API (no SDK needed)
    upload_url = f"{SUPABASE_URL}/storage/v1/object/{AVATAR_BUCKET}/{path}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": file.content_type,
        "x-upsert": "true",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(upload_url, content=file_data, headers=headers)
    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=500, detail=f"Supabase upload failed: {resp.text}")

    public_url = f"{SUPABASE_URL}/storage/v1/object/public/{AVATAR_BUCKET}/{path}"

    current_user.avatar_url = public_url
    db.commit()

    return {"avatar_url": public_url}


@router.put("/me")
def update_user(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if data.first_name is not None:
        current_user.first_name = data.first_name
    if data.last_name is not None:
        current_user.last_name = data.last_name
    if data.phone is not None:
        current_user.phone = data.phone
    if data.bio is not None:
        current_user.bio = data.bio

    db.commit()
    db.refresh(current_user)
    return {"message": "User updated successfully"}


@router.post("/change-password")
def change_password(
    data: ChangePassword,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.password:
        raise HTTPException(status_code=400, detail="Your account has no password. Use Set Password instead.")
    if not verify_password(data.old_password, current_user.password):
        raise HTTPException(status_code=401, detail="Old password incorrect")

    current_user.password = hash_password(data.new_password)
    db.commit()
    return {"message": "Password updated successfully"}


@router.post("/me/unlink-google")
def unlink_google(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.google_linked:
        raise HTTPException(status_code=400, detail="Google is not linked to your account.")
    if not current_user.password:
        raise HTTPException(status_code=400, detail="Set a password before unlinking Google so you don't lose access to your account.")

    current_user.google_linked = False
    db.commit()
    return {"message": "Google unlinked successfully."}


GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")


class GoogleLinkRequest(BaseModel):
    code: str


@router.post("/me/link-google")
def link_google(
    body: GoogleLinkRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    token_response = http_requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": body.code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
            "redirect_uri": "postmessage",
            "grant_type": "authorization_code",
        },
    )
    if token_response.status_code != 200:
        raise HTTPException(status_code=401, detail="Failed to exchange Google code")

    id_token_str = token_response.json().get("id_token")
    if not id_token_str:
        raise HTTPException(status_code=401, detail="No ID token in Google response")

    try:
        info = google_id_token.verify_oauth2_token(
            id_token_str,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=10,
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {e}")

    google_email = info.get("email")
    if not google_email:
        raise HTTPException(status_code=400, detail="Google account has no email")

    if google_email.lower() != current_user.email.lower():
        raise HTTPException(status_code=400, detail="This Google account belongs to a different email address.")

    avatar_url = info.get("picture")
    current_user.google_linked = True
    if avatar_url and not current_user.avatar_url:
        current_user.avatar_url = avatar_url
    db.commit()
    return {"message": "Google account linked successfully"}


class SetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)


@router.post("/me/set-password")
def set_password(
    data: SetPasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.password:
        raise HTTPException(status_code=400, detail="Your account already has a password. Use Change Password instead.")

    current_user.password = hash_password(data.new_password)
    db.commit()
    return {"message": "Password set successfully"}


class EmailChangeRequest(BaseModel):
    new_email: _EmailStr
    current_password: str


@router.post("/me/request-email-change")
def request_email_change(
    data: EmailChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Step 1: Re-authenticate — verify current password before proceeding
    if not current_user.password:
        raise HTTPException(status_code=400, detail="Password authentication is not available for your account.")
    if not verify_password(data.current_password, current_user.password):
        raise HTTPException(status_code=401, detail="Incorrect password.")

    new_email = data.new_email.strip().lower()

    if new_email == current_user.email:
        raise HTTPException(status_code=400, detail="That is already your current email address.")

    taken = db.query(User).filter(User.email == new_email).first()
    if taken:
        raise HTTPException(status_code=400, detail="That email address is already in use.")

    token = secrets.token_urlsafe(32)
    cancel_token = secrets.token_urlsafe(32)
    old_email = current_user.email

    current_user.pending_email = new_email
    current_user.email_change_token = token
    current_user.email_change_expires = datetime.utcnow() + timedelta(hours=1)
    current_user.email_change_cancel_token = cancel_token
    db.commit()

    confirm_url = f"{FRONTEND_URL}/confirm-email-change?token={token}"
    cancel_url = f"{FRONTEND_URL}/cancel-email-change?token={cancel_token}"

    # Step 3: Send confirmation link to new email
    try:
        send_email_change_confirmation(new_email, confirm_url)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to send confirmation email.")

    # Step 4: Send security alert to old email (best-effort — don't block on failure)
    try:
        send_email_change_notification(old_email, new_email, cancel_url)
    except Exception:
        pass

    return {"message": "Confirmation email sent. Check your new inbox."}


@router.get("/me/confirm-email-change")
def confirm_email_change(
    token: str,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email_change_token == token).first()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired confirmation link.")

    if user.email_change_expires < datetime.utcnow():
        user.pending_email = None
        user.email_change_token = None
        user.email_change_expires = None
        db.commit()
        raise HTTPException(status_code=400, detail="This confirmation link has expired. Please request a new one.")

    user.email = user.pending_email
    user.pending_email = None
    user.email_change_token = None
    user.email_change_expires = None
    user.email_change_cancel_token = None
    # Step 6: Increment session version to invalidate all existing tokens
    user.session_version = (user.session_version or 1) + 1
    db.commit()

    return {"message": "Email updated successfully."}


@router.get("/me/cancel-email-change")
def cancel_email_change(
    token: str,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email_change_cancel_token == token).first()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired cancellation link.")

    user.pending_email = None
    user.email_change_token = None
    user.email_change_expires = None
    user.email_change_cancel_token = None
    db.commit()

    return {"message": "Email change cancelled."}


class OnboardingData(BaseModel):
    company_name: str = Field(min_length=1, max_length=200)
    company_website: Optional[str] = Field(None, max_length=255)
    industry: str = Field(min_length=1, max_length=100)
    company_stage: str = Field(min_length=1, max_length=100)
    year_founded: Optional[int] = Field(None, ge=1800, le=2030)
    current_valuation: float = Field(gt=0)
    fundraising_round: str = Field(min_length=1, max_length=100)
    target_raise: float = Field(gt=0)
    typical_check_size: float = Field(gt=0)
    first_investor_passed: Optional[str] = None


@router.post("/me/onboarding")
def save_onboarding(
    data: OnboardingData,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create or update the company and fundraising opportunity for the current user.
    Used by Google-signup users who skipped the registration form."""
    # Create or update company
    if current_user.company_id:
        company = db.query(Company).filter(Company.id == current_user.company_id).first()
    else:
        company = Company()
        db.add(company)
        db.flush()  # populate company.id before linking
        current_user.company_id = company.id

    company.name = data.company_name
    company.website = data.company_website or None
    company.industry = data.industry
    company.stage = data.company_stage
    company.year_founded = data.year_founded

    db.flush()

    # Create or update opportunity
    opportunity = db.query(Opportunity).filter(Opportunity.company_id == company.id).first()
    if not opportunity:
        opportunity = Opportunity(company_id=company.id)
        db.add(opportunity)

    opportunity.current_valuation = data.current_valuation
    opportunity.fundraising_round = data.fundraising_round
    opportunity.target_raise = data.target_raise
    opportunity.typical_check_size = data.typical_check_size
    opportunity.first_investor_passed = data.first_investor_passed or None

    db.commit()
    return {"message": "Onboarding saved"}
