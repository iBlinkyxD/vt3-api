from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db

from utils.auth import get_current_user
from utils.security import hash_password, verify_password

from models.user import User
from models.company import Company

from schemas.user import UserUpdate, ChangePassword

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
def get_logged_in_user(
    current_user: User = Depends(get_current_user),
):

    company = current_user.company
    opportunity = company.opportunity if company else None

    return {
        "user": {
            "id": current_user.id,
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "email": current_user.email,
            "phone": current_user.phone,
            "role": current_user.role,
            "is_active": current_user.is_active,
            "is_verified": current_user.is_verified
        },
        "company": {
            "id": company.id,
            "name": company.name,
            "website": company.website,
            "industry": company.industry,
            "stage": company.stage,
            "year_founded": company.year_founded
        } if company else None,
        "fundraising": {
            "current_valuation": opportunity.current_valuation,
            "fundraising_round": opportunity.fundraising_round,
            "target_raise": opportunity.target_raise,
            "typical_check_size": opportunity.typical_check_size,
            "first_investor_passed": opportunity.first_investor_passed
        } if opportunity else None
    }

@router.put("/me")
def update_user(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    if data.first_name:
        current_user.first_name = data.first_name

    if data.last_name:
        current_user.last_name = data.last_name

    if data.phone:
        current_user.phone = data.phone

    db.commit()
    db.refresh(current_user)

    return {"message": "User updated successfully"}

@router.post("/change-password")
def change_password(
    data: ChangePassword,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    if not verify_password(data.old_password, current_user.password):
        raise HTTPException(status_code=401, detail="Old password incorrect")

    current_user.password = hash_password(data.new_password)

    db.commit()

    return {"message": "Password updated successfully"}