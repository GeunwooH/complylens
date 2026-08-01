"""보고서 파이프라인 — 상세 보고서 HTML, LL144 공개 요약, PDF 렌더."""
from __future__ import annotations

import html
import subprocess
from pathlib import Path

WEASYPRINT = "/opt/homebrew/bin/weasyprint"

_PUBLIC_SUMMARY_FIELDS = {
    "tool_description",
    "audit_date",
    "highest_selection_rate",
    "categories",
}


def _escape(value: object) -> str:
    return html.escape(str(value))


def build_detailed_report_html(audit_json: dict, narrative: str, tool_description: str) -> str:
    if not audit_json.get("categories"):
        raise ValueError("audit_json has no categories")
    rows = "".join(
        "<tr>"
        f"<td>{_escape(cat)}</td>"
        f"<td>{audit_json['categories'][cat]['selection_rate']:.4f}</td>"
        f"<td>{audit_json['categories'][cat]['impact_ratio']:.4f}</td>"
        f"<td>{'PASS' if audit_json['categories'][cat]['four_fifths_pass'] else 'FAIL'}</td>"
        "</tr>"
        for cat in audit_json["categories"]
    )
    return (
        "<html><head><meta charset='utf-8'><title>Bias Audit Report</title></head><body>"
        f"<h1>Bias Audit Report</h1>"
        f"<p><strong>Tool:</strong> {_escape(tool_description)}</p>"
        f"<p>{_escape(narrative)}</p>"
        "<table border='1'><tr><th>Category</th><th>Selection Rate</th>"
        "<th>Impact Ratio</th><th>Four-Fifths</th></tr>"
        f"{rows}</table>"
        f"<p><strong>Highest selection rate:</strong> {audit_json['highest_selection_rate']:.4f}</p>"
        "</body></html>"
    )


def build_public_summary_html(audit_json: dict, tool_description: str, audit_date: str) -> str:
    if not audit_json.get("categories"):
        raise ValueError("audit_json has no categories")
    if not tool_description or not audit_date:
        raise ValueError("tool_description and audit_date are required")
    rows = "".join(
        "<li>"
        f"{_escape(cat)}: selection rate {audit_json['categories'][cat]['selection_rate']:.4f}, "
        f"impact ratio {audit_json['categories'][cat]['impact_ratio']:.4f}"
        "</li>"
        for cat in audit_json["categories"]
    )
    return (
        "<html><head><meta charset='utf-8'><title>Bias Audit Public Summary</title></head><body>"
        f"<h1>Bias Audit Public Summary</h1>"
        f"<p><strong>Tool:</strong> {_escape(tool_description)}</p>"
        f"<p><strong>Audit date:</strong> {_escape(audit_date)}</p>"
        f"<p><strong>Highest selection rate:</strong> {audit_json['highest_selection_rate']:.4f}</p>"
        f"<ul>{rows}</ul>"
        "</body></html>"
    )


def build_notice_text(tool_name: str, audit_date: str) -> str:
    return (
        f"This position uses an automated employment decision tool ({tool_name}) "
        f"to screen candidates. A bias audit of this tool was completed on {audit_date}. "
        "You may request an alternative selection process."
    )


def render_pdf(html_str: str, out_path: Path) -> Path:
    src = out_path.with_suffix(".src.html")
    src.write_text(html_str, encoding="utf-8")
    result = subprocess.run(
        [WEASYPRINT, str(src), str(out_path)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"weasyprint failed: {result.stderr[:500]}")
    return out_path
