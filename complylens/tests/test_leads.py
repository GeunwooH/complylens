"""리드 캡처 테스트 — 문의 폼 제출, 저장, 검증."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from complylens.web.app import app


@pytest.fixture()
def client(tmp_path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("COMPLYLENS_API_KEY", "test-key")
    monkeypatch.setenv("COMPLYLENS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("COMPLYLENS_LLM_ENABLED", "0")
    return TestClient(app)


def test_lead_submission_saved(client: TestClient) -> None:
    resp = client.post(
        "/api/leads",
        json={
            "name": "Jane Doe",
            "company": "Acme Corp",
            "email": "jane@acme.com",
            "message": "Need LL144 audit for our ATS",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "received"
    lead_id = resp.json()["lead_id"]
    stored = client.get(f"/api/leads/{lead_id}", headers={"X-API-Key": "test-key"})
    assert stored.status_code == 200
    body = stored.json()
    assert body["email"] == "jane@acme.com"
    assert body["company"] == "Acme Corp"


def test_lead_persists_source_attribution(client: TestClient) -> None:
    oversized = "x" * 100
    resp = client.post(
        "/api/leads",
        json={
            "name": "Jane Doe",
            "company": "Acme Corp",
            "email": "jane@acme.com",
            "message": "Need LL144 audit for our ATS",
            "attribution": {
                "source": "  quote-form  ",
                "utm_source": "founder",
                "utm_medium": "direct",
                "utm_campaign": oversized,
                "ignored": "not-stored",
            },
        },
    )

    assert resp.status_code == 200
    stored = client.get(
        f"/api/leads/{resp.json()['lead_id']}",
        headers={"X-API-Key": "test-key"},
    ).json()
    assert stored["attribution"] == {
        "source": "quote-form",
        "utm_source": "founder",
        "utm_medium": "direct",
        "utm_campaign": oversized[:80],
    }


def test_lead_persists_quiz_result_attribution(client: TestClient) -> None:
    resp = client.post(
        "/api/leads",
        json={
            "email": "quiz@example.com",
            "message": "QUIZ: covered=yes",
            "attribution": {"quiz_result": "covered_no_audit"},
        },
    )
    assert resp.status_code == 200
    stored = client.get(
        f"/api/leads/{resp.json()['lead_id']}",
        headers={"X-API-Key": "test-key"},
    ).json()
    assert stored["attribution"]["quiz_result"] == "covered_no_audit"


def test_lead_persists_product_and_consent_attribution(client: TestClient) -> None:
    resp = client.post(
        "/api/leads",
        json={
            "email": "buyer@example.com",
            "message": "CSV profile inquiry",
            "attribution": {
                "source": "kmong",
                "product": "kmong-csv-profile",
                "consent": "customer-confirmed",
                "email": "do-not-store@example.com",
            },
        },
    )

    assert resp.status_code == 200
    stored = client.get(
        f"/api/leads/{resp.json()['lead_id']}",
        headers={"X-API-Key": "test-key"},
    ).json()
    assert stored["attribution"] == {
        "source": "kmong",
        "product": "kmong-csv-profile",
        "consent": "customer-confirmed",
    }


def test_lead_persists_homepage_csv_attribution(client: TestClient) -> None:
    resp = client.post(
        "/api/leads",
        json={
            "email": "homepage@example.com",
            "message": "CSV profile inquiry from homepage",
            "attribution": {
                "source": "homepage",
                "product": "kmong-csv-profile",
                "consent": "customer-confirmed",
            },
        },
    )

    assert resp.status_code == 200
    stored = client.get(
        f"/api/leads/{resp.json()['lead_id']}",
        headers={"X-API-Key": "test-key"},
    ).json()
    assert stored["attribution"] == {
        "source": "homepage",
        "product": "kmong-csv-profile",
        "consent": "customer-confirmed",
    }


def test_lead_requires_authentication(client: TestClient) -> None:
    resp = client.post(
        "/api/leads",
        json={"email": "private@example.com", "message": "private"},
    )
    lead_id = resp.json()["lead_id"]
    assert client.get(f"/api/leads/{lead_id}").status_code == 401


def test_lead_requires_valid_email(client: TestClient) -> None:
    resp = client.post(
        "/api/leads",
        json={"name": "X", "company": "Y", "email": "not-an-email", "message": ""},
    )
    assert resp.status_code == 400


def test_lead_requires_message(client: TestClient) -> None:
    resp = client.post(
        "/api/leads",
        json={"name": "X", "company": "Y", "email": "a@b.com", "message": "  "},
    )
    assert resp.status_code == 400
