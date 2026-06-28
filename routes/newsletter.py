from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models.newsletter import Newsletter
from models.user import User
from schemas.newsletter import NewsletterCreate, NewsletterOut
from utils.auth import admin_required

router = APIRouter(prefix="/newsletter", tags=["newsletter"])


@router.post("", response_model=NewsletterOut)
def subscribe(body: NewsletterCreate, db: Session = Depends(get_db)):
    """Public endpoint: capture an email for the newsletter. Idempotent on email."""
    email = body.email.strip().lower()

    existing = db.query(Newsletter).filter(Newsletter.email == email).first()
    if existing:
        return existing

    subscriber = Newsletter(email=email, source=body.source)
    db.add(subscriber)
    db.commit()
    db.refresh(subscriber)
    return subscriber


@router.get("", response_model=List[NewsletterOut])
def list_subscribers(
    db: Session = Depends(get_db),
    _admin: User = Depends(admin_required),
):
    """Admin only: list all captured newsletter emails, newest first."""
    return db.query(Newsletter).order_by(Newsletter.created_at.desc()).all()
