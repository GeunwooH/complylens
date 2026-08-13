"""주문 관리 + 크립토 결제 검증 + 납품 게이트."""
from __future__ import annotations

import json
import os
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import TypedDict, assert_never


class Product(TypedDict):
    name: str
    price_btc: float
    price_usd: int
    file: str


PRODUCTS: dict[str, Product] = {
    "p1-analysis": {
        "name": "LL144 Data Analysis Report",
        "price_btc": 0.0045,
        "price_usd": 299,
        "file": "p1-analysis.html",
    },
    "p2-playbook": {
        "name": "LL144 Compliance Playbook",
        "price_btc": 0.00075,
        "price_usd": 49,
        "file": "ll144-playbook.html",
    },
    "p3-custom": {
        "name": "Multi-State Compliance Pack",
        "price_btc": 0.003,
        "price_usd": 199,
        "file": "p3-custom.html",
    },
    "p4-euaiakit": {
        "name": "EU AI Act Readiness Kit",
        "price_btc": 0.0022,
        "price_usd": 149,
        "file": "eu-ai-act-kit.html",
    },
    "p5-vendor": {
        "name": "LL144 Vendor Comparison Pack",
        "price_btc": 0.00045,
        "price_usd": 29,
        "file": "p5-vendor-comparison.html",
    },
    "p6-soc2": {
        "name": "SOC2 Under $5k Startup Playbook",
        "price_btc": 0.00075,
        "price_usd": 49,
        "file": "p6-soc2-playbook.html",
    },
}

_BTC_TO_SAT = 100_000_000
_ATTRIBUTION_KEYS = (
    "source",
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_content",
)


class PaymentMethod(StrEnum):
    BTC = "btc"
    STRIPE = "stripe"


@dataclass(frozen=True, slots=True)
class PaymentConflict(ValueError):
    """주문 결제 경로 또는 결제 식별자가 현재 주문과 충돌함."""

    detail: str

    def __str__(self) -> str:
        return self.detail


def _clean_attribution(value: object) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    cleaned: dict[str, str] = {}
    for key in _ATTRIBUTION_KEYS:
        raw = value.get(key)
        if isinstance(raw, str):
            item = raw.strip()
            if item:
                cleaned[key] = item[:80]
    return cleaned


class OrderStore:
    def __init__(self, data_dir: Path) -> None:
        self._dir = Path(data_dir) / "orders"
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, order_id: str) -> Path:
        return self._dir / f"{order_id}.json"

    def create(
        self,
        email: str,
        product_id: str,
        attribution: object = None,
        payment_method: PaymentMethod = PaymentMethod.BTC,
    ) -> dict:
        product = PRODUCTS[product_id]
        order = {
            "order_id": __import__("uuid").uuid4().hex[:12],
            "email": email,
            "product_id": product_id,
            "product_name": product["name"],
            "status": "pending",
            "payment_method": payment_method.value,
            "created_at": datetime.now(UTC).isoformat(),
            "attribution": _clean_attribution(attribution),
        }
        match payment_method:
            case PaymentMethod.BTC:
                order.update(
                    {
                        "amount_btc": product["price_btc"],
                        "amount_sat": int(product["price_btc"] * _BTC_TO_SAT),
                        "btc_address": os.environ.get("BTC_ADDRESS", ""),
                    }
                )
            case PaymentMethod.STRIPE:
                order["stripe_session_id"] = None
            case unreachable:
                assert_never(unreachable)
        self._path(order["order_id"]).write_text(json.dumps(order, indent=2), encoding="utf-8")
        return order

    def get(self, order_id: str) -> dict:
        path = self._path(order_id)
        if not path.exists():
            raise KeyError(order_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def confirm(
        self,
        order_id: str,
        payment_reference: str,
        payment_method: PaymentMethod = PaymentMethod.BTC,
    ) -> dict:
        order = self.get(order_id)
        if order["payment_method"] != payment_method.value:
            raise PaymentConflict(
                f"order payment method is {order['payment_method']}, not {payment_method.value}"
            )
        if order["status"] == "confirmed":
            return order
        if order["status"] != "pending":
            raise PaymentConflict(f"order is not payable: {order['status']}")
        order["status"] = "confirmed"
        order["payment_method"] = payment_method.value
        match payment_method:
            case PaymentMethod.BTC:
                order["txid"] = payment_reference
            case PaymentMethod.STRIPE:
                order["stripe_session_id"] = payment_reference
            case unreachable:
                assert_never(unreachable)
        order["confirmed_at"] = datetime.now(UTC).isoformat()
        self._path(order_id).write_text(json.dumps(order, indent=2), encoding="utf-8")
        return order

    def attach_stripe_session(self, order_id: str, session_id: str) -> dict:
        """Persist the Checkout session created for a pending Stripe order."""
        order = self.get(order_id)
        if order["payment_method"] != PaymentMethod.STRIPE.value:
            raise PaymentConflict("order is not a Stripe order")
        if not session_id:
            raise PaymentConflict("Stripe Checkout session ID is missing")
        existing = order.get("stripe_session_id")
        if existing is not None and existing != session_id:
            raise PaymentConflict("Stripe Checkout session already attached")
        order["stripe_session_id"] = session_id
        self._path(order_id).write_text(json.dumps(order, indent=2), encoding="utf-8")
        return order

    def fail_checkout(self, order_id: str, detail: str) -> dict:
        """Record a failed Stripe Checkout attempt without leaving a payable order."""
        order = self.get(order_id)
        if order["payment_method"] != PaymentMethod.STRIPE.value:
            raise PaymentConflict("order is not a Stripe order")
        if order["status"] == "pending":
            order["status"] = "checkout_failed"
            order["payment_error"] = detail
            self._path(order_id).write_text(json.dumps(order, indent=2), encoding="utf-8")
        return order

    def confirm_stripe(self, order_id: str, session_id: str, event_id: str) -> dict:
        """Confirm one exact, paid Stripe Checkout session exactly once."""
        order = self.get(order_id)
        if order["payment_method"] != PaymentMethod.STRIPE.value:
            raise PaymentConflict("order is not a Stripe order")
        if order.get("stripe_session_id") != session_id:
            raise PaymentConflict("Stripe Checkout session does not match order")
        if order["status"] == "confirmed":
            if order.get("stripe_event_id") == event_id:
                return order
            raise PaymentConflict("Stripe event conflicts with confirmed order")
        if order["status"] != "pending":
            raise PaymentConflict(f"order is not payable: {order['status']}")
        order["status"] = "confirmed"
        order["stripe_event_id"] = event_id
        order["stripe_session_id"] = session_id
        order["confirmed_at"] = datetime.now(UTC).isoformat()
        self._path(order_id).write_text(json.dumps(order, indent=2), encoding="utf-8")
        return order

    def txid_used(self, txid: str, exclude_order_id: str | None = None) -> bool:
        for path in self._dir.glob("*.json"):
            order = json.loads(path.read_text(encoding="utf-8"))
            if order.get("txid") == txid and order["order_id"] != exclude_order_id:
                return True
        return False


def verify_btc_payment(txid: str, expected_address: str, expected_sat: int) -> bool:
    if not txid or len(txid) != 64 or any(c not in "0123456789abcdef" for c in txid.lower()):
        return False
    try:
        with urllib.request.urlopen(
            f"https://blockstream.info/api/tx/{txid}", timeout=15
        ) as resp:
            tx = json.loads(resp.read().decode())
    except (OSError, ValueError, KeyError):
        return False
    # H1: 0-conf 거부 — 블록 확정된 거래만 수락 (RBF/이중지불 방지)
    status = tx.get("status", {})
    if not status.get("confirmed"):
        return False
    received = sum(
        out.get("value", 0)
        for out in tx.get("vout", [])
        if out.get("scriptpubkey_address") == expected_address
    )
    return received >= expected_sat
