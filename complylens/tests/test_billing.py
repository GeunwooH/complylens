"""결제 테스트 — 주문 상태 머신, Stripe 체크아웃, 웹훅 멱등성."""
from __future__ import annotations

from pathlib import Path

import pytest

from complylens.web.billing import (
    InvalidTransition,
    OrderStore,
    create_checkout_session,
    handle_checkout_webhook,
)


@pytest.fixture()
def store(tmp_path: Path) -> OrderStore:
    return OrderStore(tmp_path)


def test_order_create_and_status(store: OrderStore) -> None:
    order = store.create("ToolX")
    assert order["status"] == "created"
    assert store.get(order["order_id"])["status"] == "created"


def test_transition_created_to_paid(store: OrderStore) -> None:
    order = store.create("ToolX")
    store.transition(order["order_id"], "paid")
    assert store.get(order["order_id"])["status"] == "paid"


def test_illegal_transition_rejected(store: OrderStore) -> None:
    order = store.create("ToolX")
    with pytest.raises(InvalidTransition):
        store.transition(order["order_id"], "delivered")


def test_webhook_marks_paid_and_is_idempotent(store: OrderStore, monkeypatch: pytest.MonkeyPatch) -> None:
    order = store.create("ToolX")

    def fake_construct(payload, sig, secret):
        assert sig == "test-sig"
        return {"type": "checkout.session.completed", "data": {"object": {"metadata": {"order_id": order["order_id"]}}}}

    monkeypatch.setattr("complylens.web.billing.stripe.Webhook.construct_event", fake_construct)
    order_id = handle_checkout_webhook(b"{}", "test-sig", "whsec_test", store)
    assert order_id == order["order_id"]
    assert store.get(order["order_id"])["status"] == "paid"
    handle_checkout_webhook(b"{}", "test-sig", "whsec_test", store)
    assert store.get(order["order_id"])["status"] == "paid"


def test_checkout_session_uses_1500_usd(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return type("S", (), {"id": "cs_test_123"})()

    monkeypatch.setattr("complylens.web.billing.stripe.checkout.Session.create", fake_create)
    session_id = create_checkout_session("order-1")
    assert session_id == "cs_test_123"
    assert captured["line_items"][0]["price_data"]["unit_amount"] == 150_000
    assert captured["metadata"]["order_id"] == "order-1"


def test_webhook_bad_signature_rejected(store: OrderStore, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_construct(payload, sig, secret):
        raise ValueError("signature verification failed")

    monkeypatch.setattr("complylens.web.billing.stripe.Webhook.construct_event", fake_construct)
    with pytest.raises(ValueError):
        handle_checkout_webhook(b"{}", "bad", "whsec_test", store)
