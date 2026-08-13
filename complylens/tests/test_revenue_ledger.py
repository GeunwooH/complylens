from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "revenue-ledger.py"


def write_ledger(path: Path, rows: list[dict[str, object]]) -> Path:
    path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )
    return path


def run_ledger(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--ledger", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )


def order(order_id: str, net_amount_krw: int, status: str = "paid") -> dict[str, object]:
    return {
        "order_id": order_id,
        "gross_amount_krw": 300_000,
        "net_amount_krw": net_amount_krw,
        "status": status,
        "channel": "kmong",
    }


def test_ledger_deduplicates_order_updates_and_requires_five_orders(
    tmp_path: Path,
) -> None:
    rows = [order("order-1", 235_000), order("order-1", 235_000, "delivered")]
    rows.extend(order(f"order-{index}", 235_000) for index in range(2, 6))

    result = run_ledger(write_ledger(tmp_path / "ledger.jsonl", rows))

    assert result.returncode == 0
    assert json.loads(result.stdout) == {
        "status": "target_met",
        "target_krw": 1_000_000,
        "net_paid_krw": 1_175_000,
        "remaining_krw": 0,
        "order_count": 5,
        "channels": {"kmong": 5},
    }


def test_ledger_rejects_negative_amount_and_invalid_status(tmp_path: Path) -> None:
    result = run_ledger(
        write_ledger(
            tmp_path / "invalid.jsonl",
            [order("bad", -1, "pending")],
        )
    )

    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["status"] == "blocked"
    assert payload["errors"] == ["line 1: net_amount_krw must be positive", "line 1: unsupported status"]
