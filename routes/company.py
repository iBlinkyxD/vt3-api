from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from utils.auth import get_current_user

from models.company import Company
from models.user import User

from schemas.company import CompanyUpdate

router = APIRouter(prefix="/company", tags=["company"])

@router.get("/")
def get_company(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    if not current_user.company_id:
        raise HTTPException(status_code=404, detail="User has no company")

    company = db.query(Company).filter(
        Company.id == current_user.company_id
    ).first()

    return company

@router.put("/")
def update_company(
    data: CompanyUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    company = db.query(Company).filter(
        Company.id == current_user.company_id
    ).first()

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if data.name:
        company.name = data.name

    if data.website:
        company.website = data.website

    db.commit()
    db.refresh(company)

    return {"message": "Company updated successfully"}