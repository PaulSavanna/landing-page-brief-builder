from __future__ import annotations

from datetime import datetime, timezone
import json

from landing_builder.domain.models import Page
from landing_builder.storage.page_repository import PageConflictError, PageRepository


def build_page(**overrides):
    payload = {
        "id": "page0001",
        "slug": "novastack",
        "revision": 1,
        "created_at": datetime(2026, 4, 15, 10, 0, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 4, 15, 10, 0, tzinfo=timezone.utc),
        "business_name": "NovaStack",
        "niche": "Developer Tools",
        "audience": "Engineering teams",
        "offer": "Release notes assistant",
        "tone": "Direct",
        "call_to_action": "Book an intro call",
        "hero_title": "NovaStack: Release notes assistant",
        "hero_subtitle": "Helps engineering teams publish better release notes faster.",
        "benefits": ["One", "Two", "Three"],
        "faq": [
            {"q": "Q1?", "a": "A1"},
            {"q": "Q2?", "a": "A2"},
            {"q": "Q3?", "a": "A3"},
        ],
    }
    payload.update(overrides)
    return Page.model_validate(payload)


def test_create_page_persists_revision_entry(tmp_path) -> None:
    repository = PageRepository(tmp_path / "pages.json", tmp_path / "revisions.json")
    page = build_page()

    repository.create_page(page)

    revisions = repository.list_page_revisions(page.slug)
    assert len(revisions) == 1
    assert revisions[0].revision == 1
    assert revisions[0].change_note == "Initial draft"


def test_update_page_increments_history(tmp_path) -> None:
    repository = PageRepository(tmp_path / "pages.json", tmp_path / "revisions.json")
    page = build_page()
    repository.create_page(page)

    updated = build_page(revision=2, updated_at=datetime(2026, 4, 15, 11, 0, tzinfo=timezone.utc), offer="Updated offer")
    repository.update_page(page.slug, updated, expected_revision=1, change_note="Refined offer")

    revisions = repository.list_page_revisions(page.slug)
    assert len(revisions) == 2
    assert revisions[0].revision == 2
    assert revisions[0].change_note == "Refined offer"


def test_update_page_rejects_stale_revision(tmp_path) -> None:
    repository = PageRepository(tmp_path / "pages.json", tmp_path / "revisions.json")
    page = build_page()
    repository.create_page(page)

    updated = build_page(revision=2)

    try:
        repository.update_page(page.slug, updated, expected_revision=99, change_note="Refined offer")
    except PageConflictError as exc:
        assert "changed since revision" in str(exc)
    else:
        raise AssertionError("Expected PageConflictError")


def test_invalid_json_storage_is_backed_up_and_reset(tmp_path) -> None:
    pages_file = tmp_path / "pages.json"
    revisions_file = tmp_path / "revisions.json"
    pages_file.write_text("{not-json", encoding="utf-8")

    repository = PageRepository(pages_file, revisions_file)

    assert repository.list_pages() == []
    assert json.loads(pages_file.read_text(encoding="utf-8")) == []
    backups = sorted(tmp_path.glob("pages.corrupted.*.json"))
    assert len(backups) == 1


def test_invalid_root_storage_is_backed_up_and_reset(tmp_path) -> None:
    pages_file = tmp_path / "pages.json"
    revisions_file = tmp_path / "revisions.json"
    pages_file.write_text(json.dumps({"items": []}), encoding="utf-8")

    repository = PageRepository(pages_file, revisions_file)

    assert repository.list_pages() == []
    assert json.loads(pages_file.read_text(encoding="utf-8")) == []
    backups = sorted(tmp_path.glob("pages.invalid-root.*.json"))
    assert len(backups) == 1
