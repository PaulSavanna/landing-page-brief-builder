from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from landing_builder.api.dependencies import get_repository, get_settings, get_templates
from landing_builder.config import Settings
from landing_builder.domain.models import Page
from landing_builder.domain.schemas import (
    ErrorResponse,
    PageCreateRequest,
    PageRevisionsResponse,
    PagesListResponse,
    PageUpdateRequest,
    ValidationErrorResponse,
)
from landing_builder.services.page_composer import PageComposer
from landing_builder.storage.page_repository import PageRepository

router = APIRouter()


@router.get('/', include_in_schema=False)
def root(settings: Settings = Depends(get_settings)) -> FileResponse:
    return FileResponse(settings.static_dir / 'index.html')


@router.get('/health', tags=['system'])
def healthcheck(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    return {'status': 'ok', 'version': settings.app_version}


@router.get(
    '/api/pages',
    response_model=PagesListResponse,
    tags=['pages'],
    responses={500: {'model': ErrorResponse}},
)
def list_pages(repository: PageRepository = Depends(get_repository)) -> PagesListResponse:
    return PagesListResponse(items=repository.list_pages())


@router.post(
    '/api/pages',
    response_model=Page,
    status_code=status.HTTP_201_CREATED,
    tags=['pages'],
    responses={409: {'model': ErrorResponse}, 422: {'model': ValidationErrorResponse}, 500: {'model': ErrorResponse}},
)
def create_page(
    payload: PageCreateRequest,
    repository: PageRepository = Depends(get_repository),
) -> Page:
    page = PageComposer(existing_slugs=repository.list_slugs()).build(payload)
    return repository.create_page(page, change_note='Initial draft')


@router.put(
    '/api/pages/{slug}',
    response_model=Page,
    tags=['pages'],
    responses={404: {'model': ErrorResponse}, 409: {'model': ErrorResponse}, 422: {'model': ValidationErrorResponse}},
)
def update_page(
    slug: str,
    payload: PageUpdateRequest,
    repository: PageRepository = Depends(get_repository),
) -> Page:
    existing_page = repository.get_page_by_slug(slug)
    if existing_page is None:
        raise HTTPException(status_code=404, detail='Page not found.')

    updated_page = PageComposer().build(
        payload,
        slug_override=existing_page.slug,
        page_id=existing_page.id,
        created_at=existing_page.created_at,
        revision=existing_page.revision + 1,
        now=datetime.now(timezone.utc),
    )
    return repository.update_page(
        existing_page.slug,
        updated_page,
        expected_revision=payload.expected_revision,
        change_note=payload.change_note,
    )


@router.get(
    '/api/pages/{slug}',
    response_model=Page,
    tags=['pages'],
    responses={404: {'model': ErrorResponse}, 500: {'model': ErrorResponse}},
)
def get_page(slug: str, repository: PageRepository = Depends(get_repository)) -> Page:
    page = repository.get_page_by_slug(slug)
    if page is None:
        raise HTTPException(status_code=404, detail='Page not found.')
    return page


@router.get(
    '/api/pages/{slug}/revisions',
    response_model=PageRevisionsResponse,
    tags=['pages'],
    responses={404: {'model': ErrorResponse}},
)
def list_page_revisions(slug: str, repository: PageRepository = Depends(get_repository)) -> PageRevisionsResponse:
    page = repository.get_page_by_slug(slug)
    if page is None:
        raise HTTPException(status_code=404, detail='Page not found.')
    return PageRevisionsResponse(items=repository.list_page_revisions(slug))


@router.get(
    '/preview/{slug}',
    response_class=HTMLResponse,
    include_in_schema=False,
    responses={404: {'model': ErrorResponse}, 500: {'model': ErrorResponse}},
)
def preview_page(
    request: Request,
    slug: str,
    repository: PageRepository = Depends(get_repository),
    templates: Jinja2Templates = Depends(get_templates),
) -> HTMLResponse:
    page = repository.get_page_by_slug(slug)
    if page is None:
        raise HTTPException(status_code=404, detail='Page not found.')

    return templates.TemplateResponse(
        request=request,
        name='preview.html',
        context={'page': page},
    )
