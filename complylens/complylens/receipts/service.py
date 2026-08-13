"""영수증 파이프라인 — 이미지 → Gemini OCR → GPT 분류 → 장부 저장 → 카드 응답."""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
import uuid

from complylens.receipts.classify import ACCOUNT_CATEGORIES, CategoryClassifier, Classification
from complylens.receipts.ocr import GeminiOCRClient, ReceiptExtraction, to_price
from complylens.receipts.store import LedgerStore

_MIME_EXT = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/webp": "webp",
    "image/gif": "gif",
}


class ReceiptPipeline:
    """이미지 업로드 → OCR → 분류 → 장부 저장 / 카드 JSON 생성."""

    def __init__(
        self,
        data_dir: Path | str = "data",
        ocr: GeminiOCRClient | None = None,
        classifier: CategoryClassifier | None = None,
        store: LedgerStore | None = None,
        namespace: str = "default",
        images_dir: Path | str | None = None,
    ) -> None:
        """namespace(가게 코드)별 저장소로 파이프라인을 격리한다.

        images_dir이 주어지면 OCR 원본 이미지를 보관한다 (P0-G5 — 국세기본법
        제85조의3 증빙 보존 근거, 앱 카피는 '신고 준비용'으로 한정).
        """
        self.data_dir = Path(data_dir)
        self.namespace = namespace
        self.ocr = ocr if ocr is not None else GeminiOCRClient()
        self.classifier = classifier if classifier is not None else CategoryClassifier()
        self.store = store if store is not None else LedgerStore(self.data_dir, namespace=namespace)
        self.images_dir = Path(images_dir) if images_dir is not None else None

    def process(
        self,
        image_bytes: bytes,
        mime_type: str,
        *,
        image_sha256: str | None = None,
    ) -> dict[str, Any]:
        """이미지 1장 → 카드 응답 + 장부 저장.

        C1: 품목 합계 vs 총액 검증(needs_review/warnings) — OCR 경고와 병합.
        C2: 같은 가게의 이전 수정 기록(few-shot)으로 분류를 override한다.
        G2(멱등성): image_sha256이 주어지고 같은 해시의 최근 기록이 있으면
        OCR/분류를 다시 돌리지 않고 기존 기록으로 응답한다 — 재업로드 중복 차단.
        G5(원본 보관): images_dir이 설정돼 있으면 원본 이미지를 저장한다.
        """
        if image_sha256:
            existing = self.store.find_by_image_sha256(image_sha256)
            if existing is not None:
                return self._card_from_entry(existing)
        extraction = self.ocr.extract(image_bytes, mime_type)
        classification = self.classifier.classify(
            extraction.store, [item.name for item in extraction.items]
        )
        classification = self._apply_correction_rules(extraction, classification)
        needs_review, warnings = self._recheck_items(
            [
                {"name": item.name, "price": item.price}
                for item in extraction.items
            ],
            extraction.total,
        )
        needs_review = needs_review or bool(extraction.needs_review)
        warnings = list(dict.fromkeys([*extraction.warnings, *warnings]))
        entry = self._entry_from(extraction, classification, needs_review, warnings)
        if image_sha256:
            entry["image_sha256"] = image_sha256
        if self.images_dir is not None:
            # G5: save가 receipt_id를 확정하기 전에 원본을 보관한다
            # (image_path를 entry에 넣어 디스크 기록에도 반영되도록)
            entry.setdefault("receipt_id", uuid.uuid4().hex[:12])
            self._persist_image(entry, image_bytes, mime_type)
        saved = self.store.save(entry)
        return self._card(saved, extraction, classification)

    def _persist_image(self, entry: dict[str, Any], image_bytes: bytes, mime_type: str) -> None:
        """원본 영수증 이미지를 data/receipt-images/{store}/{receipt_id}.{ext}에 보관."""
        ext = _MIME_EXT.get((mime_type or "").split(";")[0].strip().lower(), "bin")
        rel = f"{self.namespace}/{entry['receipt_id']}.{ext}"
        path = self.images_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(image_bytes)
        entry["image_path"] = rel

    def _apply_correction_rules(
        self, extraction: Any, classification: Any
    ) -> Any:
        """같은 가게의 few-shot 수정: (store, 원분류) → 수정분류 매칭이면 override."""
        for sample in self.store.list_corrections():
            original = sample.get("original") or {}
            corrected = sample.get("corrected") or {}
            if (
                original.get("store") == extraction.store
                and original.get("category") == classification.category
                and corrected.get("category")
                and corrected["category"] != original.get("category")
            ):
                return Classification(
                    str(corrected["category"]), 1.0, "correction"
                )
        return classification

    @staticmethod
    def _entry_from(
        extraction: ReceiptExtraction, classification: Any, needs_review: bool, warnings: list[str]
    ) -> dict[str, Any]:
        unclassified = classification.category == "기타"
        return {
            "kind": "expense",
            "store": extraction.store or "",
            "date": extraction.date or "",
            "items": [
                {"name": item.name, "price": item.price} for item in extraction.items
            ],
            "total": extraction.total,
            "vat": extraction.vat,
            "payment": extraction.payment,
            "category": classification.category,
            "category_confidence": classification.confidence,
            "category_source": classification.source,
            "unclassified": unclassified,
            "needs_review": needs_review,
            "warnings": warnings,
            "ocr_model": extraction.model,
        }

    @staticmethod
    def _card(entry: dict[str, Any], extraction: ReceiptExtraction, classification: Any) -> dict[str, Any]:
        return {
            "receipt_id": entry["receipt_id"],
            "store": entry["store"],
            "date": entry["date"],
            "items": entry["items"],
            "total": entry["total"],
            "vat": entry["vat"],
            "payment": entry["payment"],
            "category": classification.category,
            "category_confidence": classification.confidence,
            "category_source": classification.source,
            "confidence": "low" if entry["needs_review"] else "high",
            "needs_review": entry["needs_review"],
            "warnings": entry["warnings"],
            "ocr_model": extraction.model,
            "created_at": datetime.now(UTC).isoformat(),
        }

    @staticmethod
    def _card_from_entry(entry: dict[str, Any]) -> dict[str, Any]:
        """저장된 기록에서 카드 응답을 재구성한다 (멱등성 중복 응답용)."""
        return {
            "receipt_id": entry["receipt_id"],
            "store": entry.get("store", ""),
            "date": entry.get("date", ""),
            "items": entry.get("items", []),
            "total": entry.get("total", 0),
            "vat": entry.get("vat", 0),
            "payment": entry.get("payment", ""),
            "category": entry.get("category", "기타"),
            "category_confidence": entry.get("category_confidence", 0.0),
            "category_source": entry.get("category_source", "rule"),
            "confidence": "low" if entry.get("needs_review") else "high",
            "needs_review": bool(entry.get("needs_review")),
            "warnings": entry.get("warnings", []),
            "ocr_model": entry.get("ocr_model", ""),
            "created_at": entry.get("created_at", ""),
            "duplicate": True,
        }

    # -- 수정 파이프라인 -------------------------------------------------------
    def correct(self, receipt_id: str, changes: dict[str, Any]) -> dict[str, Any]:
        """사용자 수정값을 장부에 반영하고 few-shot 재학습 샘플을 저장한다."""
        original = self.store.get(receipt_id)

        corrected_changes = self._normalize_changes(changes)

        if "category" in corrected_changes:
            category = str(corrected_changes["category"]).strip()
            if category not in ACCOUNT_CATEGORIES:
                raise ValueError(f"unknown category: {category}")
            corrected_changes["category"] = category
            corrected_changes["category_confidence"] = 1.0
            corrected_changes["category_source"] = "manual"
            corrected_changes["unclassified"] = category == "기타"

        if "items" in corrected_changes or "total" in corrected_changes:
            items = corrected_changes.get("items", original.get("items", []))
            total = corrected_changes.get("total", original.get("total"))
            needs_review, warnings = self._recheck_items(items, total)
            corrected_changes["needs_review"] = needs_review
            corrected_changes["warnings"] = warnings

        updated = self.store.update(receipt_id, corrected_changes)
        self.store.record_correction(receipt_id, original, updated)
        return updated

    @staticmethod
    def _normalize_changes(changes: dict[str, Any]) -> dict[str, Any]:
        """수정 페이로드의 금액/품목/문자열 필드를 정규화한다."""
        normalized: dict[str, Any] = {}
        for key in ("store", "date", "payment"):
            if key in changes:
                value = changes[key]
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(f"{key} must be a non-empty string")
                normalized[key] = value.strip()
        if "total" in changes:
            value = to_price(changes["total"])
            if value is None:
                raise ValueError("total must be a valid amount")
            normalized["total"] = value
        if "vat" in changes:
            value = to_price(changes["vat"])
            if value is None:
                raise ValueError("vat must be a valid amount")
            normalized["vat"] = value
        if "category" in changes:
            normalized["category"] = str(changes["category"]).strip()
        if "items" in changes:
            raw_items = changes["items"]
            if not isinstance(raw_items, list) or not raw_items:
                raise ValueError("items must be a non-empty list")
            items: list[dict[str, Any]] = []
            for item in raw_items:
                if not isinstance(item, dict):
                    raise ValueError("each item must be an object")  # noqa: TRY004 - 400 응답 매핑용
                name = item.get("name")
                price = to_price(item.get("price"))
                if not isinstance(name, str) or not name.strip() or price is None:
                    raise ValueError("each item needs name and a valid price")
                items.append({"name": name.strip(), "price": price})
            normalized["items"] = items
        return normalized

    @staticmethod
    def _recheck_items(items: Any, total: Any) -> tuple[bool, list[str]]:
        if not isinstance(items, list) or not items:
            return True, ["품목이 비어 있어 검토가 필요합니다"]
        prices = [to_price(item.get("price")) for item in items if isinstance(item, dict)]
        if any(price is None for price in prices):
            return True, ["품목 가격을 읽지 못한 항목이 있습니다"]
        item_sum = sum(prices)  # type: ignore[arg-type]
        if abs(float(item_sum) - float(total or 0)) > max(2.0, float(item_sum) * 0.02):
            return True, [f"물품 합계({item_sum:g})와 총액({total:g})이 일치하지 않습니다"]
        return False, []