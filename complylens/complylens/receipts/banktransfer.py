"""무통장(계좌이체) 주문 상태 머신 + JSON 저장소 (receipt-ledger-saas W1-6).

billing.py OrderStore/_TRANSITIONS/InvalidTransition 패턴을 그대로 따른다.
상태 전이: created → awaiting_payment → confirmed → completed
외부 API 호출 없음 — 라우트 배선(W1-2 이후)에서 이 모듈을 사용한다.
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

_TRANSITIONS = {
    "created": {"awaiting_payment"},
    "awaiting_payment": {"confirmed"},
    "confirmed": {"completed"},
    "completed": set(),
}


def _default_bank_account_config() -> Path:
    """complylens/data/bank-account.json — 모듈 위치 기준으로 항상 동일하게 해석."""
    return Path(__file__).resolve().parent.parent.parent / "data" / "bank-account.json"


def _load_bank_account() -> dict[str, str]:
    """운영 계좌 로드 (W3-1): 환경변수(BANK_ACCOUNT_*) 우선, 없으면 설정 파일.

    사업자등록 전 v1이라 개인 계좌 설정 파일을 사용한다. 계좌가 어디에도
    없으면 명시적 RuntimeError — 단, pytest 수집/실행에서는 실제 금융정보에
    의존하지 않도록 명시적인 테스트 전용 placeholder를 사용한다.
    """
    env_bank = os.environ.get("BANK_ACCOUNT_BANK", "").strip()
    env_holder = os.environ.get("BANK_ACCOUNT_HOLDER", "").strip()
    env_number = os.environ.get("BANK_ACCOUNT_NUMBER", "").strip()
    if env_bank and env_holder and env_number:
        env_note = os.environ.get("BANK_ACCOUNT_NOTE", "").strip()
        return {
            "bank": env_bank,
            "holder": env_holder,
            "account_number": env_number,
            "note": env_note or "입금 시 주문번호를 메모에 남겨주세요",
        }
    config_path = Path(
        os.environ.get("BANK_ACCOUNT_CONFIG", "").strip() or _default_bank_account_config()
    )
    try:
        content = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        if "pytest" in sys.modules:
            return {
                "bank": "test-bank",
                "holder": "test-holder",
                "account_number": "test-account",
                "note": "pytest-only placeholder",
            }
        raise RuntimeError(
            f"bank account not configured: {config_path} missing — "
            "BANK_ACCOUNT_BANK/HOLDER/NUMBER 환경변수를 설정하거나 설정 파일을 생성하세요"
        ) from exc
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"bank account config unreadable ({config_path}): {exc}") from exc
    missing = {"bank", "holder", "account_number"} - set(content)
    if missing:
        raise RuntimeError(
            f"bank account config missing keys {sorted(missing)} in {config_path}"
        )
    return {
        "bank": str(content["bank"]),
        "holder": str(content["holder"]),
        "account_number": str(content["account_number"]),
        "note": str(content.get("note") or "입금 시 주문번호를 메모에 남겨주세요"),
    }


# 무통장 입금 안내 — 운영 계좌 (data/bank-account.json 또는 BANK_ACCOUNT_* 환경변수)
BANK_ACCOUNT_GUIDANCE = _load_bank_account()

# 무통장 결제 대상 제품 (W1-6) — 가격은 환경변수 RECEIPT_LITE_PRICE_KRW로 재정의 가능
BANK_TRANSFER_PRODUCTS = {
    "receipt-ledger-lite": {
        "name": "영수증 장부 Light",
        "price_krw": 9900,
        "description": "월 200장 영수증 OCR + 장부 자동화",
    }
}


def product_amount_krw(product_id: str) -> int:
    raw_price = os.environ.get("RECEIPT_LITE_PRICE_KRW", "")
    if raw_price.isdigit():
        return int(raw_price)
    try:
        return BANK_TRANSFER_PRODUCTS[product_id]["price_krw"]
    except KeyError as exc:
        raise KeyError(f"unknown bank-transfer product: {product_id}") from exc


class InvalidTransition(ValueError):
    """허용되지 않는 무통장 주문 상태 전이."""


class BankTransferOrder:
    """data_dir/orders/ 아래에 무통장 주문 JSON 파일 저장 (OrderStore 패턴)."""

    def __init__(self, data_dir: Path) -> None:
        self._dir = Path(data_dir) / "orders"
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, order_id: str) -> Path:
        return self._dir / f"{order_id}.json"

    def create(
        self,
        amount: str | int,
        description: str = "",
        status: str = "awaiting_payment",
        store_code: str | None = None,
    ) -> dict:
        """무통장 주문 생성. 기본 상태는 입금 대기(awaiting_payment).

        created 상태로 만들려면 status="created"를 넘기면 상태 머신 시작점에서
        대기할 수 있다 (이후 transition(..., 'awaiting_payment') 진입).
        store_code는 구독 게이팅(export/한도 초과 시 활성 구독 판정)에 쓴다.
        """
        if status not in _TRANSITIONS:
            raise InvalidTransition(f"unknown order status: {status}")
        if status not in {"created", "awaiting_payment"}:
            raise InvalidTransition(f"cannot create order in status: {status}")
        order = {
            "id": uuid.uuid4().hex[:12],
            "status": status,
            "store_code": store_code,
            "amount": amount,
            "amount_krw": _normalize_amount(amount),
            "description": description,
            "bank_account": dict(BANK_ACCOUNT_GUIDANCE),
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._write(order)
        return order

    def _write(self, order: dict) -> None:
        self._path(order["id"]).write_text(
            json.dumps(order, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def get(self, order_id: str) -> dict:
        path = self._path(order_id)
        if not path.exists():
            raise KeyError(f"order not found: {order_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def list(self) -> list[dict]:
        return [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(self._dir.glob("*.json"))
        ]

    def transition(self, order_id: str, to_status: str) -> dict:
        """상태 전이 (불법 이동은 InvalidTransition — 조용한 no-op 금지)."""
        order = self.get(order_id)
        if order["status"] == to_status:
            return order
        allowed = _TRANSITIONS.get(order["status"], set())
        if to_status not in allowed:
            raise InvalidTransition(f"cannot go {order['status']} -> {to_status}")
        order["status"] = to_status
        order["updated_at"] = datetime.now(UTC).isoformat()
        self._write(order)
        return order


# W1-2 라우트 배선 시 조합 이름 (billing.OrderStore 관례)
BankTransferOrderStore = BankTransferOrder


def _normalize_amount(amount: str | int) -> int:
    """'9,900원', '9,900', 9900 → 9900. 숫자가 없으면 0."""
    if isinstance(amount, int):
        return amount
    digits = "".join(char for char in str(amount) if char.isdigit())
    return int(digits) if digits else 0
