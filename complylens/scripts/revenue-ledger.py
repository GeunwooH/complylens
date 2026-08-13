#!/usr/bin/env python3
"""Summarize paid revenue events without contacting external services."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import TypedDict

TARGET_KRW = 1_000_000
COUNTED_STATUSES = {"paid", "delivered", "completed"}


class RevenueEvent(TypedDict):
    order_id: str
    gross_amount_krw: int
    net_amount_krw: int
    status: str
    channel: str


def _positive_int(row: Mapping[str, object], key: str, errors: list[str], line: int) -> int:
    value = row.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        errors.append(f"line {line}: {key} must be positive")
        return 0
    return value


def _text(row: Mapping[str, object], key: str, errors: list[str], line: int) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"line {line}: {key} must be non-empty")
        return ""
    return value.strip()


def _read_events(path: Path) -> tuple[dict[str, RevenueEvent], list[str]]:
    events: dict[str, RevenueEvent] = {}
    errors: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return {}, ["ledger: unreadable file"]

    for line_number, raw_line in enumerate(lines, start=1):
        if not raw_line.strip():
            continue
        try:
            value = json.loads(raw_line)
        except json.JSONDecodeError:
            errors.append(f"line {line_number}: invalid JSON")
            continue
        if not isinstance(value, Mapping):
            errors.append(f"line {line_number}: event must be an object")
            continue

        order_id = _text(value, "order_id", errors, line_number)
        gross_amount = _positive_int(value, "gross_amount_krw", errors, line_number)
        net_amount = _positive_int(value, "net_amount_krw", errors, line_number)
        status = _text(value, "status", errors, line_number)
        channel = _text(value, "channel", errors, line_number)
        if status and status not in COUNTED_STATUSES:
            errors.append(f"line {line_number}: unsupported status")
        if errors and any(error.startswith(f"line {line_number}:") for error in errors):
            continue

        event: RevenueEvent = {
            "order_id": order_id,
            "gross_amount_krw": gross_amount,
            "net_amount_krw": net_amount,
            "status": status,
            "channel": channel,
        }
        previous = events.get(order_id)
        if previous and (
            previous["gross_amount_krw"] != gross_amount
            or previous["net_amount_krw"] != net_amount
            or previous["channel"] != channel
        ):
            errors.append(f"line {line_number}: conflicting order amounts or channel")
            continue
        events[order_id] = event
    return events, errors


def summarize(path: Path, target_krw: int = TARGET_KRW) -> dict[str, object]:
    events, errors = _read_events(path)
    if errors:
        return {"status": "blocked", "errors": errors}

    paid = [event for event in events.values() if event["status"] in COUNTED_STATUSES]
    net_paid = sum(event["net_amount_krw"] for event in paid)
    channels = Counter(event["channel"] for event in paid)
    return {
        "status": "target_met" if net_paid >= target_krw else "in_progress",
        "target_krw": target_krw,
        "net_paid_krw": net_paid,
        "remaining_krw": max(0, target_krw - net_paid),
        "order_count": len(paid),
        "channels": dict(sorted(channels.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--target", type=int, default=TARGET_KRW)
    args = parser.parse_args()
    result = summarize(args.ledger, args.target)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] != "blocked" else 2


if __name__ == "__main__":
    raise SystemExit(main())
