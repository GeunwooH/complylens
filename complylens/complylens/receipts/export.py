"""장부 내보내기 — CSV(UTF-8 BOM) / Excel(xlsx, 의존성 없음)."""
from __future__ import annotations

import csv
import io
import zipfile
from typing import Any, Final
from xml.sax.saxutils import escape

_HEADERS: Final[tuple[str, ...]] = (
    "일자",
    "거래처",
    "품목",
    "계정과목",
    "구분",
    "금액",
    "부가세",
    "결제수단",
    "상태",
)


def _items_summary(entry: dict[str, Any]) -> str:
    items = entry.get("items") or []
    names = [str(item.get("name", "")) for item in items if isinstance(item, dict) and item.get("name")]
    if not names:
        return ""
    if len(names) <= 3:
        return " / ".join(names)
    return f"{' / '.join(names[:3])} 외 {len(names) - 3}건"


def _status(entry: dict[str, Any]) -> str:
    flags: list[str] = []
    if entry.get("needs_review"):
        flags.append("검토필요")
    if entry.get("category") == "기타" or entry.get("unclassified"):
        flags.append("미분류")
    return " / ".join(flags) if flags else "정상"


def _row(entry: dict[str, Any]) -> list[str]:
    amount = entry.get("total", entry.get("amount", ""))
    return [
        str(entry.get("date", "")),
        str(entry.get("store", "")),
        _items_summary(entry) or str(entry.get("note", "")),
        str(entry.get("category") or "기타"),
        "매출" if entry.get("kind") == "income" else "지출",
        str(amount),
        str(entry.get("vat") or ""),
        str(entry.get("payment") or ""),
        _status(entry),
    ]


def entries_to_csv(entries: list[dict[str, Any]]) -> bytes:
    """CSV (UTF-8 BOM) — Excel에서 한글 안 깨짐."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(_HEADERS)
    for entry in entries:
        writer.writerow(_row(entry))
    return ("\ufeff" + buffer.getvalue()).encode("utf-8")


# ---------------------------------------------------------------------------
# 최소 xlsx — openpyxl 없이 inlineStr 셀로 구성한 단일 시트 패키지
# ---------------------------------------------------------------------------

_XML_DECL = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'


def _cell(ref: str, text: str) -> str:
    return (
        f'<c r="{ref}" t="inlineStr"><is>'
        f"<t xml:space=\"preserve\">{escape(text)}</t>"
        "</is></c>"
    )


def _column_letter(index: int) -> str:
    return chr(ord("A") + index - 1)


def _sheet_xml(entries: list[dict[str, Any]]) -> str:
    rows: list[str] = []
    header_cells = "".join(
        _cell(f"{_column_letter(index)}1", header)
        for index, header in enumerate(_HEADERS, start=1)
    )
    rows.append(f'<row r="1">{header_cells}</row>')
    for row_index, entry in enumerate(entries, start=2):
        cells = "".join(
            _cell(f"{_column_letter(col_index)}{row_index}", value)
            for col_index, value in enumerate(_row(entry), start=1)
        )
        rows.append(f'<row r="{row_index}">{cells}</row>')
    return (
        f"{_XML_DECL}\n"
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{''.join(rows)}</sheetData></worksheet>"
    )


_CONTENT_TYPES = f"""{_XML_DECL}
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>"""

_ROOT_RELS = f"""{_XML_DECL}
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""

_WORKBOOK_XML = f"""{_XML_DECL}
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets><sheet name="장부" sheetId="1" r:id="rId1"/></sheets>
</workbook>"""

_WORKBOOK_RELS = f"""{_XML_DECL}
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>"""


def entries_to_xlsx(entries: list[dict[str, Any]]) -> bytes:
    """엑셀(.xlsx) 바이트 — 표준 최소 스프레드시트 패키지 (외부 라이브러리 불필요)."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _CONTENT_TYPES)
        archive.writestr("_rels/.rels", _ROOT_RELS)
        archive.writestr("xl/workbook.xml", _WORKBOOK_XML)
        archive.writestr("xl/_rels/workbook.xml.rels", _WORKBOOK_RELS)
        archive.writestr("xl/worksheets/sheet1.xml", _sheet_xml(entries))
    return buffer.getvalue()