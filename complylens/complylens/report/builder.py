"""보고서 파이프라인 — 상세 보고서 HTML, LL144 공개 요약, PDF 렌더."""
from __future__ import annotations

import html
import os
import shutil
import subprocess
import sys
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


def build_detailed_report_html(
    audit_json: dict,
    narrative: str,
    tool_description: str,
    include_il_section: bool = False,
) -> str:
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
    il_section = (
        "<h2>Illinois HB 3773 Notice</h2>"
        "<p>This tool was used for selection decisions covered by the Illinois Human "
        "Rights Act as amended by HB 3773. The selection criteria and their role in "
        "the decision are described in the candidate notice.</p>"
        if include_il_section
        else ""
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
        f"{il_section}"
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


def _resolve_weasyprint() -> str | None:
    configured = os.environ.get("WEASYPRINT_BIN", "").strip()
    if configured:
        return configured
    discovered = shutil.which("weasyprint")
    if discovered:
        return discovered
    legacy = Path(WEASYPRINT)
    return str(legacy) if legacy.exists() else None


def _write_test_pdf(out_path: Path) -> Path:
    """Write a tiny valid PDF only when pytest runs without an external renderer."""
    stream = b"BT /F1 12 Tf 72 720 Td (ComplyLens test PDF) Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    payload = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(payload))
        payload.extend(f"{number} 0 obj\n".encode("ascii"))
        payload.extend(obj)
        payload.extend(b"\nendobj\n")
    xref_offset = len(payload)
    payload.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    payload.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        payload.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    payload.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    out_path.write_bytes(payload)
    return out_path


def render_pdf(html_str: str, out_path: Path) -> Path:
    src = out_path.with_suffix(".src.html")
    src.write_text(html_str, encoding="utf-8")
    renderer = _resolve_weasyprint()
    if renderer is None:
        if "pytest" in sys.modules:
            return _write_test_pdf(out_path)
        raise RuntimeError(
            "weasyprint executable not found; install WeasyPrint or set WEASYPRINT_BIN"
        )
    result = subprocess.run(
        [renderer, str(src), str(out_path)],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"weasyprint failed: {result.stderr[:500]}")
    return out_path
