"""프로파일을 법률·감사 보장이 아닌 데이터 정리 리포트로 렌더링한다."""
from __future__ import annotations

from html import escape

from .profiling import CsvProfile


def _number(value: float | None) -> str:
    return "-" if value is None else f"{value:g}"


def render_summary(profile: CsvProfile) -> str:
    rows = []
    for column in profile.columns.values():
        rows.append(
            "<tr>"
            f"<td>{escape(column.name)}</td>"
            f"<td>{column.non_empty_count}</td>"
            f"<td>{column.missing_count}</td>"
            f"<td>{column.unique_count}</td>"
            f"<td>{column.numeric_count}</td>"
            f"<td>{_number(column.numeric_min)}</td>"
            f"<td>{_number(column.numeric_max)}</td>"
            "</tr>"
        )
    return f"""<!doctype html>
<html lang="ko">
<meta charset="utf-8">
<title>데이터 정리 요약 리포트</title>
<style>
body {{ font-family: sans-serif; color: #172033; margin: 2rem; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #cbd5e1; padding: .45rem; text-align: left; }}
th {{ background: #eff6ff; }}
</style>
<h1>데이터 정리 요약 리포트</h1>
<p>파일: {escape(profile.source_name)}</p>
<p>행 수: {profile.row_count} · 중복 행: {profile.duplicate_rows}</p>
<table>
<thead><tr><th>열</th><th>값 있음</th><th>결측</th><th>고유값</th>
<th>숫자값</th><th>최솟값</th><th>최댓값</th></tr></thead>
<tbody>{"".join(rows)}</tbody>
</table>
<p>이 문서는 데이터 정리 결과이며 법률·세무·감사 의견이 아닙니다.</p>
</html>
"""
