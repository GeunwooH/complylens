"""다중관할 확장 테스트 — IL 섹션 토글(비활성 기본), 요건 문서."""
from __future__ import annotations

from pathlib import Path

from complylens.report.builder import build_detailed_report_html

ROOT = Path(__file__).resolve().parents[2]

AUDIT = {
    "categories": {
        "male": {"selection_rate": 1.0, "impact_ratio": 1.0, "four_fifths_pass": True},
        "female": {"selection_rate": 0.2, "impact_ratio": 0.2, "four_fifths_pass": False},
    },
    "highest_selection_rate": 1.0,
    "four_fifths_violations": ["female"],
    "score_based_rates": None,
}


def test_il_section_off_by_default() -> None:
    out = build_detailed_report_html(AUDIT, "narrative", "ToolX")
    assert "Illinois HB 3773" not in out


def test_il_section_included_when_enabled() -> None:
    out = build_detailed_report_html(AUDIT, "narrative", "ToolX", include_il_section=True)
    assert "Illinois HB 3773 Notice" in out


def test_il_checklist_document_exists_with_sources() -> None:
    doc = (ROOT / "docs" / "compliance" / "illinois-hb3773.md").read_text(encoding="utf-8")
    for needle in ["2026-01-01", "notice", "nondiscrimination", "hinshawlaw.com"]:
        assert needle in doc


def test_ca_admt_document_exists_with_sources() -> None:
    doc = (ROOT / "docs" / "compliance" / "california-admt.md").read_text(encoding="utf-8")
    for needle in ["2027-01-01", "risk assessment"]:
        assert needle in doc
