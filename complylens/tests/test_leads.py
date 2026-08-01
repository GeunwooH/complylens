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
    stored = client.get(f"/api/leads/{lead_id}")
    assert stored.status_code == 200
    body = stored.json()
    assert body["email"] == "jane@acme.com"
    assert body["company"] == "Acme Corp"


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
