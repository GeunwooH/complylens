#!/usr/bin/env python3
"""Validate local prerequisites for a Stripe test-mode staging run."""
from __future__ import annotations

import argparse
import json
import os
from collections.abc import Mapping
from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class Check:
    name: str
    ok: bool
    detail: str


def evaluate_environment(env: Mapping[str, str]) -> tuple[bool, list[Check]]:
    checks = [
        Check(
            "payment_mode",
            env.get("COMPLYLENS_PAYMENT_MODE", "").strip().lower() == "stripe",
            "stripe mode enabled" if env.get("COMPLYLENS_PAYMENT_MODE", "").strip().lower() == "stripe" else "set COMPLYLENS_PAYMENT_MODE=stripe",
        ),
        Check(
            "stripe_secret",
            env.get("STRIPE_SECRET_KEY", "").startswith("sk_test_"),
            "Stripe test key configured"
            if env.get("STRIPE_SECRET_KEY", "").startswith("sk_test_")
            else "set a Stripe test key",
        ),
        Check(
            "webhook_secret",
            env.get("STRIPE_WEBHOOK_SECRET", "").startswith("whsec_"),
            "webhook secret configured"
            if env.get("STRIPE_WEBHOOK_SECRET", "").startswith("whsec_")
            else "set a Stripe webhook secret",
        ),
        Check(
            "public_url",
            env.get("COMPLYLENS_PUBLIC_URL", "").startswith("https://"),
            "HTTPS public URL configured"
            if env.get("COMPLYLENS_PUBLIC_URL", "").startswith("https://")
            else "set COMPLYLENS_PUBLIC_URL to an https:// URL",
        ),
        Check(
            "api_key",
            bool(env.get("COMPLYLENS_API_KEY", "").strip()),
            "API key configured" if env.get("COMPLYLENS_API_KEY", "").strip() else "set COMPLYLENS_API_KEY",
        ),
    ]
    return all(check.ok for check in checks), checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()
    ready, checks = evaluate_environment(os.environ)
    payload = {"status": "ready" if ready else "blocked", "checks": [asdict(check) for check in checks]}
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"Stripe staging preflight: {payload['status']}")
        for check in checks:
            print(f"[{'OK' if check.ok else 'BLOCKED'}] {check.name}: {check.detail}")
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
