"""페이지뷰 통계 테스트 — 기록, 집계, 인증."""
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


def test_record_pageview(client: TestClient) -> None:
    resp = client.post("/api/pv", json={"path": "/pricing.html"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "recorded"


def test_pageview_counts_accumulate(client: TestClient) -> None:
    client.post("/api/pv", json={"path": "/pricing.html"})
    client.post("/api/pv", json={"path": "/pricing.html"})
    client.post("/api/pv", json={"path": "/ll144-guide.html"})
    stats = client.get("/api/stats", headers={"X-API-Key": "test-key"})
    assert stats.status_code == 200
    body = stats.json()
    assert body["total"] == 3
    assert body["by_path"]["/pricing.html"] == 2
    assert body["by_path"]["/ll144-guide.html"] == 1


def test_pageview_referrer_is_attributed(client: TestClient) -> None:
    resp = client.post(
        "/api/pv",
        json={"path": "/plan.html", "referrer": "https://search.example/q"},
    )
    assert resp.status_code == 200
    body = client.get("/api/stats", headers={"X-API-Key": "test-key"}).json()
    assert body["by_referrer"]["https://search.example/q"] == 1


def test_pageview_referrer_drops_query_tokens(client: TestClient) -> None:
    client.post(
        "/api/pv",
        json={"path": "/plan.html?utm_source=kmong", "referrer": "https://search.example/q?token=secret"},
    )
    body = client.get("/api/stats", headers={"X-API-Key": "test-key"}).json()
    assert body["by_referrer"] == {"https://search.example/q": 1}
    assert body["by_path"] == {"/plan.html?utm_source=kmong": 1}


def test_stats_requires_auth(client: TestClient) -> None:
    resp = client.get("/api/stats")
    assert resp.status_code == 401


def test_invalid_path_rejected(client: TestClient) -> None:
    resp = client.post("/api/pv", json={"path": ""})
    assert resp.status_code == 400
