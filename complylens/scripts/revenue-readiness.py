#!/usr/bin/env python3
"""Validate a revenue offer manifest without external writes."""
from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path

TARGET_KRW = 1_000_000
SELLS_VIA = {"kmong", "stripe", "invoice"}


def _text(payload: Mapping[str, object], key: str, errors: list[str]) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(key)
        return ""
    return value.strip()


def _positive_int(payload: Mapping[str, object], key: str, errors: list[str]) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        errors.append(key)
        return 0
    return value


def validate_manifest(payload: object) -> dict[str, object]:
    if not isinstance(payload, Mapping):
        return {"status": "blocked", "errors": ["manifest"]}

    errors: list[str] = []
    offer_id = _text(payload, "offer_id", errors)
    _text(payload, "title", errors)
    price_krw = _positive_int(payload, "price_krw", errors)
    target_krw = _positive_int(payload, "target_krw", errors)
    unit_count_target = _positive_int(payload, "unit_count_target", errors)
    _text(payload, "deliverable", errors)
    _text(payload, "input_policy", errors)
    sells_via = _text(payload, "sells_via", errors)
    cta_path = _text(payload, "cta_path", errors)
    proof_paths = payload.get("proof_paths")
    approval_required = payload.get("approval_required")

    if target_krw != TARGET_KRW and "target_krw" not in errors:
        errors.append("target_krw")
    if unit_count_target and (
        not price_krw or price_krw * unit_count_target < TARGET_KRW
    ):
        errors.append("unit_count_target")
    if sells_via and sells_via not in SELLS_VIA:
        errors.append("sells_via")
    if cta_path and not cta_path.startswith("/"):
        errors.append("cta_path")
    if (
        not isinstance(proof_paths, list)
        or not proof_paths
        or any(not isinstance(path, str) or not path.strip() for path in proof_paths)
    ):
        errors.append("proof_paths")
    if not isinstance(approval_required, bool):
        errors.append("approval_required")

    if errors:
        return {"status": "blocked", "errors": sorted(set(errors))}
    return {
        "status": "ready",
        "offer_id": offer_id,
        "price_krw": price_krw,
        "target_krw": target_krw,
        "unit_count_target": unit_count_target,
        "gross_target_krw": price_krw * unit_count_target,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args()
    try:
        payload = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        result = {"status": "blocked", "errors": ["manifest"]}
    else:
        result = validate_manifest(payload)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == "ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
