"""법적 준수 키트 — 계약/DPA/개인정보/독립성 문서 + 서명 게이트."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


class SignoffRequired(ValueError):
    """독립 감사인 서명 없이 납품 시도."""


class SignoffStore:
    def __init__(self, data_dir: Path) -> None:
        self._dir = Path(data_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, audit_id: str) -> Path:
        return self._dir / f"{audit_id}.signoff.json"

    def sign(self, audit_id: str, signer: str) -> None:
        record = {
            "audit_id": audit_id,
            "signer": signer,
            "signed_at": datetime.now(timezone.utc).isoformat(),
        }
        self._path(audit_id).write_text(json.dumps(record, indent=2), encoding="utf-8")

    def require_signoff(self, audit_id: str) -> str:
        path = self._path(audit_id)
        if not path.exists():
            raise SignoffRequired(f"no independent-auditor signoff for {audit_id}")
        return json.loads(path.read_text(encoding="utf-8"))["signer"]


def build_engagement_letter(client: str, tool: str, audit_date: str) -> str:
    return (
        f"ENGAGEMENT LETTER — {client}\n"
        f"Subject: Independent bias audit of {tool} under NYC Local Law 144.\n"
        f"Fee: $1,500 flat, payable in advance. Deliverable: bias audit report, "
        f"public summary, and candidate notice within 10 business days of data receipt.\n"
        f"The audit will be conducted by an independent auditor with no financial "
        f"interest in {client} or {tool}.\n"
        f"Audit date: {audit_date}\n"
    )


def build_dpa(client: str) -> str:
    return (
        f"DATA PROCESSING ADDENDUM — {client}\n"
        "1. no training of models on personal data: data is used only "
        "to produce the audit and is never used for model training.\n"
        "2. Retention: data is retained no longer than 36 months after delivery, "
        "then deleted.\n"
        "3. Deletion: upon written request or contract end, all copies are deleted "
        "within 30 days and deletion is certified.\n"
        "4. Processing location: all processing occurs in the United States.\n"
    )


def build_independence_confirmation(signer: str, tool: str) -> str:
    return (
        f"INDEPENDENCE CONFIRMATION — {signer}\n"
        f"I confirm I have no financial interest in the tool ({tool}), its vendor, "
        "or the employer, and no employment relationship with any of them, "
        "consistent with DCWP Final Rules (6 RCNY Subchapter T).\n"
    )


def build_privacy_notice(client: str) -> str:
    return (
        f"PRIVACY NOTICE — {client} bias audit service\n"
        "Candidate and employee data submitted for audit is processed solely to "
        "produce the required bias audit. Data is processed in the United States, "
        "is not used for AI training, and is deleted within 36 months.\n"
    )
