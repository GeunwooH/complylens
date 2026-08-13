"""Gemini OCR — 영수증 이미지를 결정적 필드(store/date/items/total/vat/payment)로 추출·검증.

- 모델: gemini-flash-lite-latest 우선, 실패 시 gemini-2.5-flash 에스컬레이션
- 프롬프트: 105장 검증된 엄격 프롬프트 그대로 사용
- generationConfig: temperature=0.0, responseMimeType=application/json
- 파싱/검증은 결정적(deterministic): JSON 파싱 → 필드 정규화 → 물품합계 vs 총액
  불일치는 조용히 수용하지 않고 needs_review(검토 필요)로 표시한다.
"""
from __future__ import annotations

import base64
import json
import logging
import math
import os
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Final

import httpx

_logger = logging.getLogger(__name__)

PRIMARY_MODEL: Final = "gemini-flash-lite-latest"
ESCALATION_MODEL: Final = "gemini-2.5-flash"
GEMINI_API_URL: Final = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)
MAX_IMAGE_BYTES: Final = 25 * 1024 * 1024
RETRY_BACKOFF_SECONDS: Final = 1.5

# 검증된 엄격 프롬프트 (ocr-90-report.md 기준 그대로 사용)
STRICT_OCR_PROMPT: Final = (
    "이 영수증 이미지에 실제로 보이는 텍스트만 추출해 JSON으로 출력해. "
    "이미지에 보이지 않는 내용은 추측하거나 추가하지 마. "
    "필드: store, date, items[{name,price}], total, vat, payment. JSON만."
)


class OCRUnavailableError(RuntimeError):
    """OCR 요청 실패 (키 부재, 네트워크 오류, 또는 두 모델 모두 실패)."""


class OCRValidationError(ValueError):
    """모델 출력이 유효한 영수증 필드로 검증되지 않음 (에스컬레이션 대상)."""


@dataclass(frozen=True)
class ReceiptItem:
    name: str
    price: int | float


@dataclass(frozen=True)
class ReceiptExtraction:
    store: str | None
    date: str | None
    items: list[ReceiptItem]
    total: int | float | None
    vat: int | float | None
    payment: str | None
    model: str
    needs_review: bool
    warnings: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    def items_sum(self) -> int | float:
        return sum(item.price for item in self.items)


# ---------------------------------------------------------------------------
# 결정적 파싱/검증 (오프라인 단위 테스트 대상)
# ---------------------------------------------------------------------------


def _money(num: float) -> int | float:
    if math.isnan(num) or math.isinf(num) or num < 0:
        raise ValueError(f"invalid money amount: {num}")
    return int(num) if num.is_integer() else num


def to_price(value: object) -> int | float | None:
    """'4,500' → 4500, 38.5 → 38.5, '1,500원' → 1500, '1.5만' → 15000."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return _money(float(value))
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    wan_match = re.fullmatch(r"(\d+(?:\.\d+)?)만", text)
    if wan_match:
        text = str(float(wan_match.group(1)) * 10000)
    else:
        text = text.replace(",", "")
        text = re.sub(r"(?i)(?:\s|원|₩|krw|\$|€|£)", "", text).strip()
    if not text:
        return None
    try:
        num = float(text)
    except ValueError:
        return None
    return _money(num)


def _strip_json_fences(text: str) -> str:
    text = text.strip()
    match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    return match.group(1) if match else text


def _extract_json_object(text: str) -> dict[str, Any]:
    """모델 출력에서 처음 등장하는 완전한 JSON 객체를 추출한다."""
    start = text.find("{")
    if start < 0:
        raise ValueError("no JSON object in OCR output")
    in_string = False
    escaped = False
    depth = 0
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : index + 1])
    raise ValueError("unterminated JSON object in OCR output")


def parse_receipt_json(text: str) -> dict[str, Any]:
    """원시 모델 출력 → 영수증 dict (결정적)."""
    body = _strip_json_fences(text)
    if not body:
        raise OCRValidationError("empty OCR output")
    if body.startswith("```"):
        raise OCRValidationError("unclosed JSON fence in OCR output")
    try:
        doc = _extract_json_object(body)
    except (ValueError, json.JSONDecodeError) as exc:
        raise OCRValidationError(f"unparseable OCR JSON: {exc}") from exc
    if not isinstance(doc, dict):
        raise OCRValidationError("OCR output is not a JSON object")
    return doc


def validate_receipt_fields(doc: dict[str, Any], model: str) -> ReceiptExtraction:
    """파싱된 dict를 필드 규칙으로 검증한다 (결정적).

    - 필수: store(비어 있지 않은 문자열), date, items(비어 있지 않은 목록), total(금액)
    - 금액/부가세/품목가격은 숫자 정규화
    - 물품합계와 total 불일치 → needs_review=True + 경고 (조용히 수용하지 않는다)
    """
    warnings: list[str] = []

    store = doc.get("store")
    if not isinstance(store, str) or not store.strip():
        raise OCRValidationError("missing store field")
    date = doc.get("date")
    if not isinstance(date, str) or not date.strip():
        raise OCRValidationError("missing date field")

    raw_items = doc.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        raise OCRValidationError("missing items field")
    items: list[ReceiptItem] = []
    for entry in raw_items:
        if not isinstance(entry, dict):
            warnings.append("품목 중 객체가 아닌 항목은 무시했습니다")
            continue
        name = entry.get("name")
        price = to_price(entry.get("price"))
        if not isinstance(name, str) or not name.strip():
            warnings.append("이름 없는 품목은 무시했습니다")
            continue
        if price is None:
            warnings.append(f"가격을 읽지 못한 품목은 무시했습니다: {name.strip()}")
            continue
        items.append(ReceiptItem(name=name.strip(), price=price))
    if not items:
        raise OCRValidationError("no readable items")

    total = to_price(doc.get("total"))
    if total is None:
        raise OCRValidationError("missing total field")
    vat = to_price(doc.get("vat"))
    payment = doc.get("payment")
    if not isinstance(payment, str) or not payment.strip():
        payment = None
        warnings.append("결제수단(payment)이 추출되지 않았습니다")

    needs_review = False
    item_sum = sum(item.price for item in items)
    tolerance = max(2.0, float(item_sum) * 0.02, float(total) * 0.02)
    if abs(float(total) - float(item_sum)) > tolerance:
        needs_review = True
        warnings.append(
            f"물품 합계({item_sum:g})가 총액({total:g})과 일치하지 않습니다 — 검토 필요"
        )

    return ReceiptExtraction(
        store=store.strip(),
        date=date.strip(),
        items=items,
        total=total,
        vat=vat,
        payment=payment,
        model=model,
        needs_review=needs_review,
        warnings=warnings,
        raw=dict(doc),
    )


@lru_cache(maxsize=1)
def default_api_key() -> str | None:
    """GEMINI_API_KEY 환경변수 → ~/.config/gemini/api_key 파일 순서로 키를 찾는다."""
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key:
        return env_key.strip()
    key_path = Path.home() / ".config" / "gemini" / "api_key"
    if key_path.exists():
        value = key_path.read_text(encoding="utf-8").strip()
        if value:
            return value
    return None


class GeminiOCRClient:
    """Gemini OCR 클라이언트 — flash-lite 우선, 인증/파싱 실패 시 2.5-flash 에스컬레이션."""

    def __init__(
        self,
        api_key: str | None = None,
        post: Callable[..., httpx.Response] | None = None,
        timeout: float = 60.0,
    ) -> None:
        self._api_key = api_key if api_key is not None else default_api_key()
        self._post = post if post is not None else self._default_post
        self._timeout = timeout

    @staticmethod
    def _default_post(
        url: str, *, headers: dict[str, str], json: dict[str, Any], timeout: float
    ) -> httpx.Response:
        return httpx.post(url, headers=headers, json=json, timeout=timeout)

    def _call_model(self, model: str, image_bytes: bytes, mime_type: str) -> str:
        if not self._api_key:
            raise OCRUnavailableError("Gemini API key is not configured")
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": base64.b64encode(image_bytes).decode("ascii"),
                            }
                        },
                        {"text": STRICT_OCR_PROMPT},
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.0,
                "responseMimeType": "application/json",
            },
        }
        url = GEMINI_API_URL.format(model=model)
        headers = {"x-goog-api-key": self._api_key, "Content-Type": "application/json"}
        for attempt in range(2):
            try:
                response = self._post(
                    url, headers=headers, json=payload, timeout=self._timeout
                )
            except (httpx.HTTPError, OSError) as exc:
                raise OCRUnavailableError(f"{model} request failed: {exc}") from exc
            if response.status_code == 429 and attempt == 0:
                time.sleep(RETRY_BACKOFF_SECONDS)
                continue
            if response.status_code != 200:
                raise OCRUnavailableError(
                    f"{model} returned HTTP {response.status_code}: {response.text[:200]}"
                )
            try:
                doc = response.json()
                parts = doc["candidates"][0]["content"]["parts"]
                text = "".join(part.get("text", "") for part in parts if part.get("text"))
                if not text.strip():
                    raise KeyError("empty text")
                return text
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                raise OCRUnavailableError(f"{model} malformed response: {exc}") from exc
        raise OCRUnavailableError(f"{model} rate limited")

    def extract(self, image_bytes: bytes, mime_type: str = "image/png") -> ReceiptExtraction:
        """프라이머리 → 에스컬레이션 순서로 시도한다.

        물품합계/총액 불일치(needs_review=True)는 모델 재시도로 해결되지 않는
        데이터 품질 문제이므로 그대로 반환해 검토 플래그를 남긴다.
        """
        failures: list[str] = []
        for model in (PRIMARY_MODEL, ESCALATION_MODEL):
            try:
                text = self._call_model(model, image_bytes, mime_type)
                extraction = validate_receipt_fields(parse_receipt_json(text), model)
                return extraction
            except OCRUnavailableError as exc:
                failures.append(str(exc))
            except OCRValidationError as exc:
                failures.append(f"{model}: {exc}")
        raise OCRUnavailableError(" | ".join(failures))