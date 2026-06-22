from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import Lock
from typing import Any

from pydantic import ValidationError

from landing_builder.domain.models import Page, PageRevisionEntry

logger = logging.getLogger(__name__)


class DuplicatePageSlugError(RuntimeError):
    pass


class PageConflictError(RuntimeError):
    pass


class PageRepository:
    def __init__(self, pages_file: Path, revisions_file: Path | None = None) -> None:
        self._pages_file = pages_file
        self._revisions_file = revisions_file or pages_file.with_name('page_revisions.json')
        self._lock = Lock()
        self._ensure_storage_exists()

    def list_pages(self) -> list[Page]:
        with self._lock:
            pages = self._read_pages_unlocked()
        return sorted(pages, key=lambda item: item.updated_at, reverse=True)

    def list_slugs(self) -> list[str]:
        return [page.slug for page in self.list_pages()]

    def get_page_by_slug(self, slug: str) -> Page | None:
        normalized_slug = slug.strip().strip('/')
        return next((page for page in self.list_pages() if page.slug == normalized_slug), None)

    def list_page_revisions(self, slug: str) -> list[PageRevisionEntry]:
        normalized_slug = slug.strip().strip('/')
        with self._lock:
            revisions = [item for item in self._read_revisions_unlocked() if item.slug == normalized_slug]
        return sorted(revisions, key=lambda item: item.revision, reverse=True)

    def create_page(self, page: Page, *, change_note: str = 'Initial draft') -> Page:
        with self._lock:
            pages = self._read_pages_unlocked()
            if any(existing_page.slug == page.slug for existing_page in pages):
                raise DuplicatePageSlugError(f"Page with slug '{page.slug}' already exists.")

            pages.insert(0, page)
            self._write_pages_unlocked(pages)
            self._append_revision_unlocked(page, change_note)
        return page

    def update_page(self, slug: str, page: Page, *, expected_revision: int, change_note: str) -> Page:
        normalized_slug = slug.strip().strip('/')
        with self._lock:
            pages = self._read_pages_unlocked()
            for index, existing_page in enumerate(pages):
                if existing_page.slug != normalized_slug:
                    continue
                if existing_page.revision != expected_revision:
                    raise PageConflictError(
                        f"Page '{normalized_slug}' changed since revision {expected_revision}. Refresh and try again."
                    )
                pages[index] = page
                self._write_pages_unlocked(pages)
                self._append_revision_unlocked(page, change_note)
                return page
        raise KeyError(normalized_slug)

    def _ensure_storage_exists(self) -> None:
        self._pages_file.parent.mkdir(parents=True, exist_ok=True)
        self._revisions_file.parent.mkdir(parents=True, exist_ok=True)
        if not self._pages_file.exists():
            self._write_raw_unlocked(self._pages_file, [])
        if not self._revisions_file.exists():
            self._write_raw_unlocked(self._revisions_file, [])

    def _read_pages_unlocked(self) -> list[Page]:
        raw_items = self._read_raw_items_unlocked(self._pages_file)
        pages: list[Page] = []

        for raw_item in raw_items:
            try:
                payload = dict(raw_item)
                payload.setdefault('revision', 1)
                pages.append(Page.model_validate(payload))
            except ValidationError:
                logger.warning('Skipping invalid page record in storage.', exc_info=True)

        return pages

    def _read_revisions_unlocked(self) -> list[PageRevisionEntry]:
        raw_items = self._read_raw_items_unlocked(self._revisions_file)
        revisions: list[PageRevisionEntry] = []
        for raw_item in raw_items:
            try:
                revisions.append(PageRevisionEntry.model_validate(raw_item))
            except ValidationError:
                logger.warning('Skipping invalid revision record in storage.', exc_info=True)
        return revisions

    def _read_raw_items_unlocked(self, file_path: Path) -> list[dict[str, Any]]:
        if not file_path.exists():
            return []

        try:
            data = json.loads(file_path.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            logger.exception('Storage file is corrupted. Resetting to an empty list.')
            self._reset_invalid_storage(file_path, 'corrupted')
            return []

        if not isinstance(data, list):
            logger.warning('Storage file root must be a list. Resetting to an empty list.')
            self._reset_invalid_storage(file_path, 'invalid-root')
            return []

        return [item for item in data if isinstance(item, dict)]

    def _reset_invalid_storage(self, file_path: Path, suffix: str) -> None:
        backup_path = self._build_backup_path(file_path, suffix)
        try:
            if file_path.exists():
                file_path.replace(backup_path)
        except OSError:
            logger.exception('Failed to back up invalid storage file before reset.')
        self._write_raw_unlocked(file_path, [])

    def _build_backup_path(self, file_path: Path, suffix: str) -> Path:
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        candidate = file_path.with_name(f"{file_path.stem}.{suffix}.{timestamp}.json")
        counter = 2

        while candidate.exists():
            candidate = file_path.with_name(f"{file_path.stem}.{suffix}.{timestamp}.{counter}.json")
            counter += 1

        return candidate

    def _write_pages_unlocked(self, pages: list[Page]) -> None:
        self._write_raw_unlocked(self._pages_file, [page.model_dump(mode='json') for page in pages])

    def _append_revision_unlocked(self, page: Page, change_note: str) -> None:
        revisions = self._read_revisions_unlocked()
        revisions.append(
            PageRevisionEntry(
                page_id=page.id,
                slug=page.slug,
                revision=page.revision,
                saved_at=page.updated_at,
                change_note=change_note,
                hero_title=page.hero_title,
                offer=page.offer,
            )
        )
        self._write_raw_unlocked(self._revisions_file, [item.model_dump(mode='json') for item in revisions])

    def _write_raw_unlocked(self, target_file: Path, data: list[dict[str, Any]]) -> None:
        target_file.parent.mkdir(parents=True, exist_ok=True)

        temp_path: str | None = None
        try:
            with NamedTemporaryFile(
                mode='w',
                encoding='utf-8',
                dir=target_file.parent,
                delete=False,
            ) as temp_file:
                json.dump(data, temp_file, ensure_ascii=False, indent=2)
                temp_file.flush()
                os.fsync(temp_file.fileno())
                temp_path = temp_file.name

            Path(temp_path).replace(target_file)
        finally:
            if temp_path:
                leftover = Path(temp_path)
                if leftover.exists() and leftover != target_file:
                    leftover.unlink(missing_ok=True)
