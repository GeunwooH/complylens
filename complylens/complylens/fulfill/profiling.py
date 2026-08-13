"""CSV 입력을 사람이 검토할 수 있는 데이터 프로파일로 변환한다."""
from __future__ import annotations

import csv
import math
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class ColumnProfile:
    name: str
    non_empty_count: int
    missing_count: int
    unique_count: int
    numeric_count: int
    numeric_min: float | None
    numeric_max: float | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class CsvProfile:
    source_name: str
    row_count: int
    duplicate_rows: int
    columns: dict[str, ColumnProfile]

    def to_dict(self) -> dict[str, object]:
        return {
            "source_name": self.source_name,
            "row_count": self.row_count,
            "duplicate_rows": self.duplicate_rows,
            "columns": {
                name: column.to_dict() for name, column in self.columns.items()
            },
        }


def _as_number(value: str) -> float | None:
    try:
        number = float(value.replace(",", ""))
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def profile_csv(path: Path) -> CsvProfile:
    """Read a UTF-8 CSV and return deterministic, JSON-safe statistics."""
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        if not fields or any(not field.strip() for field in fields):
            raise ValueError("CSV must have non-empty column names")
        if len(set(fields)) != len(fields):
            raise ValueError("CSV column names must be unique")

        values = {field: set[str]() for field in fields}
        missing = dict.fromkeys(fields, 0)
        numeric_values: dict[str, list[float]] = {field: [] for field in fields}
        row_count = 0
        unique_rows: set[tuple[str, ...]] = set()

        for row in reader:
            row_count += 1
            normalized = tuple((row.get(field) or "").strip() for field in fields)
            unique_rows.add(normalized)
            for field, value in zip(fields, normalized):
                if not value:
                    missing[field] += 1
                    continue
                values[field].add(value)
                number = _as_number(value)
                if number is not None:
                    numeric_values[field].append(number)

    columns = {
        field: ColumnProfile(
            name=field,
            non_empty_count=row_count - missing[field],
            missing_count=missing[field],
            unique_count=len(values[field]),
            numeric_count=len(numeric_values[field]),
            numeric_min=min(numeric_values[field], default=None),
            numeric_max=max(numeric_values[field], default=None),
        )
        for field in fields
    }
    return CsvProfile(
        source_name=path.name,
        row_count=row_count,
        duplicate_rows=row_count - len(unique_rows),
        columns=columns,
    )
