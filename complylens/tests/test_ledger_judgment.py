"""기장의무 판정 API 테스트 (T4 — 무료 티어 장부 고도화).

소득세법 시행령 제208조 기장의무 판단 로직:
- 가군(도소매 등): 복식 3억 / 기준경비율 6천만
- 나군(제조·음식점 등): 복식 1.5억 / 기준경비율 3,600만
- 다군(부동산임대·서비스 등): 복식 7,500만 / 기준경비율 2,400만
- 전문직: 수입금액 무관 복식부기
- 신규 개업: 간편장부
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from complylens.web.app import app


@pytest.fixture()
def client(tmp_path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("COMPLYLENS_DATA_DIR", str(tmp_path))
    return TestClient(app)


def _judge(client: TestClient, **overrides) -> dict:
    payload = {"industry_group": "나", "revenue": 10_000_000, **overrides}
    resp = client.post("/api/ledger-judgment", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_judgment_small_restaurant_simple_ratio(client: TestClient) -> None:
    """음식점 매출 1,000만 → 나군 단순경비율 간편장부."""
    result = _judge(client, industry_group="나", revenue=10_000_000)
    assert result["obligation"] == "간편장부"
    assert "단순경비율" in result["reason"]
    assert result["kang"] == "나"


def test_judgment_standard_ratio_boundary(client: TestClient) -> None:
    """나군 3,600만 이상 → 기준경비율, 1.5억 미만 → 간편장부."""
    result = _judge(client, industry_group="나", revenue=36_000_000)
    assert result["obligation"] == "간편장부"
    assert "기준경비율" in result["reason"]
    # 1.5억 이상 → 복식부기
    result = _judge(client, industry_group="나", revenue=150_000_000)
    assert result["obligation"] == "복식부기"


def test_judgment_wholesale_thresholds(client: TestClient) -> None:
    """가군(도소매): 6천만 미만 단순경비율 / 3억 이상 복식."""
    assert "단순경비율" in _judge(client, industry_group="가", revenue=59_999_999)["reason"]
    assert _judge(client, industry_group="가", revenue=300_000_000)["obligation"] == "복식부기"


def test_judgment_service_thresholds(client: TestClient) -> None:
    """다군(서비스): 7,500만 이상 복식, 2,400만 미만 단순경비율."""
    assert _judge(client, industry_group="다", revenue=20_000_000)["obligation"] == "간편장부"
    assert "단순경비율" in _judge(client, industry_group="다", revenue=20_000_000)["reason"]
    assert _judge(client, industry_group="다", revenue=75_000_000)["obligation"] == "복식부기"


def test_judgment_professional_always_complex(client: TestClient) -> None:
    """전문직(의사 등)은 수입금액과 무관하게 복식부기."""
    result = _judge(client, industry_group="다", revenue=1_000_000, professional=True)
    assert result["obligation"] == "복식부기"
    assert "전문직" in result["reason"]


def test_judgment_new_business_simple(client: TestClient) -> None:
    """당해연도 신규 개업 → 간편장부."""
    result = _judge(client, industry_group="나", revenue=300_000_000, new_business=True)
    assert result["obligation"] == "간편장부"
    assert "신규" in result["reason"]


def test_judgment_validation(client: TestClient) -> None:
    """잘못된 업종군 400, 음수 매출 400."""
    assert client.post("/api/ledger-judgment", json={"industry_group": "라", "revenue": 1000}).status_code == 400
    assert client.post("/api/ledger-judgment", json={"industry_group": "나", "revenue": -1}).status_code == 400
    assert client.post("/api/ledger-judgment", json={"industry_group": "나"}).status_code == 400
