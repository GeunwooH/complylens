"""주문/결제 테스트 — 제품 주문, txid 검증, 납품 게이트."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from complylens.web.app import app

API_KEY = "test-key"

PRODUCTS = {
    "p1-analysis": {"name": "LL144 Data Analysis Report", "price_btc": 0.0045, "price_usd": 299},
    "p2-playbook": {"name": "LL144 Compliance Playbook", "price_btc": 0.00075, "price_usd": 49},
    "p3-custom": {"name": "Custom Research & Document Automation", "price_btc": 0.003, "price_usd": 199},
}


@pytest.fixture()
def client(tmp_path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("COMPLYLENS_API_KEY", API_KEY)
    monkeypatch.setenv("COMPLYLENS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("COMPLYLENS_LLM_ENABLED", "0")
    monkeypatch.setenv("BTC_ADDRESS", "1C1mjuJ1ox3YgxT6Jq7FA6YjrjXb319nr7")
    monkeypatch.setenv("ETH_ADDRESS", "0xB8b9D6086ddeDC5CD2A27d88cF7FD2A6BeBcD2B2")
    return TestClient(app)


def test_create_order_returns_wallet_addresses(client: TestClient) -> None:
    resp = client.post("/api/orders", json={"email": "buyer@example.com", "product_id": "p2-playbook"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["order_id"]
    assert body["amount_btc"] == 0.00075
    assert body["btc_address"].startswith("1") or body["btc_address"].startswith("3")
    assert body["eth_address"].startswith("0x")
    assert body["status"] == "pending"


def test_unknown_product_rejected(client: TestClient) -> None:
    resp = client.post("/api/orders", json={"email": "x@y.com", "product_id": "nope"})
    assert resp.status_code == 400


def test_download_blocked_until_confirmed(client: TestClient) -> None:
    resp = client.post("/api/orders", json={"email": "buyer@example.com", "product_id": "p2-playbook"})
    order_id = resp.json()["order_id"]
    dl = client.get(f"/api/orders/{order_id}/download")
    assert dl.status_code == 403


def test_confirm_with_valid_txid_grants_download(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    resp = client.post("/api/orders", json={"email": "buyer@example.com", "product_id": "p2-playbook"})
    order = resp.json()

    def fake_verify(txid: str, expected_address: str, expected_sat: int) -> bool:
        assert expected_address == order["btc_address"]
        return True

    monkeypatch.setattr("complylens.web.app.verify_btc_payment", fake_verify)
    confirm = client.post(
        f"/api/orders/{order['order_id']}/confirm",
        json={"txid": "abc123"},
    )
    assert confirm.status_code == 200
    assert confirm.json()["status"] == "confirmed"
    dl = client.get(f"/api/orders/{order['order_id']}/download")
    assert dl.status_code == 200
    assert "Compliance Playbook" in dl.text


def test_confirm_with_invalid_txid_rejected(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    resp = client.post("/api/orders", json={"email": "buyer@example.com", "product_id": "p2-playbook"})
    order = resp.json()
    monkeypatch.setattr("complylens.web.app.verify_btc_payment", lambda *a: False)
    confirm = client.post(
        f"/api/orders/{order['order_id']}/confirm", json={"txid": "bogus"}
    )
    assert confirm.status_code == 402


def test_confirm_idempotent(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    resp = client.post("/api/orders", json={"email": "buyer@example.com", "product_id": "p2-playbook"})
    order = resp.json()
    monkeypatch.setattr("complylens.web.app.verify_btc_payment", lambda *a: True)
    client.post(f"/api/orders/{order['order_id']}/confirm", json={"txid": "abc"})
    again = client.post(f"/api/orders/{order['order_id']}/confirm", json={"txid": "abc"})
    assert again.status_code == 200
    assert again.json()["status"] == "confirmed"
