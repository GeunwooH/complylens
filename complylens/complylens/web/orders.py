"""주문 관리 + 크립토 결제 검증 + 납품 게이트."""
from __future__ import annotations

import json
import os
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

PRODUCTS = {
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
}

_BTC_TO_SAT = 100_000_000


class OrderStore:
    def __init__(self, data_dir: Path) -> None:
        self._dir = Path(data_dir) / "orders"
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, order_id: str) -> Path:
        return self._dir / f"{order_id}.json"

    def create(self, email: str, product_id: str) -> dict:
        product = PRODUCTS[product_id]
        order = {
            "order_id": __import__("uuid").uuid4().hex[:12],
            "email": email,
            "product_id": product_id,
            "product_name": product["name"],
            "amount_btc": product["price_btc"],
            "amount_sat": int(product["price_btc"] * _BTC_TO_SAT),
            "btc_address": os.environ.get("BTC_ADDRESS", ""),
            "status": "pending",
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._path(order["order_id"]).write_text(json.dumps(order, indent=2), encoding="utf-8")
        return order

    def get(self, order_id: str) -> dict:
        path = self._path(order_id)
        if not path.exists():
            raise KeyError(order_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def confirm(self, order_id: str, txid: str) -> dict:
        order = self.get(order_id)
        order["status"] = "confirmed"
        order["txid"] = txid
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
