import os
import httpx
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models.invitation import Invitation
from models.newsletter import Newsletter
from models.user import User
from schemas.invitation import InvitationCreate, InvitationUpdate, InvitationOut
from utils.auth import admin_required

router = APIRouter(prefix="/invitations", tags=["invitations"])

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
IMAGE_BUCKET = "preset-icons"  # reuse existing public bucket, under an invitations/ prefix
# Map content-type -> canonical extension. SVG is intentionally excluded: same-origin
# SVGs can carry scripts (stored XSS) when served from the API host. The extension is
# derived from this map (never from the client filename) to avoid path traversal.
CONTENT_TYPE_EXT = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}
EXT_MIME = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
MAX_IMAGE_BYTES = 5_000_000  # 5 MB
ASSETS_DIR = "assets"  # mounted at /assets in main.py — used as a local fallback


def _sniff_ext(data: bytes) -> str | None:
    """Identify the real image type from magic bytes (independent of client headers)."""
    if data[:3] == b"\xff\xd8\xff":
        return "jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def _save_local(request: Request, invitation_id: int, ext: str, data: bytes) -> str:
    """Persist the image to the mounted assets dir and return an absolute URL."""
    rel_dir = os.path.join("invitations", str(invitation_id))
    abs_dir = os.path.join(ASSETS_DIR, rel_dir)
    os.makedirs(abs_dir, exist_ok=True)
    filename = f"avatar.{ext}"
    with open(os.path.join(abs_dir, filename), "wb") as f:
        f.write(data)
    base = str(request.base_url).rstrip("/")
    return f"{base}/assets/invitations/{invitation_id}/{filename}"


# ── Public — fetch invitation by slug ──────────────────────────────────────────

def _is_expired(invitation: Invitation, db: Session) -> bool:
    """A link is expired if past its expiry, or single-use and already signed up."""
    if invitation.expires_at is not None:
        exp = invitation.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > exp:
            return True
    if invitation.single_use:
        used = db.query(Newsletter).filter(Newsletter.source == invitation.slug).count() > 0
        if used:
            return True
    return False


@router.get("/public/{slug}", response_model=InvitationOut)
def get_invitation_by_slug(slug: str, db: Session = Depends(get_db)):
    """Unauthenticated — used by the public invitation page (vt3.ai/<slug>)."""
    invitation = db.query(Invitation).filter(Invitation.slug == slug.lower()).first()
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")
    if _is_expired(invitation, db):
        raise HTTPException(status_code=410, detail="This invitation link has expired.")
    return invitation


# ── Admin CRUD ─────────────────────────────────────────────────────────────────

@router.get("", response_model=List[InvitationOut])
def list_invitations(db: Session = Depends(get_db), _admin: User = Depends(admin_required)):
    return db.query(Invitation).order_by(Invitation.created_at.desc()).all()


@router.post("", response_model=InvitationOut)
def create_invitation(body: InvitationCreate, db: Session = Depends(get_db), _admin: User = Depends(admin_required)):
    if db.query(Invitation).filter(Invitation.slug == body.slug).first():
        raise HTTPException(status_code=409, detail="That link is already taken. Choose another.")
    invitation = Invitation(**body.model_dump())
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return invitation


@router.put("/{invitation_id}", response_model=InvitationOut)
def update_invitation(invitation_id: int, body: InvitationUpdate, db: Session = Depends(get_db), _admin: User = Depends(admin_required)):
    invitation = db.query(Invitation).filter(Invitation.id == invitation_id).first()
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")

    updates = body.model_dump(exclude_unset=True)
    new_slug = updates.get("slug")
    if new_slug and new_slug != invitation.slug:
        if db.query(Invitation).filter(Invitation.slug == new_slug).first():
            raise HTTPException(status_code=409, detail="That link is already taken. Choose another.")

    for field, value in updates.items():
        setattr(invitation, field, value)
    db.commit()
    db.refresh(invitation)
    return invitation


@router.delete("/{invitation_id}")
def delete_invitation(invitation_id: int, db: Session = Depends(get_db), _admin: User = Depends(admin_required)):
    invitation = db.query(Invitation).filter(Invitation.id == invitation_id).first()
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")
    db.delete(invitation)
    db.commit()
    return {"message": "Deleted"}


# ── Image upload ───────────────────────────────────────────────────────────────

@router.post("/{invitation_id}/image")
async def upload_invitation_image(
    request: Request,
    invitation_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _admin: User = Depends(admin_required),
):
    declared_ext = CONTENT_TYPE_EXT.get(file.content_type or "")
    if not declared_ext:
        raise HTTPException(status_code=400, detail="Invalid image type. Use JPEG, PNG, or WebP.")

    invitation = db.query(Invitation).filter(Invitation.id == invitation_id).first()
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")

    file_data = await file.read()
    if len(file_data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="Image is too large. Max size is 5 MB.")

    # Trust the actual bytes, not the client-declared Content-Type.
    ext = _sniff_ext(file_data)
    if ext is None or ext != declared_ext:
        raise HTTPException(status_code=400, detail="File is not a valid JPEG, PNG, or WebP image.")

    content_type = EXT_MIME[ext]  # canonical MIME, never the raw client value
    public_url = None

    # Prefer Supabase storage when configured; fall back to local assets on any failure.
    if SUPABASE_URL and SUPABASE_SERVICE_KEY:
        path = f"invitations/{invitation_id}/avatar.{ext}"
        upload_url = f"{SUPABASE_URL}/storage/v1/object/{IMAGE_BUCKET}/{path}"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    upload_url,
                    content=file_data,
                    headers={
                        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                        "Content-Type": content_type,
                        "x-upsert": "true",
                    },
                )
            if resp.status_code in (200, 201):
                public_url = f"{SUPABASE_URL}/storage/v1/object/public/{IMAGE_BUCKET}/{path}"
        except httpx.HTTPError:
            public_url = None  # network/DNS failure — fall back to local

    if public_url is None:
        public_url = _save_local(request, invitation_id, ext, file_data)

    invitation.image_url = public_url
    db.commit()

    return {"image_url": public_url}
