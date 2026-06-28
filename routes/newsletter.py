from fastapi import APIRouter, Depends, BackgroundTasks, status
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models.newsletter import Newsletter
from models.invitation import Invitation
from models.user import User
from schemas.newsletter import NewsletterCreate, NewsletterOut
from utils.auth import admin_required
from utils.email import send_newsletter_welcome_email

router = APIRouter(prefix="/newsletter", tags=["newsletter"])


def _send_welcome_safe(email: str) -> None:
    """Best-effort welcome email — never let delivery failures break signup."""
    try:
        send_newsletter_welcome_email(email)
    except Exception:
        pass


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def subscribe(
    body: NewsletterCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Public endpoint: capture an email for the newsletter.

    Returns a fixed response regardless of prior subscription state so the
    endpoint can't be used to enumerate which emails already exist.
    """
    email = body.email.strip().lower()

    # Only trust `source` if it maps to a real invitation slug (avoids junk /
    # arbitrary source values being injected by clients).
    source = None
    if body.source:
        slug = body.source.strip().lower()
        if db.query(Invitation.id).filter(Invitation.slug == slug).first():
            source = slug

    existing = db.query(Newsletter).filter(Newsletter.email == email).first()
    if not existing:
        db.add(Newsletter(email=email, source=source))
        db.commit()
        background_tasks.add_task(_send_welcome_safe, email)

    return {"ok": True}


@router.get("", response_model=List[NewsletterOut])
def list_subscribers(
    db: Session = Depends(get_db),
    _admin: User = Depends(admin_required),
):
    """Admin only: list all captured newsletter emails, newest first."""
    return db.query(Newsletter).order_by(Newsletter.created_at.desc()).all()
