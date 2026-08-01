"""주문 상태 머신 + Stripe Checkout/웹훅 처리."""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

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
            "created_at": datetime.now(timezone.utc).isoformat(),
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
        order["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._write(order)
        return order


def _stripe() -> None:
    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "sk_test_missing")


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
    )
    return session.id


def handle_checkout_webhook(payload: bytes, sig_header: str, secret: str, store: OrderStore) -> str:
    event = stripe.Webhook.construct_event(payload, sig_header, secret)
    if event["type"] == "checkout.session.completed":
        order_id = event["data"]["object"]["metadata"]["order_id"]
        store.transition(order_id, "paid")
        return order_id
    raise ValueError(f"unsupported event type: {event['type']}")
