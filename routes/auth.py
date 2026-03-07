from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime, timedelta


from sqlalchemy.orm import Session

from database import get_db

from models.user import User
from models.company import Company
from models.opportunity import Opportunity

from schemas.user import UserCreate

from utils.security import hash_password, verify_password
from utils.jwt import create_access_token
from utils.verification import generate_verification_code
from utils.email import send_verification_email

router = APIRouter()

@router.post("/register")
async def register(data: UserCreate, db: Session = Depends(get_db)):

    # check if email exists
    existing = db.query(User).filter(User.email == data.user.email).first()

    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # create company
    company = Company(
        name=data.company.name,
        website=data.company.website,
        industry=data.company.industry,
        stage=data.company.stage,
        year_founded=data.company.year_founded
    )

    db.add(company)
    db.commit()
    db.refresh(company)

    # create fundraising opportunity
    opportunity = Opportunity(
        company_id=company.id,
        current_valuation=data.fundraising.current_valuation,
        fundraising_round=data.fundraising.current_round,
        target_raise=data.fundraising.target_raise,
        typical_check_size=data.fundraising.typical_check_size,
        first_investor_passed=data.fundraising.first_investor_passed
    )

    db.add(opportunity)
    db.commit()

    # hash password
    hashed_password = hash_password(data.user.password)

    # create user
    code = generate_verification_code()

    user = User(
        first_name=data.user.first_name,
        last_name=data.user.last_name,
        email=data.user.email,
        phone=data.user.phone,
        password=hashed_password,
        role=data.user.role,
        company_id=company.id,

        verification_code=code,
        verification_expires=datetime.utcnow() + timedelta(minutes=10),

        is_active=True,
        is_verified=False,
        is_admin=False
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    await send_verification_email(user.email, code)

    return {"message": "User registered successfully"}

@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):

    db_user = db.query(User).filter(User.email == form_data.username).first()

    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(form_data.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not db_user.is_active:
        raise HTTPException(status_code=403, detail="Account not active")

    if not db_user.is_verified:
        raise HTTPException(status_code=403, detail="Account not verified")

    token = create_access_token(db_user.id)

    return {
        "access_token": token,
        "token_type": "bearer"
    }

@router.post("/verify-email")
def verify_email(email: str, code: str, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.verification_code != code:
        raise HTTPException(status_code=400, detail="Invalid code")

    if user.verification_expires < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Code expired")

    user.is_verified = True
    user.verification_code = None
    user.verification_expires = None

    db.commit()

    return {"message": "Email verified successfully"}