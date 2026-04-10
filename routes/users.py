import os
import httpx

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from database import get_db
from utils.auth import get_current_user
from utils.security import hash_password, verify_password
from models.user import User
from schemas.user import UserUpdate, ChangePassword

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
    if not verify_password(data.old_password, current_user.password):
        raise HTTPException(status_code=401, detail="Old password incorrect")

    current_user.password = hash_password(data.new_password)
    db.commit()
    return {"message": "Password updated successfully"}
