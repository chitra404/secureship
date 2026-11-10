from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import __version__
from app.main import app, store

client = TestClient(app)

VALID = {
    "sender": "Chitra",
    "receiver": "Ram",
    "destination": "Pokhara, Nepal",
    "item": "Laptop",
}


@pytest.fixture(autouse=True)
def clean_store():
    store.clear()
    yield
    store.clear()


def create(**overrides):
    return client.post("/api/v1/shipments", json={**VALID, **overrides})


# ---------------------------- basic endpoints -------------------------------
def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_api_status_endpoint() -> None:
    body = client.get("/api/v1/status").json()
    assert body["service"] == "secureship-api"
    assert body["version"] == __version__
    assert body["status"] == "operational"
    assert body["shipments"] == 0


def test_project_version_file_matches_app_version() -> None:
    text = Path(__file__).resolve().parent.parent.joinpath("PROJECT_VERSION").read_text()
    assert text.strip() == f"SecureShip {__version__}"


# ------------------------------- frontend -----------------------------------
def test_home_page_is_served() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "SecureShip" in response.text


def test_static_assets_are_served() -> None:
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/style.css").status_code == 200


def test_security_headers_are_present() -> None:
    response = client.get("/")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["cache-control"] == "no-store"
    assert "default-src 'self'" in response.headers["content-security-policy"]


def test_docs_page_is_not_blocked_by_csp() -> None:
    response = client.get("/docs")
    assert response.status_code == 200
    assert "content-security-policy" not in response.headers


# ------------------------------- shipments ----------------------------------
def test_create_shipment() -> None:
    response = create()
    assert response.status_code == 201
    body = response.json()
    assert body["tracking_code"].startswith("SS-")
    assert len(body["tracking_code"]) == 11
    assert body["status"] == "created"
    assert body["receiver"] == "Ram"
    assert [h["status"] for h in body["history"]] == ["created"]


def test_list_and_get_shipment() -> None:
    code = create().json()["tracking_code"]
    assert [s["tracking_code"] for s in client.get("/api/v1/shipments").json()] == [code]
    assert client.get(f"/api/v1/shipments/{code}").json()["tracking_code"] == code


def test_advance_through_all_statuses() -> None:
    code = create().json()["tracking_code"]
    seen = []
    for _ in range(3):
        response = client.post(f"/api/v1/shipments/{code}/advance")
        assert response.status_code == 200
        seen.append(response.json()["status"])
    assert seen == ["in_transit", "out_for_delivery", "delivered"]
    assert len(client.get(f"/api/v1/shipments/{code}").json()["history"]) == 4


def test_cannot_advance_after_delivered() -> None:
    code = create().json()["tracking_code"]
    for _ in range(3):
        client.post(f"/api/v1/shipments/{code}/advance")
    assert client.post(f"/api/v1/shipments/{code}/advance").status_code == 409


def test_unknown_tracking_code_returns_404() -> None:
    assert client.get("/api/v1/shipments/SS-00000000").status_code == 404
    assert client.post("/api/v1/shipments/SS-00000000/advance").status_code == 404


def test_malformed_tracking_code_returns_422() -> None:
    assert client.get("/api/v1/shipments/not-a-code").status_code == 422


@pytest.mark.parametrize(
    "bad",
    [
        {"sender": ""},
        {"receiver": "   "},
        {"item": "x" * 101},
        {"destination": "y" * 101},
    ],
)
def test_invalid_input_is_rejected(bad) -> None:
    assert create(**bad).status_code == 422


def test_unknown_fields_are_rejected() -> None:
    assert create(admin=True).status_code == 422


def test_text_is_stored_as_plain_text_not_html() -> None:
    body = create(receiver="<script>alert(1)</script>").json()
    assert body["receiver"] == "<script>alert(1)</script>"  # stored verbatim; the UI uses textContent


def test_store_limit_returns_429(monkeypatch) -> None:
    monkeypatch.setattr(store, "_limit", 2)
    assert create().status_code == 201
    assert create().status_code == 201
    assert create().status_code == 429
