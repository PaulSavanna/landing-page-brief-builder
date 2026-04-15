from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from landing_builder.domain.models import Page, PageRevisionEntry

RequestShortText = Annotated[str, Field(min_length=2, max_length=120)]
RequestMediumText = Annotated[str, Field(min_length=2, max_length=240)]


class PageCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    business_name: RequestShortText
    niche: RequestShortText
    audience: RequestMediumText
    offer: RequestMediumText
    tone: RequestShortText
    call_to_action: Annotated[str, Field(min_length=2, max_length=80)]

    @field_validator("business_name", "niche", "audience", "offer", "tone", "call_to_action")
    @classmethod
    def normalize_input(cls, value: str) -> str:
        collapsed = " ".join(value.split())
        if not collapsed:
            raise ValueError("Field must not be empty.")
        if any(ord(char) < 32 for char in collapsed):
            raise ValueError("Field contains unsupported control characters.")
        return collapsed


class PageUpdateRequest(PageCreateRequest):
    expected_revision: Annotated[int, Field(ge=1)]
    change_note: Annotated[str, Field(min_length=2, max_length=140)]


class PagesListResponse(BaseModel):
    items: list[Page]


class PageRevisionsResponse(BaseModel):
    items: list[PageRevisionEntry]


class ErrorResponse(BaseModel):
    detail: str


class ValidationErrorResponse(ErrorResponse):
    errors: list[dict[str, Any]]
