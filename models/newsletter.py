from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from database import Base


class Newsletter(Base):
    __tablename__ = "newsletter"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False, unique=True, index=True)
    source = Column(String, nullable=True)  # invitation slug the email was captured from
    created_at = Column(DateTime(timezone=True), server_default=func.now())
