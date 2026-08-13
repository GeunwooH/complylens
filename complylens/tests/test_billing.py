"""결제 테스트 — 주문 상태 머신, Stripe 체크아웃, 웹훅 멱등성."""
from __future__ import annotations

from pathlib import Path
from typing import TypedDict

import pytest

from complylens.web import billing
from complylens.web.billing import (
    InvalidTransition,
    OrderStore,
    create_checkout_session,
    handle_checkout_webhook,
)


class PriceData(TypedDict):
    currency: str
    unit_amount: int
    product_data: dict[str, str]


class LineItem(TypedDict):
    price_data: PriceData
    quantity: int


class CheckoutArguments(TypedDict):
    mode: str
    line_items: list[LineItem]
    customer_email: str
    success_url: str
    cancel_url: str
    metadata: dict[str, str]
    idempotency_key: str


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


def test_checkout_session_requires_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)

    with pytest.raises(billing.StripeConfigurationError, match="not configured"):
        create_checkout_session("order-1")


def test_checkout_session_uses_1500_usd_and_stable_idempotency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_legacy")
    captured: dict = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return type("S", (), {"id": "cs_test_123"})()

    monkeypatch.setattr("complylens.web.billing.stripe.checkout.Session.create", fake_create)
    session_id = create_checkout_session("order-1")
    assert session_id == "cs_test_123"
    assert captured["line_items"][0]["price_data"]["unit_amount"] == 150_000
    assert captured["metadata"]["order_id"] == "order-1"
    assert captured["idempotency_key"] == "complylens-checkout-order-1"


def test_product_checkout_session_returns_hosted_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_product")
    captured: CheckoutArguments | None = None

    class FakeSession:
        id = "cs_product_123"
        url = "https://checkout.stripe.com/c/pay/product"

    def fake_create(**kwargs: CheckoutArguments) -> FakeSession:
        nonlocal captured
        captured = kwargs
        return FakeSession()

    monkeypatch.setattr("complylens.web.billing.stripe.checkout.Session.create", fake_create)

    result = billing.create_product_checkout_session(
        order_id="order-1",
        product_id="p6-soc2",
        product_name="SOC2 Under $5k Startup Playbook",
        amount_usd=49,
        customer_email="buyer@example.com",
        success_url="https://example.com/success",
        cancel_url="https://example.com/cancel",
    )

    assert result == {
        "session_id": "cs_product_123",
        "checkout_url": "https://checkout.stripe.com/c/pay/product",
    }
    assert captured is not None
    line_item = captured["line_items"][0]
    assert line_item["price_data"]["unit_amount"] == 4_900
    assert captured["customer_email"] == "buyer@example.com"
    assert captured["metadata"] == {"order_id": "order-1", "product_id": "p6-soc2"}
    assert captured["idempotency_key"] == "complylens-checkout-order-1"


def test_product_checkout_requires_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)

    with pytest.raises(billing.StripeConfigurationError, match="not configured"):
        billing.create_product_checkout_session(
            order_id="order-1",
            product_id="p6-soc2",
            product_name="SOC2 Under $5k Startup Playbook",
            amount_usd=49,
            customer_email="buyer@example.com",
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
        )


def test_product_checkout_rejects_missing_hosted_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_product")

    class SessionWithoutUrl:
        id = "cs_product_123"
        url = None

    def fake_create(**kwargs: CheckoutArguments) -> SessionWithoutUrl:
        return SessionWithoutUrl()

    monkeypatch.setattr(
        "complylens.web.billing.stripe.checkout.Session.create",
        fake_create,
    )

    with pytest.raises(billing.StripeConfigurationError, match="URL is missing"):
        billing.create_product_checkout_session(
            order_id="order-1",
            product_id="p6-soc2",
            product_name="SOC2 Under $5k Startup Playbook",
            amount_usd=49,
            customer_email="buyer@example.com",
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
        )


def test_webhook_bad_signature_rejected(store: OrderStore, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_construct(payload, sig, secret):
        raise ValueError("signature verification failed")

    monkeypatch.setattr("complylens.web.billing.stripe.Webhook.construct_event", fake_construct)
    with pytest.raises(ValueError):
        handle_checkout_webhook(b"{}", "bad", "whsec_test", store)
