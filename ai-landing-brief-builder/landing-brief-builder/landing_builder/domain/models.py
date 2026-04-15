from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

ShortText = Annotated[str, Field(min_length=2, max_length=120)]
MediumText = Annotated[str, Field(min_length=2, max_length=240)]
LongText = Annotated[str, Field(min_length=2, max_length=400)]


class BaseNormalizedModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    @staticmethod
    def normalize_text(value: str) -> str:
        collapsed = " ".join(value.split())
        if not collapsed:
            raise ValueError("Field must not be empty.")
        if any(ord(char) < 32 for char in collapsed):
            raise ValueError("Field contains unsupported control characters.")
        return collapsed


class FAQItem(BaseNormalizedModel):
    q: MediumText
    a: MediumText

    @field_validator("q", "a")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return cls.normalize_text(value)


class Page(BaseNormalizedModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:8], min_length=8, max_length=64)
    slug: str = Field(min_length=3, max_length=160)
    revision: int = Field(default=1, ge=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(microsecond=0))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(microsecond=0))
    business_name: ShortText
    niche: ShortText
    audience: MediumText
    offer: MediumText
    tone: ShortText
    call_to_action: Annotated[str, Field(min_length=2, max_length=80)]
    hero_title: Annotated[str, Field(min_length=2, max_length=200)]
    hero_subtitle: LongText
    benefits: Annotated[list[MediumText], Field(min_length=3, max_length=6)]
    faq: Annotated[list[FAQItem], Field(min_length=3, max_length=6)]

    @field_validator(
        "business_name",
        "niche",
        "audience",
        "offer",
        "tone",
        "call_to_action",
        "hero_title",
        "hero_subtitle",
    )
    @classmethod
    def validate_text_fields(cls, value: str) -> str:
        return cls.normalize_text(value)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        slug = value.strip().strip("/")
        if not slug:
            raise ValueError("Slug must not be empty.")
        if any(char.isspace() for char in slug):
            raise ValueError("Slug must not contain whitespace.")
        return slug

    @field_validator("benefits")
    @classmethod
    def validate_benefits(cls, value: list[str]) -> list[str]:
        normalized = [cls.normalize_text(item) for item in value]
        if len(set(normalized)) != len(normalized):
            raise ValueError("Benefits must not contain duplicates.")
        return normalized

    @field_validator("updated_at")
    @classmethod
    def validate_timestamp_order(cls, value: datetime, info: ValidationInfo) -> datetime:
        created_at = info.data.get("created_at")
        if isinstance(created_at, datetime) and value < created_at:
            raise ValueError("updated_at cannot be earlier than created_at.")
        return value


class PageRevisionEntry(BaseNormalizedModel):
    page_id: str = Field(min_length=8, max_length=64)
    slug: str = Field(min_length=3, max_length=160)
    revision: int = Field(ge=1)
    saved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(microsecond=0))
    change_note: Annotated[str, Field(min_length=2, max_length=140)]
    hero_title: Annotated[str, Field(min_length=2, max_length=200)]
    offer: MediumText

    @field_validator("slug", "change_note", "hero_title", "offer")
    @classmethod
    def validate_strings(cls, value: str) -> str:
        return cls.normalize_text(value)
