from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class NewsletterCreate(BaseModel):
    email: EmailStr
    source: Optional[str] = None


class NewsletterOut(BaseModel):
    id: int
    email: EmailStr
    source: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
