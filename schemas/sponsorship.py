from pydantic import BaseModel, Field
from datetime import datetime


class SponsorshipCreate(BaseModel):
    units: int = Field(gt=0)
    display_name: str = Field(max_length=100, default="Anonymous")


class SponsorshipOut(BaseModel):
    id: int
    item_id: int
    display_name: str
    units_funded: int
    amount_usd: float
    created_at: datetime
    item_title: str

    class Config:
        from_attributes = True
