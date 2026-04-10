from pydantic import BaseModel
from typing import Any, Dict, Optional
from datetime import datetime
from models.submission import SubmissionType, SubmissionStatus


class SubmissionCreate(BaseModel):
    type: SubmissionType
    data: Dict[str, Any]


class SubmissionStatusUpdate(BaseModel):
    status: SubmissionStatus


class SubmissionOut(BaseModel):
    id: int
    owner_id: int
    advisor_user_id: Optional[int]
    advisor_name: str
    advisor_email: str
    type: SubmissionType
    status: SubmissionStatus
    data: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True
