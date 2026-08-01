"""운영 플레이북 테스트 — 문서 4종 존재 + 클레임 참조."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_sales_pipeline_document() -> None:
    doc = (ROOT / "docs" / "ops" / "sales-pipeline.md").read_text(encoding="utf-8")
    for needle in ["SEO", "LL144 bias audit", "법무법인"]:
        assert needle in doc


def test_pricing_strategy_document() -> None:
    doc = (ROOT / "docs" / "ops" / "pricing-strategy.md").read_text(encoding="utf-8")
    for needle in ["$1,500", "$2,500", "88.6%", "C44"]:
        assert needle in doc


def test_sla_operations_document() -> None:
    doc = (ROOT / "docs" / "ops" / "sla-operations.md").read_text(encoding="utf-8")
    for needle in ["72", "DeepInfra", "페일오버", "36개월"]:
        assert needle in doc


def test_case_study_template_forbids_real_data() -> None:
    doc = (ROOT / "docs" / "ops" / "case-study-template.md").read_text(encoding="utf-8")
    assert "합성 데이터" in doc
    assert "실고객 데이터 사용 금지" in doc
