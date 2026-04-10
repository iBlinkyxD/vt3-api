from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class FundingItem(Base):
    __tablename__ = "funding_items"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    category = Column(String, nullable=False)
    price_per_unit = Column(Float, nullable=False)
    unit_label = Column(String, nullable=False)
    units_needed = Column(Integer, nullable=False)
    units_funded = Column(Integer, default=0)
    description = Column(String, nullable=False)
    impact = Column(String, nullable=False)
    priority = Column(String, nullable=False)  # High | Medium | Low
    reward_per_unit = Column(String, nullable=False)

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner = relationship("User")
