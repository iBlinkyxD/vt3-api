from pydantic import BaseModel
from typing import Optional


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    website: Optional[str] = None