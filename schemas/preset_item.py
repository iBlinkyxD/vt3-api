from pydantic import BaseModel
from typing import List, Optional, Any


class PresetItemCreate(BaseModel):
    name: str
    category: str
    description: str
    icon_url: Optional[str] = None
    pricing_plans: List[Any] = []
    sort_order: int = 0
    is_active: bool = True


class PresetItemUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    icon_url: Optional[str] = None
    pricing_plans: Optional[List[Any]] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class PresetItemOut(BaseModel):
    id: int
    name: str
    category: str
    description: str
    icon_url: Optional[str]
    pricing_plans: List[Any]
    sort_order: int
    is_active: bool

    class Config:
        from_attributes = True
