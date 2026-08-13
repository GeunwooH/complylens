#!/usr/bin/env python3
"""Audit sensitive LLM routing without making a provider network call."""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from complylens.llm.gateway import LLMGateway, Provider


@dataclass(frozen=True, slots=True)
class RoutingAudit:
    status: str
    sensitive_providers: tuple[str, ...]
    detail: str


def _llm_gateway() -> LLMGateway | None:
    """Build the routing gateway without importing the full FastAPI application."""
    if os.environ.get("COMPLYLENS_LLM_ENABLED") != "1":
        return None
    providers = [
        Provider("deepinfra", "https://api.deepinfra.com/v1", "DEEPINFRA_API_KEY", "deepseek-ai/DeepSeek-V4-Flash", "non_prc"),
        Provider("digitalocean", "https://inference.digitalocean.com/v1", "DIGITALOCEAN_API_KEY", "deepseek-v4-flash", "non_prc"),
        Provider("deepseek", "https://api.deepseek.com", "DEEPSEEK_API_KEY", "deepseek-v4-flash", "prc"),
    ]
    return LLMGateway(providers)


def audit_sensitive_routing() -> RoutingAudit:
    gateway = _llm_gateway()
    if gateway is None:
        return RoutingAudit("blocked", (), "LLM gateway is disabled")
    providers = gateway.configured_provider_names(sensitive=True)
    if not providers:
        return RoutingAudit("blocked", (), "no explicitly non-PRC provider is configured")
    return RoutingAudit("ready", providers, "sensitive routing is restricted to explicit non-PRC providers")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()
    result = audit_sensitive_routing()
    payload = {
        "status": result.status,
        "sensitive_providers": list(result.sensitive_providers),
        "detail": result.detail,
        "network_call_made": False,
        "api_keys_emitted": False,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"Sensitive LLM routing audit: {result.status}")
        print(f"Providers: {', '.join(result.sensitive_providers) or '(none)'}")
        print(result.detail)
    return 0 if result.status == "ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
