from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class OppCostInvestorCreate(BaseModel):
    name: str
    firm: Optional[str] = None
    date_passed: str
    valuation_then: float
    hypothetical_check: float


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
    current_valuation: Optional[float] = None
    email_frequency: Optional[str] = None


class OppCostSettingsOut(BaseModel):
    current_valuation: float
    email_frequency: str
