"""영수증/장부 스키마 — pydantic v2 모델 (receipt-ledger-saas W1-1)."""
from __future__ import annotations

import datetime as _dt
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class AccountCategory(str, Enum):
    """장부 계정과목."""

    FOOD = "식대"
    SUPPLIES = "소모품"
    RENT = "임대료"
    MATERIALS = "재료비"
    TRANSPORT = "교통비"
    UTILITIES = "관리비"
    OTHER = "기타"


ACCOUNT_CATEGORIES: tuple[str, ...] = tuple(category.value for category in AccountCategory)


class ReceiptItem(BaseModel):
    """영수증 품목 한 줄."""

    name: str = Field(min_length=1)
    price: int | float = Field(gt=0)


class ReceiptCard(BaseModel):
    """OCR 추출 결과 카드 (store/date/items/total/vat/payment)."""

    store: str = Field(min_length=1)
    date: _dt.date
    items: list[ReceiptItem] = Field(default_factory=list)
    total: int | float = Field(gt=0)
    vat: int | float | None = None
    payment: str | None = None


class LedgerEntry(BaseModel):
    """장부 거래 한 건."""

    receipt_id: str | None = None
    category: AccountCategory
    amount: int | float = Field(gt=0)
    date: _dt.date | None = None
    note: str = ""
    corrected: bool = False
    kind: Literal["income", "expense"] = "expense"