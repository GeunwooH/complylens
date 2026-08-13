"""페이지뷰 통계 저장소 — 일 단위 파일, 경로별 집계."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_TRACKING_KEYS = {"source", "utm_source", "utm_medium", "utm_campaign", "utm_content"}
_MAX_DAILY_PATHS = 256
_MAX_DAILY_REFERRERS = 128
_MAX_VALUE_LENGTH = 200


def _clean_path(value: str) -> str:
    parts = urlsplit(value)
    query = urlencode(
        sorted(
            (key, item[:80])
            for key, item in parse_qsl(parts.query, keep_blank_values=False)
            if key in _TRACKING_KEYS
        )
    )
    return urlunsplit(("", "", parts.path or "/", query, ""))[:_MAX_VALUE_LENGTH]


def _clean_referrer(value: str) -> str:
    parts = urlsplit(value.strip())
    if not parts.scheme or not parts.netloc:
        return value.split("?", 1)[0][:_MAX_VALUE_LENGTH]
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path, "", "")
    )[:_MAX_VALUE_LENGTH]


class PVStore:
    def __init__(self, data_dir: Path) -> None:
        self._dir = Path(data_dir) / "stats"
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, day: str) -> Path:
        return self._dir / f"{day}.json"

    def record(self, path: str, referrer: str = "") -> None:
        day = datetime.now(UTC).date().isoformat()
        p = self._path(day)
        counts: dict[str, int] = {}
        referrers: dict[str, int] = {}
        if p.exists():
            stored = json.loads(p.read_text(encoding="utf-8"))
            if "counts" in stored:
                counts = stored["counts"]
                referrers = stored.get("referrers", {})
            else:
                counts = stored
        path_key = _clean_path(path)
        if path_key not in counts and len(counts) >= _MAX_DAILY_PATHS:
            path_key = "/__other__"
        counts[path_key] = counts.get(path_key, 0) + 1
        referrer_key = _clean_referrer(referrer) if referrer else ""
        if referrer_key:
            if referrer_key not in referrers and len(referrers) >= _MAX_DAILY_REFERRERS:
                referrer_key = "__other__"
            referrers[referrer_key] = referrers.get(referrer_key, 0) + 1
        p.write_text(
            json.dumps({"counts": counts, "referrers": referrers}),
            encoding="utf-8",
        )

    def summary(self) -> dict:
        total = 0
        by_path: dict[str, int] = {}
        by_day: dict[str, int] = {}
        by_referrer: dict[str, int] = {}
        for p in self._dir.glob("*.json"):
            day = p.stem
            stored = json.loads(p.read_text(encoding="utf-8"))
            if "counts" in stored:
                counts = stored["counts"]
                referrers = stored.get("referrers", {})
            else:
                counts = stored
                referrers = {}
            day_total = sum(counts.values())
            by_day[day] = day_total
            total += day_total
            for path, count in counts.items():
                by_path[path] = by_path.get(path, 0) + count
            for referrer, count in referrers.items():
                by_referrer[referrer] = by_referrer.get(referrer, 0) + count
        return {
            "total": total,
            "by_path": dict(sorted(by_path.items(), key=lambda kv: -kv[1])),
            "by_day": dict(sorted(by_day.items())),
            "by_referrer": dict(sorted(by_referrer.items(), key=lambda kv: -kv[1])),
        }
