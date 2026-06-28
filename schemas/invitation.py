import re
from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _normalize_slug(value: str) -> str:
    slug = value.strip().lstrip("/").lower()
    if not SLUG_RE.match(slug):
        raise ValueError(
            "Link can only contain lowercase letters, numbers, and hyphens (e.g. 'john-doe')."
        )
    return slug


class InvitationCreate(BaseModel):
    slug: str
    title: Optional[str] = None
    name: str
    content: str = ""
    image_url: Optional[str] = None
    expires_at: Optional[datetime] = None
    single_use: bool = False

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        return _normalize_slug(v)


class InvitationUpdate(BaseModel):
    slug: Optional[str] = None
    title: Optional[str] = None
    name: Optional[str] = None
    content: Optional[str] = None
    image_url: Optional[str] = None
    expires_at: Optional[datetime] = None
    single_use: Optional[bool] = None

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: Optional[str]) -> Optional[str]:
        return _normalize_slug(v) if v is not None else v


class InvitationOut(BaseModel):
    id: int
    slug: str
    title: Optional[str]
    name: str
    content: str
    image_url: Optional[str]
    expires_at: Optional[datetime]
    single_use: bool
    created_at: datetime

    class Config:
        from_attributes = True
