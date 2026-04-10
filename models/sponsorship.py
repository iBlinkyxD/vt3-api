from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from database import Base


class Sponsorship(Base):
    __tablename__ = "sponsorships"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("funding_items.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    display_name = Column(String, nullable=False, default="Anonymous")
    units_funded = Column(Integer, nullable=False)
    amount_usd = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    item = relationship("FundingItem")
    user = relationship("User")
