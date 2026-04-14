from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class OppCostInvestor(Base):
    __tablename__ = "opp_cost_investors"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    name = Column(String, nullable=False)
    firm = Column(String, nullable=True)
    date_passed = Column(String, nullable=False)  # stored as ISO date string (YYYY-MM-DD)
    valuation_then = Column(Float, nullable=False)
    hypothetical_check = Column(Float, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="opp_cost_investors")
