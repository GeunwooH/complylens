from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "stripe-staging-preflight.py"


def test_preflight_blocks_without_user_owned_stripe_configuration() -> None:
    env = {key: value for key, value in os.environ.items() if not key.startswith("STRIPE_")}
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--json"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["status"] == "blocked"
    assert "sk_test_" not in result.stdout
    assert "whsec_" not in result.stdout


def test_preflight_is_ready_for_complete_test_mode_configuration() -> None:
    env = {
        "COMPLYLENS_PAYMENT_MODE": "stripe",
        "STRIPE_SECRET_KEY": "sk_test_redacted",
        "STRIPE_WEBHOOK_SECRET": "whsec_redacted",
        "COMPLYLENS_PUBLIC_URL": "https://staging.example",
        "COMPLYLENS_API_KEY": "local-test-key",
    }

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--json"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "ready"
    assert "redacted" not in result.stdout
