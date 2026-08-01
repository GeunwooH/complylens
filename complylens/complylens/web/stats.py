"""페이지뷰 통계 저장소 — 일 단위 파일, 경로별 집계."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


class PVStore:
    def __init__(self, data_dir: Path) -> None:
        self._dir = Path(data_dir) / "stats"
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, day: str) -> Path:
        return self._dir / f"{day}.json"

    def record(self, path: str) -> None:
        day = datetime.now(UTC).date().isoformat()
        p = self._path(day)
        counts: dict[str, int] = {}
        if p.exists():
            counts = json.loads(p.read_text(encoding="utf-8"))
        counts[path] = counts.get(path, 0) + 1
        p.write_text(json.dumps(counts), encoding="utf-8")

    def summary(self) -> dict:
        total = 0
        by_path: dict[str, int] = {}
        by_day: dict[str, int] = {}
        for p in self._dir.glob("*.json"):
            day = p.stem
            counts = json.loads(p.read_text(encoding="utf-8"))
            day_total = sum(counts.values())
            by_day[day] = day_total
            total += day_total
            for path, count in counts.items():
                by_path[path] = by_path.get(path, 0) + count
        return {
            "total": total,
            "by_path": dict(sorted(by_path.items(), key=lambda kv: -kv[1])),
            "by_day": dict(sorted(by_day.items())),
        }
