"""웹 API 테스트 — 업로드→감사→PDF/공개요약, 인증, 에러."""
from __future__ import annotations

import io
import json
from pathlib import Path
from typing import TypedDict

import pytest
from fastapi.testclient import TestClient

from complylens.web.app import app

API_KEY = "test-key"

CSV_OK = b"candidate_id,category,selected\nm1,male,1\nm2,male,1\nf1,female,0\nf2,female,0\n"


class CheckoutMetadata(TypedDict):
    order_id: str
    product_id: str


class CheckoutObject(TypedDict):
    id: str
    metadata: CheckoutMetadata
    payment_status: str
    amount_total: int
    currency: str


class CheckoutData(TypedDict):
    object: CheckoutObject


class CheckoutEvent(TypedDict):
    id: str
    type: str
    data: CheckoutData


@pytest.fixture()
def client(tmp_path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("COMPLYLENS_API_KEY", API_KEY)
    monkeypatch.setenv("COMPLYLENS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("COMPLYLENS_LLM_ENABLED", "0")
    return TestClient(app)


def _auth() -> dict[str, str]:
    return {"X-API-Key": API_KEY}


def test_upload_runs_audit_and_returns_schema(client: TestClient) -> None:
    resp = client.post(
        "/api/audits",
        files={"file": ("data.csv", io.BytesIO(CSV_OK), "text/csv")},
        data={"tool_description": "Test Screener"},
        headers=_auth(),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["audit_id"]
    assert body["result"]["highest_selection_rate"] == 1.0
    assert body["result"]["four_fifths_violations"] == ["female"]


def test_download_report_pdf(client: TestClient) -> None:
    created = client.post(
        "/api/audits",
        files={"file": ("data.csv", io.BytesIO(CSV_OK), "text/csv")},
        data={"tool_description": "Test Screener"},
        headers=_auth(),
    ).json()
    signoff = client.post(
        f"/api/audits/{created['audit_id']}/signoff",
        json={"signer": "Jane Auditor"},
        headers=_auth(),
    )
    assert signoff.status_code == 200
    resp = client.get(f"/api/audits/{created['audit_id']}/report.pdf", headers=_auth())
    assert resp.status_code == 200
    assert resp.content[:4] == b"%PDF"


def test_download_report_requires_independent_signoff(client: TestClient) -> None:
    created = client.post(
        "/api/audits",
        files={"file": ("data.csv", io.BytesIO(CSV_OK), "text/csv")},
        data={"tool_description": "Test Screener"},
        headers=_auth(),
    ).json()

    resp = client.get(f"/api/audits/{created['audit_id']}/report.pdf", headers=_auth())

    assert resp.status_code == 409
    assert resp.json()["detail"] == "independent-auditor signoff required"


def test_public_summary_requires_no_auth(client: TestClient) -> None:
    created = client.post(
        "/api/audits",
        files={"file": ("data.csv", io.BytesIO(CSV_OK), "text/csv")},
        data={"tool_description": "Test Screener"},
        headers=_auth(),
    ).json()
    signoff = client.post(
        f"/api/audits/{created['audit_id']}/signoff",
        json={"signer": "Jane Auditor"},
        headers=_auth(),
    )
    assert signoff.status_code == 200
    resp = client.get(f"/api/audits/{created['audit_id']}/summary")
    assert resp.status_code == 200
    assert "Bias Audit Public Summary" in resp.text


def test_public_summary_requires_independent_signoff(client: TestClient) -> None:
    created = client.post(
        "/api/audits",
        files={"file": ("data.csv", io.BytesIO(CSV_OK), "text/csv")},
        data={"tool_description": "Test Screener"},
        headers=_auth(),
    ).json()

    resp = client.get(f"/api/audits/{created['audit_id']}/summary")

    assert resp.status_code == 409
    assert resp.json()["detail"] == "independent-auditor signoff required"


def test_upload_without_auth_rejected(client: TestClient) -> None:
    resp = client.post(
        "/api/audits",
        files={"file": ("data.csv", io.BytesIO(CSV_OK), "text/csv")},
        data={"tool_description": "Test Screener"},
    )
    assert resp.status_code == 401


def test_corrupt_csv_rejected(client: TestClient) -> None:
    resp = client.post(
        "/api/audits",
        files={"file": ("data.csv", io.BytesIO(b"not,a,csv\n"), "text/csv")},
        data={"tool_description": "Test Screener"},
        headers=_auth(),
    )
    assert resp.status_code == 400


def test_upload_rejects_payload_over_configured_limit(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("complylens.web.app.MAX_UPLOAD_BYTES", 4)

    resp = client.post(
        "/api/audits",
        files={"file": ("data.csv", io.BytesIO(CSV_OK), "text/csv")},
        data={"tool_description": "Test Screener"},
        headers=_auth(),
    )

    assert resp.status_code == 413
    assert resp.json()["detail"] == "CSV exceeds the 100 MB limit"


def test_upload_records_processing_sla_timestamps(
    client: TestClient,
    tmp_path: Path,
) -> None:
    resp = client.post(
        "/api/audits",
        files={"file": ("data.csv", io.BytesIO(CSV_OK), "text/csv")},
        data={"tool_description": "Test Screener"},
        headers=_auth(),
    )
    audit_id = resp.json()["audit_id"]
    record = json.loads(
        (tmp_path / audit_id / "record.json").read_text(encoding="utf-8")
    )

    assert record["processing_started_at"]
    assert record["processing_completed_at"]
    assert record["sla_due_at"]


def test_missing_required_category_rejected(client: TestClient) -> None:
    resp = client.post(
        "/api/audits",
        files={"file": ("data.csv", io.BytesIO(CSV_OK), "text/csv")},
        data={"tool_description": ""},
        headers=_auth(),
    )
    assert resp.status_code == 422  # FastAPI 필수 Form 검증이 빈 값 거부


def test_unknown_audit_404(client: TestClient) -> None:
    resp = client.get("/api/audits/nonexistent", headers=_auth())
    assert resp.status_code == 404


def test_audit_id_traversal_is_rejected(client: TestClient, tmp_path) -> None:
    (tmp_path.parent / "summary.html").write_text("SECRET", encoding="utf-8")

    resp = client.get("/api/audits/%2e%2e/summary")

    assert resp.status_code == 404
    assert "SECRET" not in resp.text


def test_create_order_uses_stripe_checkout_when_enabled(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLYLENS_PAYMENT_MODE", "stripe")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_checkout")

    def fake_checkout(**kwargs: str) -> dict[str, str]:
        assert kwargs["order_id"]
        assert kwargs["product_id"] == "p2-playbook"
        return {
            "session_id": "cs_test_checkout",
            "checkout_url": "https://checkout.stripe.com/c/pay/test",
        }

    monkeypatch.setattr(
        "complylens.web.app.create_product_checkout_session",
        fake_checkout,
        raising=False,
    )

    resp = client.post(
        "/api/orders",
        json={"email": "buyer@example.com", "product_id": "p2-playbook"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["payment_method"] == "stripe"
    assert body["checkout_url"] == "https://checkout.stripe.com/c/pay/test"
    assert body["stripe_session_id"] == "cs_test_checkout"


def test_create_order_stripe_mode_without_secret_returns_configuration_error(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLYLENS_PAYMENT_MODE", "stripe")
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)

    resp = client.post(
        "/api/orders",
        json={"email": "buyer@example.com", "product_id": "p2-playbook"},
    )

    assert resp.status_code == 503
    assert resp.json()["detail"] == "Stripe payment is not configured"


def test_payment_mode_endpoint_reflects_feature_flag(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLYLENS_PAYMENT_MODE", "stripe")

    resp = client.get("/api/payment-mode")

    assert resp.status_code == 200
    assert resp.json() == {"payment_method": "stripe"}


def test_stripe_webhook_is_disabled_until_stripe_mode_enabled(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("COMPLYLENS_PAYMENT_MODE", raising=False)
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")

    resp = client.post(
        "/api/stripe/webhook",
        content=b"{}",
        headers={"stripe-signature": "sig_test"},
    )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Stripe payment is disabled"


def test_stripe_webhook_confirms_order_and_unlocks_download(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLYLENS_PAYMENT_MODE", "stripe")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")

    def fake_checkout(**kwargs: str) -> dict[str, str]:
        return {
            "session_id": "cs_test_checkout",
            "checkout_url": "https://checkout.stripe.com/c/pay/test",
        }

    monkeypatch.setattr(
        "complylens.web.app.create_product_checkout_session",
        fake_checkout,
    )
    order = client.post(
        "/api/orders",
        json={"email": "buyer@example.com", "product_id": "p2-playbook"},
    ).json()

    def fake_construct(payload: bytes, signature: str, secret: str) -> CheckoutEvent:
        assert payload == b"{}"
        assert signature == "sig_test"
        assert secret == "whsec_test"
        return {
            "id": "evt_test_checkout",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_checkout",
                    "metadata": {
                        "order_id": order["order_id"],
                        "product_id": "p2-playbook",
                    },
                    "payment_status": "paid",
                    "amount_total": 4900,
                    "currency": "usd",
                }
            },
        }

    monkeypatch.setattr(
        "complylens.web.billing.stripe.Webhook.construct_event",
        fake_construct,
    )

    webhook = client.post(
        "/api/stripe/webhook",
        content=b"{}",
        headers={"stripe-signature": "sig_test"},
    )

    assert webhook.status_code == 200
    assert webhook.json() == {
        "order_id": order["order_id"],
        "status": "confirmed",
    }
    download = client.get(f"/api/orders/{order['order_id']}/download")
    assert download.status_code == 200
    assert "Compliance Playbook" in download.text


def test_stripe_webhook_rejects_unpaid_session(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLYLENS_PAYMENT_MODE", "stripe")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_checkout")

    monkeypatch.setattr(
        "complylens.web.app.create_product_checkout_session",
        lambda **kwargs: {
            "session_id": "cs_test_unpaid",
            "checkout_url": "https://checkout.stripe.com/c/pay/unpaid",
        },
    )
    order = client.post(
        "/api/orders",
        json={"email": "buyer@example.com", "product_id": "p2-playbook"},
    ).json()
    monkeypatch.setattr(
        "complylens.web.billing.stripe.Webhook.construct_event",
        lambda *_args: {
            "id": "evt_test_unpaid",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_unpaid",
                    "metadata": {
                        "order_id": order["order_id"],
                        "product_id": "p2-playbook",
                    },
                    "payment_status": "unpaid",
                    "amount_total": 4900,
                    "currency": "usd",
                }
            },
        },
    )

    webhook = client.post(
        "/api/stripe/webhook",
        content=b"{}",
        headers={"stripe-signature": "sig_test"},
    )

    assert webhook.status_code == 402
    assert client.get(f"/api/orders/{order['order_id']}/download").status_code == 403


def test_stripe_webhook_rejects_wrong_amount(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLYLENS_PAYMENT_MODE", "stripe")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_checkout")
    monkeypatch.setattr(
        "complylens.web.app.create_product_checkout_session",
        lambda **kwargs: {
            "session_id": "cs_test_wrong_amount",
            "checkout_url": "https://checkout.stripe.com/c/pay/wrong-amount",
        },
    )
    order = client.post(
        "/api/orders",
        json={"email": "buyer@example.com", "product_id": "p2-playbook"},
    ).json()
    monkeypatch.setattr(
        "complylens.web.billing.stripe.Webhook.construct_event",
        lambda *_args: {
            "id": "evt_test_wrong_amount",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_wrong_amount",
                    "metadata": {
                        "order_id": order["order_id"],
                        "product_id": "p2-playbook",
                    },
                    "payment_status": "paid",
                    "amount_total": 1,
                    "currency": "usd",
                }
            },
        },
    )

    webhook = client.post(
        "/api/stripe/webhook",
        content=b"{}",
        headers={"stripe-signature": "sig_test"},
    )

    assert webhook.status_code == 402
    assert client.get(f"/api/orders/{order['order_id']}/download").status_code == 403


def test_stripe_webhook_rejects_mismatched_session(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLYLENS_PAYMENT_MODE", "stripe")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_checkout")
    monkeypatch.setattr(
        "complylens.web.app.create_product_checkout_session",
        lambda **kwargs: {
            "session_id": "cs_expected",
            "checkout_url": "https://checkout.stripe.com/c/pay/expected",
        },
    )
    order = client.post(
        "/api/orders",
        json={"email": "buyer@example.com", "product_id": "p2-playbook"},
    ).json()
    monkeypatch.setattr(
        "complylens.web.billing.stripe.Webhook.construct_event",
        lambda *_args: {
            "id": "evt_test_mismatched_session",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_other",
                    "metadata": {
                        "order_id": order["order_id"],
                        "product_id": "p2-playbook",
                    },
                    "payment_status": "paid",
                    "amount_total": 4900,
                    "currency": "usd",
                }
            },
        },
    )

    webhook = client.post(
        "/api/stripe/webhook",
        content=b"{}",
        headers={"stripe-signature": "sig_test"},
    )

    assert webhook.status_code == 409
    assert client.get(f"/api/orders/{order['order_id']}/download").status_code == 403


def test_btc_confirmation_cannot_confirm_stripe_order(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLYLENS_PAYMENT_MODE", "stripe")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_checkout")
    monkeypatch.setattr(
        "complylens.web.app.create_product_checkout_session",
        lambda **kwargs: {
            "session_id": "cs_test_cross_method",
            "checkout_url": "https://checkout.stripe.com/c/pay/cross-method",
        },
    )
    order = client.post(
        "/api/orders",
        json={"email": "buyer@example.com", "product_id": "p2-playbook"},
    ).json()
    monkeypatch.setattr("complylens.web.app.verify_btc_payment", lambda *_args: True)

    response = client.post(
        f"/api/orders/{order['order_id']}/confirm",
        json={"txid": "deadbeef" * 8},
    )

    assert response.status_code == 409
    assert client.get(f"/api/orders/{order['order_id']}/download").status_code == 403


def test_stripe_webhook_replay_is_idempotent_and_conflicts_are_rejected(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLYLENS_PAYMENT_MODE", "stripe")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_checkout")
    monkeypatch.setattr(
        "complylens.web.app.create_product_checkout_session",
        lambda **kwargs: {
            "session_id": "cs_test_replay",
            "checkout_url": "https://checkout.stripe.com/c/pay/replay",
        },
    )
    order = client.post(
        "/api/orders",
        json={"email": "buyer@example.com", "product_id": "p2-playbook"},
    ).json()
    event = {
        "id": "evt_test_replay",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_replay",
                "metadata": {
                    "order_id": order["order_id"],
                    "product_id": "p2-playbook",
                },
                "payment_status": "paid",
                "amount_total": 4900,
                "currency": "usd",
            }
        },
    }
    monkeypatch.setattr(
        "complylens.web.billing.stripe.Webhook.construct_event",
        lambda *_args: event,
    )

    first = client.post(
        "/api/stripe/webhook",
        content=b"{}",
        headers={"stripe-signature": "sig_test"},
    )
    replay = client.post(
        "/api/stripe/webhook",
        content=b"{}",
        headers={"stripe-signature": "sig_test"},
    )
    event["id"] = "evt_test_conflict"
    conflicting = client.post(
        "/api/stripe/webhook",
        content=b"{}",
        headers={"stripe-signature": "sig_test"},
    )

    assert first.status_code == 200
    assert replay.status_code == 200
    assert conflicting.status_code == 409


def test_stripe_checkout_failure_is_not_left_pending(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("COMPLYLENS_PAYMENT_MODE", "stripe")
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)

    response = client.post(
        "/api/orders",
        json={"email": "buyer@example.com", "product_id": "p2-playbook"},
    )

    assert response.status_code == 503
    order_files = list((tmp_path / "orders").glob("*.json"))
    assert len(order_files) == 1
    assert order_files[0].read_text(encoding="utf-8").find('"status": "checkout_failed"') >= 0
