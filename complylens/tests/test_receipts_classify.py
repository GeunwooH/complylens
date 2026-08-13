"""계정과목 분류 테스트 — GPT(게이트웨이) 우선 + 결정적 규칙 폴백."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from complylens.llm.gateway import LLMGateway, Provider
from complylens.receipts.classify import (
    ACCOUNT_CATEGORIES,
    CategoryClassifier,
    Classification,
)


def _fake_client(replies: list[str]):
    """LLMGateway용 fake openai 클라이언트 — 순서대로 응답."""
    state = {"index": 0}

    def create(model, messages):
        reply = replies[state["index"] % len(replies)]
        state["index"] += 1
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=reply))]
        )

    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


def _gateway(replies: list[str], monkeypatch: pytest.MonkeyPatch) -> LLMGateway:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    return LLMGateway(
        [Provider("openai", "https://api.openai.com/v1", "OPENAI_API_KEY", "gpt-4o-mini", "non_prc")],
        client_factory=lambda base, key: _fake_client(replies),
    )


def test_llm_classification_used_when_gateway_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    classifier = CategoryClassifier(
        gateway=_gateway(['{"category": "교통비", "confidence": 0.92}'], monkeypatch)
    )
    result = classifier.classify("뭐든", item_names=["아무거나"])
    assert result == Classification("교통비", 0.92, "llm")


def test_llm_junk_output_falls_back_to_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    classifier = CategoryClassifier(gateway=_gateway(["이건 JSON이 아님"], monkeypatch))
    result = classifier.classify("서울택시 12거3456", item_names=["기본요금"])
    assert result.category == "교통비"  # 규칙 폴백
    assert result.source == "rule"


def test_llm_unknown_category_falls_back_to_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    classifier = CategoryClassifier(
        gateway=_gateway(['{"category": "없는과목", "confidence": 1.0}'], monkeypatch)
    )
    assert classifier.classify("GS25", ["삼각김밥"]).source == "rule"


def test_no_gateway_uses_rules_deterministically() -> None:
    classifier = CategoryClassifier()  # 키 없음 → 게이트웨이 None
    cases = {
        ("서울택시 12거3456", ("기본요금",)): "교통비",
        ("GS25 강남점", ("삼각김밥",)): "식대",
        ("스타벅스 강남역점", ("카페라떼",)): "식대",
        ("홈플러스 강서점", ("휴지",)): "소모품",
        ("전기요금", ()): "관리비",
        ("아무매장", ("무엇이든",)): "기타",
    }
    for (store, items), expected in cases.items():
        assert classifier.classify(store, items).category == expected, f"{store=} {items=}"


def test_classification_is_always_in_account_categories() -> None:
    no_gateway = CategoryClassifier()
    for text in ["", " ", "가나다", "서울택시", "GS25"]:
        result = no_gateway.classify(text, ["품목"])
        assert result.category in ACCOUNT_CATEGORIES


def test_classification_dataclass_contract() -> None:
    result = Classification("기타", 0.4, "rule")
    assert result.category == "기타"
    assert result.confidence == 0.4
    assert result.source == "rule"