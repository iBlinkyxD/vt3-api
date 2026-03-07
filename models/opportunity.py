from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Opportunity(Base):
    __tablename__ = "opportunities"

    id = Column(Integer, primary_key=True, index=True)

    company_id = Column(Integer, ForeignKey("companies.id"))

    current_valuation = Column(Float)
    fundraising_round = Column(String)
    target_raise = Column(Float)
    typical_check_size = Column(Float)

    first_investor_passed = Column(String)

    company = relationship("Company", back_populates="opportunity")