from __future__ import annotations

from typing import cast

from fastapi import Request
from fastapi.templating import Jinja2Templates

from landing_builder.config import Settings
from landing_builder.storage.page_repository import PageRepository


def get_repository(request: Request) -> PageRepository:
    return cast(PageRepository, request.app.state.repository)


def get_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def get_templates(request: Request) -> Jinja2Templates:
    return cast(Jinja2Templates, request.app.state.templates)
