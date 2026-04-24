from sqlalchemy import Column, Integer, String, Boolean, JSON
from database import Base


class PresetItem(Base):
    __tablename__ = "preset_items"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String, nullable=False)
    category    = Column(String, nullable=False)
    description = Column(String, nullable=False)
    icon_url    = Column(String, nullable=True)
    pricing_plans = Column(JSON, nullable=False, default=list)
    sort_order  = Column(Integer, default=0)
    is_active   = Column(Boolean, default=True)
