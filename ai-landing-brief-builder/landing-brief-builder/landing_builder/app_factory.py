from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from landing_builder.api.errors import install_exception_handlers
from landing_builder.api.routes import router
from landing_builder.config import Settings, get_settings
from landing_builder.storage.page_repository import PageRepository


def create_app(settings: Settings | None = None, repository: PageRepository | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    page_repository = repository or PageRepository(app_settings.pages_file, app_settings.revisions_file)
    templates = Jinja2Templates(directory=str(app_settings.templates_dir))

    app = FastAPI(
        title=app_settings.app_title,
        version=app_settings.app_version,
        docs_url='/docs',
        redoc_url='/redoc',
    )

    app.state.settings = app_settings
    app.state.repository = page_repository
    app.state.templates = templates

    install_exception_handlers(app)
    app.mount('/static', StaticFiles(directory=app_settings.static_dir), name='static')
    app.include_router(router)

    return app
