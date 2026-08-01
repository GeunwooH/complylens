"""보고서 파이프라인 테스트 — 결정성, 공개 요약 스키마, PDF 렌더."""
from __future__ import annotations

from pathlib import Path

import pytest

from complylens.report.builder import (
    build_detailed_report_html,
    build_notice_text,
    build_public_summary_html,
    render_pdf,
)

AUDIT = {
    "categories": {
        "male": {"selection_rate": 1.0, "impact_ratio": 1.0, "four_fifths_pass": True},
        "female": {"selection_rate": 0.2, "impact_ratio": 0.2, "four_fifths_pass": False},
    },
    "highest_selection_rate": 1.0,
    "four_fifths_violations": ["female"],
    "score_based_rates": None,
}


def test_detailed_report_is_deterministic() -> None:
    a = build_detailed_report_html(AUDIT, "narrative", "ToolX")
    b = build_detailed_report_html(AUDIT, "narrative", "ToolX")
    assert a == b


def test_detailed_report_injects_exact_numbers() -> None:
    out = build_detailed_report_html(AUDIT, "narrative", "ToolX")
    assert "0.2000" in out
    assert "1.0000" in out
    assert "FAIL" in out and "PASS" in out


def test_public_summary_has_required_fields() -> None:
    out = build_public_summary_html(AUDIT, "ToolX", "2026-08-01")
    for field in ["Bias Audit Public Summary", "ToolX", "2026-08-01", "0.2000", "1.0000"]:
        assert field in out


def test_public_summary_rejects_missing_fields() -> None:
    with pytest.raises(ValueError):
        build_public_summary_html(AUDIT, "", "2026-08-01")
    with pytest.raises(ValueError):
        build_public_summary_html({"categories": {}}, "ToolX", "2026-08-01")


def test_notice_contains_statutory_elements() -> None:
    text = build_notice_text("ToolX", "2026-08-01")
    assert "automated employment decision tool" in text
    assert "ToolX" in text and "2026-08-01" in text
    assert "alternative selection process" in text


def test_render_pdf_produces_valid_pdf(tmp_path: Path) -> None:
    out = render_pdf(build_detailed_report_html(AUDIT, "narrative", "ToolX"), tmp_path / "report.pdf")
    assert out.exists() and out.stat().st_size > 100
    assert out.read_bytes()[:4] == b"%PDF"
