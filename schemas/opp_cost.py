from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, date
from enum import Enum


class EmailFrequency(str, Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    never = "never"


class OppCostInvestorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    firm: Optional[str] = Field(None, max_length=200)
    date_passed: str = Field(min_length=1, max_length=20)
    valuation_then: float = Field(gt=0)
    hypothetical_check: float = Field(gt=0)

    @field_validator("date_passed")
    @classmethod
    def validate_date(cls, v: str) -> str:
        try:
            date.fromisoformat(v)
        except ValueError:
            raise ValueError("date_passed must be a valid ISO date (YYYY-MM-DD)")
        return v


class OppCostInvestorOut(BaseModel):
    id: int
    name: str
    firm: Optional[str] = None
    date_passed: str
    valuation_then: float
    hypothetical_check: float
    created_at: datetime

    class Config:
        from_attributes = True


class OppCostSettingsUpdate(BaseModel):
    current_valuation: Optional[float] = Field(None, gt=0)
    email_frequency: Optional[EmailFrequency] = None


class OppCostSettingsOut(BaseModel):
    current_valuation: float
    email_frequency: str
