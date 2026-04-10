from pydantic import BaseModel
from datetime import datetime


class SponsorshipCreate(BaseModel):
    units: int
    display_name: str = "Anonymous"


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
