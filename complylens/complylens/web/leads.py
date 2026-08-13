"""리드 캡처 저장소 — 문의 폼 제출 저장."""
from __future__ import annotations

import json
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

_ATTRIBUTION_KEYS = (
    "source",
    "product",
    "consent",
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_content",
    "quiz_result",
)


def _clean_attribution(value: object) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    cleaned: dict[str, str] = {}
    for key in _ATTRIBUTION_KEYS:
        raw = value.get(key)
        if isinstance(raw, str):
            item = raw.strip()
            if item:
                cleaned[key] = item[:80]
    return cleaned


class LeadStore:
    def __init__(self, data_dir: Path) -> None:
        self._dir = Path(data_dir) / "leads"
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, lead_id: str) -> Path:
        return self._dir / f"{lead_id}.json"

    def create(
        self,
        name: str,
        company: str,
        email: str,
        message: str,
        attribution: object = None,
    ) -> dict:
        lead_id = uuid.uuid4().hex[:12]
        lead = {
            "lead_id": lead_id,
            "name": name,
            "company": company,
            "email": email,
            "message": message,
            "status": "new",
            "created_at": datetime.now(UTC).isoformat(),
            "attribution": _clean_attribution(attribution),
        }
        self._path(lead_id).write_text(json.dumps(lead, indent=2), encoding="utf-8")
        return lead

    def get(self, lead_id: str) -> dict:
        path = self._path(lead_id)
        if not path.exists():
            raise KeyError(lead_id)
        return json.loads(path.read_text(encoding="utf-8"))
