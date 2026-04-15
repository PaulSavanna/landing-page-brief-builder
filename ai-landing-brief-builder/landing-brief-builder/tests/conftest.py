from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from landing_builder.app_factory import create_app
from landing_builder.config import Settings
from landing_builder.storage.page_repository import PageRepository


@pytest.fixture()
def temp_pages_file(tmp_path: Path) -> Path:
    return tmp_path / "pages.json"


@pytest.fixture()
def temp_revisions_file(tmp_path: Path) -> Path:
    return tmp_path / "page_revisions.json"


@pytest.fixture()
def settings(tmp_path: Path, temp_pages_file: Path, temp_revisions_file: Path) -> Settings:
    package_root = Path(__file__).resolve().parents[1]
    return Settings(
        app_title="Landing Brief Builder Test",
        app_version="2.0.0-test",
        base_dir=package_root,
        data_dir=tmp_path,
        static_dir=package_root / "static",
        templates_dir=package_root / "landing_builder" / "templates",
        pages_file=temp_pages_file,
        revisions_file=temp_revisions_file,
    )


@pytest.fixture()
def repository(temp_pages_file: Path, temp_revisions_file: Path) -> PageRepository:
    return PageRepository(temp_pages_file, temp_revisions_file)


@pytest.fixture()
def client(settings: Settings, repository: PageRepository) -> TestClient:
    return TestClient(create_app(settings=settings, repository=repository))
