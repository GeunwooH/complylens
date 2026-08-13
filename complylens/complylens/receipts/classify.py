"""계정과목 분류 — 결정적 키워드 규칙 + GPT(openai) 우선 분류 (폴백 보장).

- `CategoryClassifier.classify(text, item_names)` → Classification (파이프라인 계약)
- gateway(LLMGateway)를 주입하면 GPT 분류를 먼저 시도하고, 실패/미응답 시
  결정적 키워드 규칙으로 폴백 — 키가 없거나 오프라인에서도 항상 동작한다.
"""
from __future__ import annotations

import json
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from complylens.llm.gateway import LLMGateway, Provider
from complylens.receipts.schema import AccountCategory, LedgerEntry, ReceiptItem

_logger = logging.getLogger(__name__)

ACCOUNT_CATEGORIES: tuple[str, ...] = tuple(category.value for category in AccountCategory)

# 계정과목별 키워드 — 검사 순서가 우선순위다 (앞에서부터 일치하는 과목).
_DEFAULT_KEYWORDS: dict[AccountCategory, Sequence[str]] = {
    AccountCategory.FOOD: ("식당", "밥", "김밥", "설렁탕", "구수", "국수", "식사", "치킨", "피자", "카페", "커피"),
    AccountCategory.SUPPLIES: ("소모품", "휴지", "종이", "세제", "비누", "물티슈", "사무용품", "문구"),
    AccountCategory.RENT: ("임대료", "월세", "보증금", "부동산", "관리소"),
    AccountCategory.MATERIALS: ("재료", "자재", "고기", "채소", "야채", "밀가루"),
    AccountCategory.TRANSPORT: ("교통", "택시", "지하철", "버스", "주유", "고속도로", "주차"),
    AccountCategory.UTILITIES: ("관리비", "전기", "수도", "가스", "인터넷", "통신"),
}

_CLASSIFY_PROMPT = (
    "영수증 거래를 계정과목 하나로 분류해 JSON으로 출력해. "
    '응답 형식: {{"category": "...", "confidence": 0.0~1.0}}. '
    "후보: " + ", ".join(ACCOUNT_CATEGORIES) + ". "
    "category는 후보 중 하나만, 다른 키는 추가하지 마. "
    '거래처/품목: "{text}"'
)


@dataclass(frozen=True)
class Classification:
    """분류 결과 — 파이프라인 카드/장부가 사용하는 계약."""

    category: str
    confidence: float
    source: str  # "llm" | "rule"


class CategoryClassifier:
    """계정과목 분류기 — GPT 우선, 결정적 키워드 규칙 폴백."""

    def __init__(
        self,
        category_map: Mapping[str, Sequence[str]] | None = None,
        gateway: LLMGateway | None = None,
    ) -> None:
        self._rules: dict[AccountCategory, Sequence[str]] = dict(_DEFAULT_KEYWORDS)
        if category_map:
            for category, keywords in category_map.items():
                resolved = AccountCategory(category)
                self._rules[resolved] = tuple(keywords)
        self._gateway = gateway if gateway is not None else self._default_gateway()

    @staticmethod
    def _default_gateway() -> LLMGateway | None:
        """OPENAI_API_KEY가 설정된 경우에만 GPT-4o mini 게이트웨이를 만든다."""
        providers = [
            Provider(
                "openai",
                "https://api.openai.com/v1",
                "OPENAI_API_KEY",
                "gpt-4o-mini",
                "non_prc",
            )
        ]
        gateway = LLMGateway(providers)
        if not gateway.configured_provider_names():
            return None
        return gateway

    def classify(
        self,
        text: str,
        item_names: Sequence[str] | None = None,
    ) -> Classification:
        """text(지점명)와 item_names(품목명)를 합쳐 계정과목으로 분류한다.

        GPT 분류를 먼저 시도하고, 실패/미설정 시 결정적 키워드 규칙으로 폴백한다.
        """
        haystack = " ".join(filter(None, [text, *(item_names or [])])).strip()
        if not haystack:
            return Classification(AccountCategory.OTHER.value, 1.0, "rule")
        if self._gateway is not None:
            llm_result = self._classify_with_llm(haystack)
            if llm_result is not None:
                return llm_result
        return self._classify_rules(haystack)

    def _classify_with_llm(self, haystack: str) -> Classification | None:
        """GPT 분류 — 실패/비정상 응답(카테고리 후보 밖)이면 None(규칙 폴백)."""
        gateway = self._gateway
        if gateway is None:
            return None
        try:
            raw = gateway.complete(_CLASSIFY_PROMPT.format(text=haystack))
        except Exception as exc:  # noqa: BLE001 - LLM 실패는 규칙 폴백으로 안전 처리
            _logger.warning("LLM classification failed, rule fallback: %s", exc)
            return None
        try:
            doc = json.loads(raw[raw.find("{") : raw.rfind("}") + 1])
        except (ValueError, json.JSONDecodeError) as exc:
            _logger.warning("LLM classification unparseable, rule fallback: %s", exc)
            return None
        category = str(doc.get("category", "")).strip()
        if category not in ACCOUNT_CATEGORIES:
            _logger.warning("LLM category %r not in %s → rule fallback", category, ACCOUNT_CATEGORIES)
            return None
        try:
            confidence = float(doc.get("confidence", 0.8))
        except (TypeError, ValueError):
            confidence = 0.8
        return Classification(category, min(max(confidence, 0.0), 1.0), "llm")

    def _classify_rules(self, haystack: str) -> Classification:
        for category, keywords in self._rules.items():
            for keyword in keywords:
                if keyword in haystack:
                    return Classification(category.value, 0.9, "rule")
        return Classification(AccountCategory.OTHER.value, 0.6, "rule")


def classify_items(
    items: list[dict],
    category_map: Mapping[str, str] | None = None,
) -> list[LedgerEntry]:
    """품목 리스트([{'name':..., 'price':...}])를 결정적 규칙으로 분류한다.

    category_map: 품목명 정확 일치 → 계정과목(exact name) 오버라이드.
    반환: LedgerEntry 목록 — receipt_id/category 비워 둠(저장 시점에 채움).
    잘못된 품목 dict(필드 누락 등)는 pydantic ValidationError.
    """
    entries: list[LedgerEntry] = []
    for raw in items:
        item = ReceiptItem.model_validate(raw)
        if category_map and item.name in category_map:
            category = AccountCategory(category_map[item.name])
        else:
            category = AccountCategory(CategoryClassifier().classify(item.name).category)
        entries.append(
            LedgerEntry(category=category, amount=item.price, note=item.name)
        )
    return entries