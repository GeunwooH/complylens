"""보안 헤더 테스트 — CSP가 인라인 스크립트 허용 + 클릭재킹 방지 유지."""
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


def test_csp_allows_inline_scripts_and_styles(client: TestClient) -> None:
    resp = client.get("/quiz.html")
    csp = resp.headers.get("Content-Security-Policy", "")
    # 정적 사이트 전체가 인라인 JS/CSS 사용 — 차단 시 전환 퍼널(주문 폼/계산기/퀴즈) 무력화
    assert "script-src" in csp and "unsafe-inline" in csp
    assert "style-src" in csp and "unsafe-inline" in csp


def test_csp_keeps_clickjacking_protection(client: TestClient) -> None:
    resp = client.get("/")
    csp = resp.headers.get("Content-Security-Policy", "")
    assert "frame-ancestors 'none'" in csp
    assert resp.headers.get("X-Frame-Options") == "DENY"


def test_security_headers_present(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.headers.get("Strict-Transport-Security") == "max-age=31536000; includeSubDomains"
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("Referrer-Policy") == "no-referrer"
