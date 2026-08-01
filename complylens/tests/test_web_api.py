"""웹 API 테스트 — 업로드→감사→PDF/공개요약, 인증, 에러."""
from __future__ import annotations

import io
import os

import pytest
from fastapi.testclient import TestClient

from complylens.web.app import app

API_KEY = "test-key"

CSV_OK = b"candidate_id,category,selected\nm1,male,1\nm2,male,1\nf1,female,0\nf2,female,0\n"


@pytest.fixture()
def client(tmp_path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("COMPLYLENS_API_KEY", API_KEY)
    monkeypatch.setenv("COMPLYLENS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("COMPLYLENS_LLM_ENABLED", "0")
    return TestClient(app)


def _auth() -> dict[str, str]:
    return {"X-API-Key": API_KEY}


def test_upload_runs_audit_and_returns_schema(client: TestClient) -> None:
    resp = client.post(
        "/api/audits",
        files={"file": ("data.csv", io.BytesIO(CSV_OK), "text/csv")},
        data={"tool_description": "Test Screener"},
        headers=_auth(),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["audit_id"]
    assert body["result"]["highest_selection_rate"] == 1.0
    assert body["result"]["four_fifths_violations"] == ["female"]


def test_download_report_pdf(client: TestClient) -> None:
    created = client.post(
        "/api/audits",
        files={"file": ("data.csv", io.BytesIO(CSV_OK), "text/csv")},
        data={"tool_description": "Test Screener"},
        headers=_auth(),
    ).json()
    resp = client.get(f"/api/audits/{created['audit_id']}/report.pdf", headers=_auth())
    assert resp.status_code == 200
    assert resp.content[:4] == b"%PDF"


def test_public_summary_requires_no_auth(client: TestClient) -> None:
    created = client.post(
        "/api/audits",
        files={"file": ("data.csv", io.BytesIO(CSV_OK), "text/csv")},
        data={"tool_description": "Test Screener"},
        headers=_auth(),
    ).json()
    resp = client.get(f"/api/audits/{created['audit_id']}/summary")
    assert resp.status_code == 200
    assert "Bias Audit Public Summary" in resp.text


def test_upload_without_auth_rejected(client: TestClient) -> None:
    resp = client.post(
        "/api/audits",
        files={"file": ("data.csv", io.BytesIO(CSV_OK), "text/csv")},
        data={"tool_description": "Test Screener"},
    )
    assert resp.status_code == 401


def test_corrupt_csv_rejected(client: TestClient) -> None:
    resp = client.post(
        "/api/audits",
        files={"file": ("data.csv", io.BytesIO(b"not,a,csv\n"), "text/csv")},
        data={"tool_description": "Test Screener"},
        headers=_auth(),
    )
    assert resp.status_code == 400


def test_missing_required_category_rejected(client: TestClient) -> None:
    resp = client.post(
        "/api/audits",
        files={"file": ("data.csv", io.BytesIO(CSV_OK), "text/csv")},
        data={"tool_description": ""},
        headers=_auth(),
    )
    assert resp.status_code == 422  # FastAPI 필수 Form 검증이 빈 값 거부


def test_unknown_audit_404(client: TestClient) -> None:
    resp = client.get("/api/audits/nonexistent", headers=_auth())
    assert resp.status_code == 404
