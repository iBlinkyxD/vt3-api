from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db

from models.user import User

from schemas.user import UserStatusUpdate

from utils.auth import admin_required

router = APIRouter(
    prefix="/admin",
    tags=["admin"]
)

@router.get("/users")
def get_all_users(
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required)
):
    users = db.query(User).all()
    return users

@router.patch("/admin/users/{user_id}/status")
def update_user_status(
    user_id: int,
    data: UserStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required)
):

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if data.is_active is not None:
        user.is_active = data.is_active

    if data.is_verified is not None:
        user.is_verified = data.is_verified

    db.commit()
    db.refresh(user)

    return {
        "message": "User status updated successfully",
        "user": {
            "id": user.id,
            "is_active": user.is_active,
            "is_verified": user.is_verified
        }
    }