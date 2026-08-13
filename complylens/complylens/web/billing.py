"""주문 상태 머신 + Stripe Checkout/웹훅 처리."""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict

import stripe

AUDIT_PRICE_USD = 1500

_TRANSITIONS = {
    "created": {"paid"},
    "paid": {"audit_in_progress"},
    "audit_in_progress": {"delivered"},
    "delivered": {"completed"},
}


class InvalidTransition(ValueError):
    """허용되지 않는 주문 상태 전이."""


@dataclass(frozen=True, slots=True)
class StripeConfigurationError(RuntimeError):
    """Stripe secret key 또는 Checkout 응답이 유효하지 않음."""

    detail: str

    def __str__(self) -> str:
        return self.detail


class CheckoutSessionResult(TypedDict):
    session_id: str
    checkout_url: str


class OrderStore:
    def __init__(self, data_dir: Path) -> None:
        self._dir = Path(data_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, order_id: str) -> Path:
        return self._dir / f"{order_id}.json"

    def create(self, tool_description: str) -> dict:
        order = {
            "order_id": uuid.uuid4().hex[:12],
            "status": "created",
            "tool_description": tool_description,
            "amount_usd": AUDIT_PRICE_USD,
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._write(order)
        return order

    def _write(self, order: dict) -> None:
        self._path(order["order_id"]).write_text(json.dumps(order, indent=2), encoding="utf-8")

    def get(self, order_id: str) -> dict:
        path = self._path(order_id)
        if not path.exists():
            raise KeyError(f"order not found: {order_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def transition(self, order_id: str, to_status: str) -> dict:
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


def _stripe() -> None:
    secret_key = os.environ.get("STRIPE_SECRET_KEY")
    if not secret_key:
        raise StripeConfigurationError("Stripe payment is not configured")
    stripe.api_key = secret_key


def _checkout_idempotency_key(order_id: str) -> str:
    return f"complylens-checkout-{order_id}"


def create_checkout_session(order_id: str, success_url: str = "https://example.com/success", cancel_url: str = "https://example.com/cancel") -> str:
    _stripe()
    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "unit_amount": AUDIT_PRICE_USD * 100,
                    "product_data": {"name": "LL144 Bias Audit"},
                },
                "quantity": 1,
            }
        ],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"order_id": order_id},
        idempotency_key=_checkout_idempotency_key(order_id),
    )
    return session.id


def create_product_checkout_session(
    order_id: str,
    product_id: str,
    product_name: str,
    amount_usd: int,
    customer_email: str,
    success_url: str,
    cancel_url: str,
) -> CheckoutSessionResult:
    """제품 주문을 Stripe hosted Checkout 세션으로 변환한다."""
    secret_key = os.environ.get("STRIPE_SECRET_KEY")
    if not secret_key:
        raise StripeConfigurationError("Stripe payment is not configured")
    stripe.api_key = secret_key
    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "unit_amount": amount_usd * 100,
                    "product_data": {"name": product_name},
                },
                "quantity": 1,
            }
        ],
        customer_email=customer_email,
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"order_id": order_id, "product_id": product_id},
        idempotency_key=_checkout_idempotency_key(order_id),
    )
    session_id = getattr(session, "id", None)
    checkout_url = getattr(session, "url", None)
    if not isinstance(session_id, str) or not session_id:
        raise StripeConfigurationError("Stripe Checkout session ID is missing")
    if not isinstance(checkout_url, str) or not checkout_url:
        raise StripeConfigurationError("Stripe Checkout URL is missing")
    return {"session_id": session_id, "checkout_url": checkout_url}


def handle_checkout_webhook(payload: bytes, sig_header: str, secret: str, store: OrderStore) -> str:
    event = stripe.Webhook.construct_event(payload, sig_header, secret)
    if event["type"] == "checkout.session.completed":
        order_id = event["data"]["object"]["metadata"]["order_id"]
        store.transition(order_id, "paid")
        return order_id
    raise ValueError(f"unsupported event type: {event['type']}")
