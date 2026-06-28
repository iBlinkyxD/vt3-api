from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.sql import func
from database import Base


class Invitation(Base):
    __tablename__ = "invitations"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String, nullable=False, unique=True, index=True)  # e.g. "jhondoe" -> vt3.ai/jhondoe
    title = Column(String, nullable=True)                           # honorific, e.g. "Mr.", "Ms."
    name = Column(String, nullable=False)                           # invitee display name
    content = Column(Text, nullable=False, default="")             # body text (paragraphs split on blank lines)
    image_url = Column(String, nullable=True)                       # profile picture
    expires_at = Column(DateTime(timezone=True), nullable=True)     # link expiry; null = never
    single_use = Column(Boolean, nullable=False, default=False)     # deactivate after first signup
    created_at = Column(DateTime(timezone=True), server_default=func.now())
