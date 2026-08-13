"""CSV 풀필먼트 프로파일과 한국어 요약 리포트 테스트."""
from __future__ import annotations

import json
from pathlib import Path

from complylens.fulfill.profiling import profile_csv
from complylens.fulfill.summary_ko import render_summary


def test_profile_csv_reports_missing_numeric_and_duplicate_rows(tmp_path: Path) -> None:
    source = tmp_path / "settlements.csv"
    source.write_text(
        "seller,amount,channel\n"
        "A,100,store\n"
        "B,,delivery\n"
        "A,100,store\n",
        encoding="utf-8",
    )

    profile = profile_csv(source).to_dict()

    assert profile["row_count"] == 3
    assert profile["duplicate_rows"] == 1
    assert profile["columns"]["amount"]["missing_count"] == 1
    assert profile["columns"]["amount"]["numeric_min"] == 100.0
    assert profile["columns"]["amount"]["numeric_max"] == 100.0


def test_summary_escapes_input_and_is_json_serializable(tmp_path: Path) -> None:
    source = tmp_path / "unsafe.csv"
    source.write_text("name<script>,value\nx&y,1\n", encoding="utf-8")

    profile = profile_csv(source)
    summary = render_summary(profile)

    assert "<script>" not in summary
    assert "name&lt;script&gt;" in summary
    json.dumps(profile.to_dict(), ensure_ascii=False)
