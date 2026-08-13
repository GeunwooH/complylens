from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_daily_report_handles_quoted_order_filename(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    orders_dir = data_dir / "orders"
    (data_dir / "leads").mkdir(parents=True)
    orders_dir.mkdir(parents=True)
    (orders_dir / "quote'order.json").write_text(
        json.dumps(
            {
                "order_id": "quoted-order",
                "email": "founder@example.com",
                "product_name": "SOC2 Under $5k Startup Playbook",
                "status": "pending",
                "created_at": "2026-08-02T07:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    curl = fake_bin / "curl"
    curl.write_text(
        """#!/bin/sh
case "$*" in
  *blockstream.info*) printf '%s\\n' '{"chain_stats":{"funded_txo_sum":0,"tx_count":0}}' ;;
  *-w*) printf '200' ;;
  *) printf '200' ;;
esac
""",
        encoding="utf-8",
    )
    curl.chmod(0o755)

    env = os.environ | {
        "COMPLYLENS_DATA_DIR": str(data_dir),
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
    }
    result = subprocess.run(
        ["bash", str(ROOT / "scripts" / "daily-report.sh")],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert result.returncode == 0
    assert "quoted-order" in result.stdout
