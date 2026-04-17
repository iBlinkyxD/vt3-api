from pydantic import BaseModel, EmailStr, Field
from typing import Optional

PASSWORD_MIN = 8
PASSWORD_MAX = 128
NAME_MAX = 100
PHONE_MAX = 30
BIO_MAX = 500
WEBSITE_MAX = 255


class RegisterUser(BaseModel):
    first_name: str = Field(min_length=1, max_length=NAME_MAX)
    last_name: str = Field(min_length=1, max_length=NAME_MAX)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=PHONE_MAX)
    password: str = Field(min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)
    role: str = Field(min_length=1, max_length=50)


class RegisterCompany(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    website: str = Field(max_length=WEBSITE_MAX, default="")
    industry: str = Field(min_length=1, max_length=100)
    stage: str = Field(min_length=1, max_length=100)
    year_founded: int = Field(ge=1800, le=2030)


class RegisterFundraising(BaseModel):
    current_valuation: float = Field(gt=0)
    current_round: str = Field(min_length=1, max_length=100)
    target_raise: float = Field(gt=0)
    typical_check_size: float = Field(gt=0)
    first_investor_passed: str = Field(max_length=200, default="")


class UserCreate(BaseModel):
    user: RegisterUser
    company: RegisterCompany
    fundraising: RegisterFundraising


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=NAME_MAX)
    last_name: Optional[str] = Field(None, min_length=1, max_length=NAME_MAX)
    phone: Optional[str] = Field(None, max_length=PHONE_MAX)
    bio: Optional[str] = Field(None, max_length=BIO_MAX)


class ChangePassword(BaseModel):
    old_password: str
    new_password: str = Field(min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)


class UserStatusUpdate(BaseModel):
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
