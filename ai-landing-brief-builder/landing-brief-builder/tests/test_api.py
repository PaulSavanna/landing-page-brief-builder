from __future__ import annotations


def build_payload(**overrides: str) -> dict[str, str]:
    payload = {
        "business_name": "NovaStack",
        "niche": "Developer Tools",
        "audience": "Engineering teams",
        "offer": "AI release notes assistant",
        "tone": "Clear and expert",
        "call_to_action": "Request access",
    }
    payload.update(overrides)
    return payload


def test_healthcheck(client) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "2.0.0-test"}


def test_root_serves_frontend(client) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Landing Brief Builder" in response.text


def test_generate_page_and_fetch_preview(client) -> None:
    create_response = client.post("/api/pages", json=build_payload())
    assert create_response.status_code == 201

    page = create_response.json()
    assert page["slug"] == "novastack"
    assert page["hero_title"] == "NovaStack: AI release notes assistant for Engineering teams"
    assert page["revision"] == 1

    page_response = client.get(f"/api/pages/{page['slug']}")
    assert page_response.status_code == 200
    assert page_response.json()["business_name"] == "NovaStack"

    preview_response = client.get(f"/preview/{page['slug']}")
    assert preview_response.status_code == 200
    assert "NovaStack" in preview_response.text


def test_update_page_increments_revision_and_keeps_slug(client) -> None:
    created = client.post("/api/pages", json=build_payload()).json()

    response = client.put(
        f"/api/pages/{created['slug']}",
        json={
            **build_payload(offer="Structured release notes for product teams"),
            "expected_revision": created["revision"],
            "change_note": "Refined offer",
        },
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["slug"] == created["slug"]
    assert updated["revision"] == 2
    assert updated["offer"] == "Structured release notes for product teams"


def test_revisions_endpoint_returns_history(client) -> None:
    created = client.post("/api/pages", json=build_payload()).json()
    client.put(
        f"/api/pages/{created['slug']}",
        json={
            **build_payload(offer="Structured release notes for product teams"),
            "expected_revision": created["revision"],
            "change_note": "Refined offer",
        },
    )

    response = client.get(f"/api/pages/{created['slug']}/revisions")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 2
    assert payload["items"][0]["revision"] == 2
    assert payload["items"][0]["change_note"] == "Refined offer"


def test_stale_update_returns_409(client) -> None:
    created = client.post("/api/pages", json=build_payload()).json()

    response = client.put(
        f"/api/pages/{created['slug']}",
        json={
            **build_payload(offer="Different offer"),
            "expected_revision": 999,
            "change_note": "Trying a stale update",
        },
    )

    assert response.status_code == 409
    assert "changed since revision" in response.json()["detail"]


def test_duplicate_slug_gets_incremented(client) -> None:
    first = client.post("/api/pages", json=build_payload(business_name="Супер Ленд"))
    second = client.post("/api/pages", json=build_payload(business_name="Супер Ленд", offer="New offer"))

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["slug"] == "super-lend"
    assert second.json()["slug"] == "super-lend-2"


def test_invalid_payload_returns_validation_errors(client) -> None:
    response = client.post(
        "/api/pages",
        json={
            "business_name": "",
            "niche": "A",
            "audience": "",
            "offer": "",
            "tone": "",
            "call_to_action": "",
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert body["detail"] == "Validation failed."
    assert body["errors"]


def test_unknown_page_returns_404(client) -> None:
    response = client.get("/api/pages/missing")

    assert response.status_code == 404
    assert response.json() == {"detail": "Page not found."}
