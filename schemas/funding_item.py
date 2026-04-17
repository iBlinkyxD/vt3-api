from pydantic import BaseModel, Field
from typing import Optional


class FundingItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    company: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=100)
    price_per_unit: float = Field(gt=0)
    unit_label: str = Field(min_length=1, max_length=100)
    units_needed: int = Field(gt=0)
    units_funded: int = Field(ge=0, default=0)
    description: str = Field(min_length=1, max_length=2000)
    impact: str = Field(min_length=1, max_length=1000)
    priority: str = Field(min_length=1, max_length=50)
    reward_per_unit: str = Field(min_length=1, max_length=500)


class FundingItemUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    company: Optional[str] = Field(None, min_length=1, max_length=200)
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    price_per_unit: Optional[float] = Field(None, gt=0)
    unit_label: Optional[str] = Field(None, min_length=1, max_length=100)
    units_needed: Optional[int] = Field(None, gt=0)
    units_funded: Optional[int] = Field(None, ge=0)
    description: Optional[str] = Field(None, min_length=1, max_length=2000)
    impact: Optional[str] = Field(None, min_length=1, max_length=1000)
    priority: Optional[str] = Field(None, min_length=1, max_length=50)
    reward_per_unit: Optional[str] = Field(None, min_length=1, max_length=500)


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
