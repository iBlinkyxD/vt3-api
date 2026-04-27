from sqlalchemy import Column, Integer, String, DateTime, JSON
from database import Base


class PendingRegistration(Base):
    __tablename__ = "pending_registrations"

    id         = Column(Integer, primary_key=True, index=True)
    email      = Column(String, unique=True, nullable=False, index=True)
    code       = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    data       = Column(JSON, nullable=False)  # all signup fields, password already hashed
