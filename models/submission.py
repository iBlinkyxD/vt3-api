import enum
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON, Enum as SAEnum
from sqlalchemy.sql import func
from database import Base


class SubmissionType(str, enum.Enum):
    introduction = "introduction"
    compute = "compute"
    funding = "funding"
    time = "time"


class SubmissionStatus(str, enum.Enum):
    new = "new"
    in_review = "in_review"
    accepted = "accepted"
    declined = "declined"
    archived = "archived"


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)       # the founder
    advisor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # logged-in advisor
    advisor_name = Column(String, nullable=False)
    advisor_email = Column(String, nullable=False)
    type = Column(SAEnum(SubmissionType), nullable=False)
    status = Column(SAEnum(SubmissionStatus), nullable=False, default=SubmissionStatus.new)
    data = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
