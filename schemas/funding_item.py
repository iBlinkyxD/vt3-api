from pydantic import BaseModel
from typing import Optional

class FundingItemCreate(BaseModel):
    title: str
    company: str
    category: str
    price_per_unit: float
    unit_label: str
    units_needed: int
    units_funded: int = 0
    description: str
    impact: str
    priority: str
    reward_per_unit: str

class FundingItemUpdate(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    category: Optional[str] = None
    price_per_unit: Optional[float] = None
    unit_label: Optional[str] = None
    units_needed: Optional[int] = None
    units_funded: Optional[int] = None
    description: Optional[str] = None
    impact: Optional[str] = None
    priority: Optional[str] = None
    reward_per_unit: Optional[str] = None

class FundingItemOut(BaseModel):
    id: int
    title: str
    company: str
    category: str
    price_per_unit: float
    unit_label: str
    units_needed: int
    units_funded: int
    description: str
    impact: str
    priority: str
    reward_per_unit: str
    owner_id: int

    class Config:
        from_attributes = True
