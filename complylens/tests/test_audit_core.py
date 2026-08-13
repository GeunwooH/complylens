"""LL144/AEDT 편향감사 통계 엔진 known-answer 테스트.

참조: DCWP Final Rules (6 RCNY Subchapter T) — selection rate,
impact ratio, four-fifths rule, median-threshold scoring.
"""
from __future__ import annotations

import pandas as pd
import pytest

from complylens.audit.core import (
    MissingCategoryError,
    compute_impact_ratios,
    compute_score_based_rates,
    compute_selection_rates,
    evaluate_audit,
    four_fifths_rule,
)


def _df(rows: list[tuple[str, str, int]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["candidate_id", "category", "selected"])


# ── Known-answer 1: 균등 데이터 (1:1 비율) ──────────────────────────
def test_known_answer_equal_selection_rates() -> None:
    df = _df(
        [
            (f"m{i}", "male", 1 if i % 2 == 0 else 0) for i in range(100)
        ]
        + [(f"f{i}", "female", 1 if i % 2 == 0 else 0) for i in range(100)]
    )
    rates = compute_selection_rates(df, category_col="category", selection_col="selected")
    assert rates["male"] == pytest.approx(0.5)
    assert rates["female"] == pytest.approx(0.5)


def test_known_answer_equal_impact_ratio_and_four_fifths() -> None:
    df = _df(
        [(f"m{i}", "male", 1 if i % 2 == 0 else 0) for i in range(100)]
        + [(f"f{i}", "female", 1 if i % 2 == 0 else 0) for i in range(100)]
    )
    rates = compute_selection_rates(df, "category", "selected")
    ratios = compute_impact_ratios(rates)
    assert ratios["male"] == pytest.approx(1.0)
    assert ratios["female"] == pytest.approx(1.0)
    assert four_fifths_rule(ratios) == set()


# ── Known-answer 2: 명백한 불리 (four-fifths 위반) ────────────────────
def test_known_answer_adverse_impact_ratio() -> None:
    df = _df(
        [(f"m{i}", "male", 1) for i in range(100)]  # 100% 선택
        + [(f"f{i}", "female", 1 if i < 40 else 0) for i in range(100)]  # 40%
    )
    rates = compute_selection_rates(df, "category", "selected")
    ratios = compute_impact_ratios(rates)
    # 최대 선택률(1.0) 대비 female 0.4 → four-fifths(0.8) 미만 = 위반
    assert ratios["female"] == pytest.approx(0.4)
    assert four_fifths_rule(ratios) == {"female"}


# ── Known-answer 3: 사라진 카테고리 → 명시적 에러 ────────────────────
def test_missing_category_raises() -> None:
    df = _df([("m1", "male", 1), ("m2", "male", 0)])
    with pytest.raises(MissingCategoryError):
        compute_selection_rates(df, "category", "selected", required_categories=["male", "female"])


# ── Known-answer 4: 교차범주 (sex × ethnicity) ───────────────────────
def test_known_answer_intersectional() -> None:
    rows = []
    for i in range(100):
        rows.append((f"a{i}", "male_asian", 1))
        rows.append((f"b{i}", "female_asian", 1 if i < 30 else 0))  # 30%
        rows.append((f"c{i}", "male_white", 1 if i < 50 else 0))  # 50%
    rates = compute_selection_rates(pd.DataFrame(rows, columns=["candidate_id", "category", "selected"]), "category", "selected")
    ratios = compute_impact_ratios(rates)
    assert ratios["female_asian"] == pytest.approx(0.3)  # 0.3 / 1.0
    assert four_fifths_rule(ratios) == {"female_asian", "male_white"}


# ── Known-answer 5: 연속 스코어 (median-threshold scoring rate) ──────
def test_known_answer_score_based_median_threshold() -> None:
    df = pd.DataFrame(
        [
            ("m1", "male", 90.0),
            ("m2", "male", 10.0),
            ("f1", "female", 60.0),
            ("f2", "female", 40.0),
        ],
        columns=["candidate_id", "category", "score"],
    )
    result = compute_score_based_rates(df, "category", "score")
    # 전체 스코어 [90, 10, 60, 40] → median = (40+60)/2 = 50
    # threshold(50) 초과: male 1/2 (90), female 1/2 (60) → 둘 다 0.5
    assert result["male"] == pytest.approx(0.5)
    assert result["female"] == pytest.approx(0.5)


def test_score_based_impact_ratio_and_four_fifths_are_reported() -> None:
    df = pd.DataFrame(
        [
            ("m1", "male", 1, 100.0),
            ("m2", "male", 1, 90.0),
            ("f1", "female", 1, 60.0),
            ("f2", "female", 1, 50.0),
        ],
        columns=["candidate_id", "category", "selected", "score"],
    )

    result = evaluate_audit(
        df,
        category_col="category",
        selection_col="selected",
        score_col="score",
    )

    assert result["score_based_rates"] == {"male": 1.0, "female": 0.0}
    assert result["score_based_impact_ratios"] == {"male": 1.0, "female": 0.0}
    assert result["score_based_four_fifths_violations"] == ["female"]


# ── End-to-end: evaluate_audit가 결정적 JSON 스키마 반환 ─────────────
def test_evaluate_audit_deterministic_schema() -> None:
    df = _df(
        [(f"m{i}", "male", 1 if i % 2 == 0 else 0) for i in range(100)]
        + [(f"f{i}", "female", 1 if i % 2 == 0 else 0) for i in range(100)]
    )
    r1 = evaluate_audit(df, category_col="category", selection_col="selected")
    r2 = evaluate_audit(df, category_col="category", selection_col="selected")
    assert r1 == r2  # 결정적
    assert isinstance(r1, dict)
    assert "categories" in r1 and "highest_selection_rate" in r1
    assert set(r1["categories"].keys()) == {"male", "female"}


def test_empty_input_raises() -> None:
    with pytest.raises(ValueError):
        evaluate_audit(_df([]), category_col="category", selection_col="selected")
