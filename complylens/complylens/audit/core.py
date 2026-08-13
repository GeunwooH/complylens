"""LL144 편향감사 통계 엔진 — selection rate, impact ratio, four-fifths rule."""
from __future__ import annotations

from typing import Any

import pandas as pd


class MissingCategoryError(ValueError):
    """필수 보호범주가 입력 데이터에 존재하지 않을 때."""


def compute_selection_rates(
    df: pd.DataFrame,
    category_col: str,
    selection_col: str,
    required_categories: list[str] | None = None,
) -> dict[str, float]:
    if df.empty:
        raise ValueError("input data is empty")
    if required_categories:
        missing = [c for c in required_categories if c not in set(df[category_col])]
        if missing:
            raise MissingCategoryError(f"missing required categories: {missing}")
    grouped = df.groupby(category_col)[selection_col].mean()
    return {str(cat): float(rate) for cat, rate in grouped.items()}


def compute_impact_ratios(rates: dict[str, float]) -> dict[str, float]:
    if not rates:
        return {}
    highest = max(rates.values())
    if highest == 0:
        return {cat: 0.0 for cat in rates}
    return {cat: rate / highest for cat, rate in rates.items()}


def four_fifths_rule(ratios: dict[str, float]) -> set[str]:
    return {cat for cat, ratio in ratios.items() if ratio < 0.8}


def compute_score_based_rates(df: pd.DataFrame, category_col: str, score_col: str) -> dict[str, float]:
    if df.empty:
        raise ValueError("input data is empty")
    threshold = float(df[score_col].median())
    above = df[df[score_col] > threshold]
    counts = df.groupby(category_col).size()
    above_counts = above.groupby(category_col).size()
    return {
        str(cat): float(above_counts.get(cat, 0) / counts[cat]) if counts[cat] > 0 else 0.0
        for cat in counts.index
    }


def evaluate_audit(
    df: pd.DataFrame,
    category_col: str,
    selection_col: str,
    score_col: str | None = None,
    required_categories: list[str] | None = None,
) -> dict[str, Any]:
    rates = compute_selection_rates(df, category_col, selection_col, required_categories)
    ratios = compute_impact_ratios(rates)
    violations = four_fifths_rule(ratios)
    score_based = (
        compute_score_based_rates(df, category_col, score_col) if score_col else None
    )
    score_based_ratios = compute_impact_ratios(score_based) if score_based is not None else None
    score_based_violations = (
        sorted(four_fifths_rule(score_based_ratios))
        if score_based_ratios is not None
        else None
    )
    return {
        "categories": {
            cat: {
                "selection_rate": rates[cat],
                "impact_ratio": ratios[cat],
                "four_fifths_pass": cat not in violations,
            }
            for cat in rates
        },
        "highest_selection_rate": max(rates.values()) if rates else 0.0,
        "four_fifths_violations": sorted(violations),
        "score_based_rates": score_based,
        "score_based_impact_ratios": score_based_ratios,
        "score_based_four_fifths_violations": score_based_violations,
    }
