"""영수증 → OCR → 계정과목 분류 → 장부 저장 파이프라인 (receipt-ledger-saas Wave 1).

모듈:
- schema.py      — pydantic v2 모델 (AccountCategory/LedgerEntry/ReceiptCard)
- ocr.py         — Gemini OCR 추출·결정적 필드 검증 (flash-lite → 2.5-flash 에스컬레이션)
- classify.py    — GPT 분류 + 결정적 규칙 폴백
- store.py       — 장부/수정(재학습 샘플) JSON 저장소 (LeadStore 패턴)
- banktransfer.py— 무통장 주문 상태머신 (billing.OrderStore 패턴)
- export.py      — CSV(xlsx) 내보내기
- service.py     — 업로드→OCR→분류→저장 파이프라인 + 수정 재학습
"""
from __future__ import annotations

from complylens.receipts.banktransfer import (
    BANK_ACCOUNT_GUIDANCE,
    BANK_TRANSFER_PRODUCTS,
    BankTransferOrder,
    BankTransferOrderStore,
    InvalidTransition,
)
from complylens.receipts.classify import (
    ACCOUNT_CATEGORIES,
    CategoryClassifier,
    Classification,
    classify_items,
)
from complylens.receipts.export import entries_to_csv, entries_to_xlsx
from complylens.receipts.ocr import (
    GeminiOCRClient,
    OCRUnavailableError,
    ReceiptExtraction,
)
from complylens.receipts.schema import (
    AccountCategory,
    LedgerEntry,
    ReceiptCard,
    ReceiptItem,
)
from complylens.receipts.service import ReceiptPipeline
from complylens.receipts.store import LedgerStore

__all__ = [
    "ACCOUNT_CATEGORIES",
    "BANK_ACCOUNT_GUIDANCE",
    "BANK_TRANSFER_PRODUCTS",
    "AccountCategory",
    "BankTransferOrder",
    "BankTransferOrderStore",
    "CategoryClassifier",
    "Classification",
    "GeminiOCRClient",
    "InvalidTransition",
    "LedgerEntry",
    "LedgerStore",
    "OCRUnavailableError",
    "ReceiptCard",
    "ReceiptExtraction",
    "ReceiptItem",
    "ReceiptPipeline",
    "classify_items",
    "entries_to_csv",
    "entries_to_xlsx",
]