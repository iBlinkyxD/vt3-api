from pydantic import BaseModel, EmailStr
from typing import Optional

class RegisterUser(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    password: str
    role: str


class RegisterCompany(BaseModel):
    name: str
    website: str
    industry: str
    stage: str
    year_founded: int


class RegisterFundraising(BaseModel):
    current_valuation: float
    current_round: str
    target_raise: float
    typical_check_size: float
    first_investor_passed: str

class UserCreate(BaseModel):
    user: RegisterUser
    company: RegisterCompany
    fundraising: RegisterFundraising

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None

class ChangePassword(BaseModel):
    old_password: str
    new_password: str

class UserStatusUpdate(BaseModel):
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None