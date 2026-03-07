from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from database import Base

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String)
    website = Column(String)

    industry = Column(String)
    stage = Column(String)
    year_founded = Column(Integer)

    users = relationship("User", back_populates="company")
    opportunity = relationship("Opportunity", back_populates="company", uselist=False)