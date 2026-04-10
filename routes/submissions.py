from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models.submission import Submission, SubmissionStatus
from models.user import User
from schemas.submission import SubmissionCreate, SubmissionOut, SubmissionStatusUpdate
from utils.auth import get_current_user

router = APIRouter(prefix="/submissions", tags=["submissions"])


@router.post("/public/{owner_public_id}", response_model=SubmissionOut)
def create_submission(
    owner_public_id: str,
    body: SubmissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Advisor submits to a founder's portal. Requires the advisor to be logged in."""
    owner = db.query(User).filter(User.public_id == owner_public_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Portal not found")

    advisor_name = (
        f"{current_user.first_name or ''} {current_user.last_name or ''}".strip()
        or current_user.email
    )

    submission = Submission(
        owner_id=owner.id,
        advisor_user_id=current_user.id,
        advisor_name=advisor_name,
        advisor_email=current_user.email,
        type=body.type,
        data=body.data,
        status=SubmissionStatus.new,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission


@router.get("", response_model=List[SubmissionOut])
def get_submissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Founder fetches all submissions to their own portal."""
    return (
        db.query(Submission)
        .filter(Submission.owner_id == current_user.id)
        .order_by(Submission.created_at.desc())
        .all()
    )


@router.patch("/{submission_id}/status", response_model=SubmissionOut)
def update_submission_status(
    submission_id: int,
    body: SubmissionStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Founder updates the status of a submission on their portal."""
    submission = (
        db.query(Submission)
        .filter(
            Submission.id == submission_id,
            Submission.owner_id == current_user.id,
        )
        .first()
    )
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    submission.status = body.status
    db.commit()
    db.refresh(submission)
    return submission
