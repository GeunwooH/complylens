from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "deployment-health.sh"


def _run_health(tmp_path: Path, scenario: str, cloudflared: bool = True) -> subprocess.CompletedProcess[str]:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    (fake_bin / "curl").write_text(
        """#!/bin/sh
case "$*" in
  *html.npopo.com/pricing.html*) printf '%s' "${FAKE_PRICING:-200}" ;;
  *html.npopo.com/kmong-csv-profile.html*) printf '%s' "${FAKE_OFFER:-200}" ;;
  *html.npopo.com/*) printf '%s' "${FAKE_HOME:-200}" ;;
  *127.0.0.1:8000/*) printf '%s' "${FAKE_ORIGIN:-200}" ;;
  *) exit 2 ;;
esac
""",
        encoding="utf-8",
    )
    (fake_bin / "curl").chmod(0o755)
    (fake_bin / "pgrep").write_text(
        """#!/bin/sh
if [ "${FAKE_CLOUDFLARED:-yes}" = "yes" ]; then
  exit 0
fi
exit 1
""",
        encoding="utf-8",
    )
    (fake_bin / "pgrep").chmod(0o755)

    values = {
        "FAKE_HOME": "200",
        "FAKE_PRICING": "200",
        "FAKE_OFFER": "200",
        "FAKE_ORIGIN": "200",
        "FAKE_CLOUDFLARED": "yes" if cloudflared else "no",
    }
    if scenario == "origin-down":
        values["FAKE_ORIGIN"] = "ERR"
    elif scenario == "edge-down":
        values["FAKE_HOME"] = "502"
        values["FAKE_PRICING"] = "502"
    elif scenario == "pricing-down":
        values["FAKE_PRICING"] = "503"
    elif scenario == "offer-down":
        values["FAKE_OFFER"] = "404"
    elif scenario != "healthy":
        raise ValueError(f"unknown scenario: {scenario}")

    env = os.environ | values | {"PATH": f"{fake_bin}:{os.environ['PATH']}"}
    return subprocess.run(
        ["bash", str(SCRIPT)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_deployment_health_reports_healthy(tmp_path: Path) -> None:
    result = _run_health(tmp_path, "healthy")

    assert result.returncode == 0
    assert "deployment_health=HEALTHY" in result.stdout
    assert "public_home=200" in result.stdout
    assert "public_pricing=200" in result.stdout
    assert "public_offer=200" in result.stdout
    assert "local_origin=200" in result.stdout
    assert "cloudflared=present" in result.stdout


def test_deployment_health_classifies_origin_down(tmp_path: Path) -> None:
    result = _run_health(tmp_path, "origin-down", cloudflared=False)

    assert result.returncode != 0
    assert "deployment_health=ORIGIN_DOWN" in result.stdout
    assert "local_origin=ERR" in result.stdout


def test_deployment_health_classifies_edge_down(tmp_path: Path) -> None:
    result = _run_health(tmp_path, "edge-down")

    assert result.returncode != 0
    assert "deployment_health=TUNNEL_OR_EDGE_DOWN" in result.stdout
    assert "public_home=502" in result.stdout
    assert "public_pricing=502" in result.stdout


def test_deployment_health_classifies_pricing_failure(tmp_path: Path) -> None:
    result = _run_health(tmp_path, "pricing-down")

    assert result.returncode != 0
    assert "deployment_health=TUNNEL_OR_EDGE_DOWN" in result.stdout
    assert "public_pricing=503" in result.stdout


def test_deployment_health_classifies_offer_failure(tmp_path: Path) -> None:
    result = _run_health(tmp_path, "offer-down")

    assert result.returncode != 0
    assert "deployment_health=TUNNEL_OR_EDGE_DOWN" in result.stdout
    assert "public_offer=404" in result.stdout


def test_deployment_health_classifies_missing_cloudflared(tmp_path: Path) -> None:
    result = _run_health(tmp_path, "healthy", cloudflared=False)

    assert result.returncode != 0
    assert "deployment_health=CLOUDFLARED_NOT_RUNNING" in result.stdout


def test_deployment_health_help() -> None:
    result = subprocess.run(
        ["bash", str(SCRIPT), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Read-only" in result.stdout
