"""장부 저장소 — JSON 파일 기반 (complylens/web/leads.py LeadStore 패턴).

- data_dir/ledger/: 장부 거래/영수증 카드 JSON (uuid hex id, mkdir parents)
- data_dir/corrections/: 사용자 수정 few-shot 재학습 샘플 (W1-3)
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
import secrets
import uuid
from pathlib import Path

from complylens.receipts.schema import AccountCategory, LedgerEntry

DateLike = _dt.date | str | None

_VALID_NAMESPACE = re.compile(r"^[A-Za-z0-9]{1,16}$")
_VALID_PIN = re.compile(r"^[A-Za-z0-9]{4,12}$")

_PIN_MAX_FAILURES = 5
_PIN_LOCK_MINUTES = 10


class LedgerStore:
    """LeadStore 패턴 그대로: uuid hex id, mkdir parents, `_path(id)`, create/get/list.

    상태는 항상 디스크에서 읽으므로 인스턴스를 새로 만들어도 최신 데이터가 보인다.
    """

    def __init__(self, data_dir: Path, namespace: str = "default") -> None:
        """장부 저장소 — namespace(가게 코드)별로 데이터를 격리한다.

        namespace는 1~16자 영숫자만 허용(경로 주입 방지).
        ``data_dir/ledger/{namespace}/`` 와 ``data_dir/corrections/{namespace}/`` 를 사용한다.
        """
        if not _VALID_NAMESPACE.fullmatch(namespace):
            raise ValueError(
                f"invalid namespace: {namespace!r} — 1~16자 영숫자만 허용합니다"
            )
        self._namespace = namespace
        self._dir = Path(data_dir) / "ledger" / namespace
        self._dir.mkdir(parents=True, exist_ok=True)
        self._corrections_dir = Path(data_dir) / "corrections" / namespace
        self._corrections_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, entry_id: str) -> Path:
        return self._dir / f"{entry_id}.json"

    def _correction_path(self, receipt_id: str) -> Path:
        return self._corrections_dir / f"{receipt_id}.json"

    def create(
        self,
        date: DateLike = None,
        category: AccountCategory | str | None = None,
        amount: float | None = None,
        note: str = "",
        corrected: bool = False,
        receipt_id: str | None = None,
        kind: str = "expense",
    ) -> dict:
        """장부 거래를 저장한다. 필수 필드 누락/형식 오류는 pydantic ValidationError."""
        entry = LedgerEntry(
            receipt_id=receipt_id or uuid.uuid4().hex[:12],
            category=category,
            amount=amount,
            date=date,
            note=note,
            corrected=corrected,
            kind=kind,
        )
        payload = entry.model_dump(mode="json")
        self._write(payload)
        return payload

    def _write(self, entry: dict) -> None:
        self._path(entry["receipt_id"]).write_text(
            json.dumps(entry, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def get(self, entry_id: str) -> dict:
        path = self._path(entry_id)
        if not path.exists():
            raise KeyError(f"ledger entry not found: {entry_id}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload

    def list(self) -> list[dict]:
        """디스크에서 모든 거래를 읽는다. (날짜 오름차순, receipt_id 오름차순)"""
        entries = []
        for path in sorted(self._dir.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            entries.append(payload)
        entries.sort(key=lambda e: (e.get("date", ""), e.get("receipt_id", "")))
        return entries

    # -- 가게 코드 PIN 잠금 (B1: 코드 유출/무차별 대입 방지) -----------------

    def _meta_path(self) -> Path:
        return self._dir / "meta.json"

    def has_pin(self) -> bool:
        return self._meta_path().exists()

    def set_pin(self, pin: str) -> None:
        """가게 코드에 PIN(4~12자 영숫자)을 설정/변경한다."""
        if not _VALID_PIN.fullmatch(pin):
            raise ValueError("PIN은 4~12자 영숫자여야 합니다")
        salt = secrets.token_hex(16)
        pin_hash = hashlib.pbkdf2_hmac(
            "sha256", pin.encode(), salt.encode(), 100_000
        ).hex()
        meta = {
            "pin_hash": pin_hash,
            "salt": salt,
            "failed_attempts": 0,
            "locked_until": None,
        }
        self._meta_path().write_text(
            json.dumps(meta, ensure_ascii=False), encoding="utf-8"
        )

    def verify_pin(self, pin: str) -> tuple[bool, str]:
        """PIN 검증 — (통과여부, 사유): ok | pin_not_set | wrong | locked.

        연속 5회 실패 시 10분 잠금 (무차별 대입 방지).
        """
        if not self.has_pin():
            return False, "pin_not_set"
        meta = json.loads(self._meta_path().read_text(encoding="utf-8"))

        locked_until = meta.get("locked_until")
        if locked_until:
            until = _dt.datetime.fromisoformat(locked_until)
            if _dt.datetime.now(_dt.UTC) < until:
                return False, "locked"
            meta["failed_attempts"] = 0
            meta["locked_until"] = None

        salt = str(meta.get("salt", ""))
        expected = str(meta.get("pin_hash", ""))
        actual = hashlib.pbkdf2_hmac(
            "sha256", pin.encode(), salt.encode(), 100_000
        ).hex()
        if secrets.compare_digest(actual, expected):
            meta["failed_attempts"] = 0
            self._write_meta(meta)
            return True, "ok"

        meta["failed_attempts"] = int(meta.get("failed_attempts", 0)) + 1
        if meta["failed_attempts"] >= _PIN_MAX_FAILURES:
            meta["locked_until"] = (
                _dt.datetime.now(_dt.UTC) + _dt.timedelta(minutes=_PIN_LOCK_MINUTES)
            ).isoformat()
        self._write_meta(meta)
        return False, "locked" if meta.get("locked_until") else "wrong"

    def _write_meta(self, meta: dict) -> None:
        self._meta_path().write_text(
            json.dumps(meta, ensure_ascii=False), encoding="utf-8"
        )

    # -- 영수증 카드/거래 공용 저장 ---------------------------------------------

    def save(self, entry: dict) -> dict:
        """영수증 파이프라인 출력(전체 카드 dict)을 영수증 id로 저장한다."""
        record = dict(entry)
        record.setdefault("receipt_id", uuid.uuid4().hex[:12])
        record.setdefault("created_at", _dt.datetime.now(_dt.UTC).isoformat())
        self._write(record)
        return record

    def update(self, entry_id: str, changes: dict) -> dict:
        """영수증 카드를 수정값으로 갱신한다 (few-shot 샘플은 record_correction으로)."""
        record = self.get(entry_id)
        record.update(changes)
        record["updated_at"] = _dt.datetime.now(_dt.UTC).isoformat()
        self._write(record)
        return record

    def delete(self, entry_id: str) -> None:
        """장부 거래 삭제 (P2)."""
        path = self._path(entry_id)
        if not path.exists():
            raise KeyError(f"ledger entry not found: {entry_id}")
        path.unlink()

    def find_by_image_sha256(self, sha256: str, within_hours: int = 24) -> dict | None:
        """같은 이미지 해시의 최근 기록을 찾는다 (업로드 멱등성 P0-G2)."""
        cutoff = (
            _dt.datetime.now(_dt.UTC) - _dt.timedelta(hours=within_hours)
        ).isoformat()
        for entry in self.list_entries():
            if entry.get("image_sha256") == sha256 and entry.get("created_at", "") >= cutoff:
                return entry
        return None

    def count_uploads_in_month(self, month: str) -> int:
        """created_at이 해당 월인 OCR 업로드 수 (P0-G4 월 한도 집계).

        영수증 날짜(date)가 아니라 업로드 시각(created_at) 기준으로 센다 —
        과거 영수증을 올려도 이번 달 한도에 카운트되어 우회할 수 없다.
        """
        prefix = month + "-"
        return sum(
            1
            for e in self.list_entries()
            if e.get("ocr_model") and (e.get("created_at") or "").startswith(prefix)
        )

    def record_correction(
        self, receipt_id: str, original: dict, corrected: dict
    ) -> None:
        """사용자의 1클릭 수정을 few-shot 재학습 샘플로 저장한다."""
        sample = {
            "receipt_id": receipt_id,
            "original": original,
            "corrected": corrected,
            "corrected_at": _dt.datetime.now(_dt.UTC).isoformat(),
        }
        self._correction_path(receipt_id).write_text(
            json.dumps(sample, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def get_correction(self, receipt_id: str) -> dict | None:
        path = self._correction_path(receipt_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list_corrections(self) -> list[dict]:
        """저장된 모든 few-shot 수정 샘플 (가게 코드별 격리된 디렉토리)."""
        samples = []
        for path in sorted(self._corrections_dir.glob("*.json")):
            samples.append(json.loads(path.read_text(encoding="utf-8")))
        return samples

    # -- 집계 (W1-4 월간 리포트) --------------------------------------

    def list_entries(self, month: str | None = None) -> list[dict]:
        """월(YYYY-MM) 필터된 거래 목록."""
        rows = self.list()
        if month:
            rows = [row for row in rows if str(row.get("date", "")).startswith(month)]
        return rows

    def monthly_report(self, month: str | None = None) -> dict:
        """월간 리포트: 매출(revenue) / 지출(expense) / 손익(profit) / 미분류.

        P1 확장: category_breakdown(카테고리별 지출) + top_stores(상위 지출처 3).
        """
        rows = self.list_entries(month)
        revenue = 0.0
        expense = 0.0
        unclassified = 0
        needs_review = 0
        category_totals: dict[str, float] = {}
        store_totals: dict[str, float] = {}
        for row in rows:
            amount = float(row.get("total", 0) or row.get("amount", 0) or 0)
            if row.get("kind") == "income":
                revenue += amount
            else:
                expense += amount
                category = row.get("category")
                if category == AccountCategory.OTHER.value or row.get("unclassified"):
                    unclassified += 1
                cat = str(category or "기타")
                category_totals[cat] = category_totals.get(cat, 0.0) + amount
                store_name = str(row.get("store") or "기타")
                store_totals[store_name] = store_totals.get(store_name, 0.0) + amount
            if row.get("needs_review"):
                needs_review += 1
        top = sorted(store_totals.items(), key=lambda kv: -kv[1])[:3]
        return {
            "month": month,
            "entry_count": len(rows),
            "revenue": revenue,
            "expense": expense,
            "profit": revenue - expense,
            "unclassified_count": unclassified,
            "needs_review_count": needs_review,
            "category_breakdown": dict(
                sorted(category_totals.items(), key=lambda kv: -kv[1])
            ),
            "top_stores": [(name, round(amount, 2)) for name, amount in top],
        }