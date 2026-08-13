from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "llm-routing-audit.py"


def test_routing_audit_fails_closed_when_gateway_disabled() -> None:
    env = {key: value for key, value in os.environ.items() if not key.startswith("COMPLYLENS_LLM")}
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--json"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload == {
        "status": "blocked",
        "sensitive_providers": [],
        "detail": "LLM gateway is disabled",
        "network_call_made": False,
        "api_keys_emitted": False,
    }


def test_routing_audit_reports_non_prc_configuration_without_keys() -> None:
    env = {
        "COMPLYLENS_LLM_ENABLED": "1",
        "DEEPINFRA_API_KEY": "secret-deepinfra",
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
    assert payload["sensitive_providers"] == ["deepinfra"]
    assert "secret-deepinfra" not in result.stdout
    assert payload["network_call_made"] is False
