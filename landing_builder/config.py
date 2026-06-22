from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    app_title: str
    app_version: str
    base_dir: Path
    data_dir: Path
    static_dir: Path
    templates_dir: Path
    pages_file: Path
    revisions_file: Path


DEFAULT_APP_TITLE = "Landing Brief Builder"
DEFAULT_APP_VERSION = "2.3.0"
_ENV_PREFIX = "LANDING_BUILDER_"


def _resolve_path(value: str | None, fallback: Path) -> Path:
    if not value:
        return fallback

    candidate = Path(value)
    return candidate if candidate.is_absolute() else (fallback.parent / candidate).resolve()


def get_settings() -> Settings:
    package_dir = Path(__file__).resolve().parent
    base_dir = package_dir.parent
    data_dir = _resolve_path(os.getenv(f"{_ENV_PREFIX}DATA_DIR"), base_dir / "data")
    pages_file = _resolve_path(os.getenv(f"{_ENV_PREFIX}PAGES_FILE"), data_dir / "pages.json")
    revisions_file = _resolve_path(
        os.getenv(f"{_ENV_PREFIX}REVISIONS_FILE"),
        data_dir / "page_revisions.json",
    )

    return Settings(
        app_title=os.getenv(f"{_ENV_PREFIX}APP_TITLE", DEFAULT_APP_TITLE),
        app_version=os.getenv(f"{_ENV_PREFIX}APP_VERSION", DEFAULT_APP_VERSION),
        base_dir=base_dir,
        data_dir=data_dir,
        static_dir=base_dir / "static",
        templates_dir=package_dir / "templates",
        pages_file=pages_file,
        revisions_file=revisions_file,
    )
