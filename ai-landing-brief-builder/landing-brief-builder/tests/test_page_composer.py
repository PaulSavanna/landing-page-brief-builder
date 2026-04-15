from landing_builder.domain.schemas import PageCreateRequest
from landing_builder.services.page_composer import PageComposer, slugify


def test_slugify_transliterates_cyrillic() -> None:
    assert slugify("Супер Ленд 24/7") == "super-lend-24-7"


def test_composer_uses_incremental_slug_suffixes() -> None:
    composer = PageComposer(existing_slugs=["novastack", "novastack-2"])
    payload = PageCreateRequest(
        business_name="NovaStack",
        niche="Developer Tools",
        audience="Engineering teams",
        offer="AI release notes assistant",
        tone="Expert and direct",
        call_to_action="Request access",
    )

    page = composer.build(payload)

    assert page.slug == "novastack-3"


def test_composer_truncates_generated_copy_to_fit_schema_limits() -> None:
    payload = PageCreateRequest(
        business_name="A" * 120,
        niche="B" * 120,
        audience="C" * 240,
        offer="D" * 240,
        tone="E" * 120,
        call_to_action="Book an intro call",
    )

    page = PageComposer().build(payload)

    assert len(page.hero_title) <= 200
    assert len(page.hero_subtitle) <= 400
    assert all(len(item) <= 240 for item in page.benefits)
    assert all(len(item.a) <= 240 and len(item.q) <= 240 for item in page.faq)


def test_composer_uses_brief_context_in_generated_copy() -> None:
    payload = PageCreateRequest(
        business_name="Northstar Ops",
        niche="Revenue operations",
        audience="RevOps leads at SaaS companies with growing inbound volume",
        offer="Qualification assistant for high-volume inbound leads",
        tone="Clear and credible",
        call_to_action="Book an intro call",
    )

    page = PageComposer().build(payload)

    assert "revenue operations" in page.hero_subtitle.lower()
    assert "book an intro call" in page.hero_subtitle.lower()
    assert any("adjacent tools" in item.lower() for item in page.benefits)
    assert any("real customer language" in item.a.lower() for item in page.faq)
