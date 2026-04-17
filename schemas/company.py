from pydantic import BaseModel, Field
from typing import Optional


class CompanyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    website: Optional[str] = Field(None, max_length=255)
