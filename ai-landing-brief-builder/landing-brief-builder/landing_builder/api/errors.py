from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from landing_builder.storage.page_repository import DuplicatePageSlugError, PageConflictError

logger = logging.getLogger(__name__)


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                'detail': 'Validation failed.',
                'errors': exc.errors(),
            },
        )

    @app.exception_handler(DuplicatePageSlugError)
    async def duplicate_slug_exception_handler(_: Request, exc: DuplicatePageSlugError) -> JSONResponse:
        return JSONResponse(status_code=409, content={'detail': str(exc)})

    @app.exception_handler(PageConflictError)
    async def page_conflict_exception_handler(_: Request, exc: PageConflictError) -> JSONResponse:
        return JSONResponse(status_code=409, content={'detail': str(exc)})

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.exception('Unhandled server error.', exc_info=exc)
        return JSONResponse(status_code=500, content={'detail': 'Internal server error.'})
