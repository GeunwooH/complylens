"""법적 준수 키트 테스트 — 문서 4종, 독립성 서명 게이트."""
from __future__ import annotations

from pathlib import Path

import pytest

from complylens.legal.kit import (
    SignoffRequired,
    SignoffStore,
    build_dpa,
    build_engagement_letter,
    build_independence_confirmation,
    build_privacy_notice,
)


def test_engagement_letter_has_statutory_clauses() -> None:
    text = build_engagement_letter("Acme Corp", "ToolX", "2026-08-01")
    for clause in ["bias audit", "independent", "$1,500", "10 business days"]:
        assert clause in text


def test_dpa_has_no_training_and_retention_clauses() -> None:
    text = build_dpa("Acme Corp")
    assert "no training" in text
    assert "retention" in text
    assert "deletion" in text


def test_independence_confirmation_declares_no_interest() -> None:
    text = build_independence_confirmation("Jane Auditor", "ToolX")
    assert "no financial interest" in text
    assert "Jane Auditor" in text


def test_privacy_notice_declares_processing_location() -> None:
    text = build_privacy_notice("Acme Corp")
    assert "United States" in text


def test_delivery_blocked_without_signoff(tmp_path: Path) -> None:
    store = SignoffStore(tmp_path)
    with pytest.raises(SignoffRequired):
        store.require_signoff("audit-1")


def test_delivery_allowed_after_signoff(tmp_path: Path) -> None:
    store = SignoffStore(tmp_path)
    store.sign("audit-1", "Jane Auditor")
    assert store.require_signoff("audit-1") == "Jane Auditor"


def test_resigning_updates_signer(tmp_path: Path) -> None:
    store = SignoffStore(tmp_path)
    store.sign("audit-1", "Jane Auditor")
    store.sign("audit-1", "John Reviewer")
    assert store.require_signoff("audit-1") == "John Reviewer"
