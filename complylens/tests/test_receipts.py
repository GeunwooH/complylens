"""무통장 주문 상태 머신 + 장부/분류 테스트 (receipt-ledger-saas W1-1·W1-6)."""
from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from complylens.receipts import (
    BankTransferOrder,
    InvalidTransition,
    LedgerStore,
    classify_items,
)


@pytest.fixture()
def ledger(tmp_path: Path) -> LedgerStore:
    return LedgerStore(tmp_path)


@pytest.fixture()
def orders(tmp_path: Path) -> BankTransferOrder:
    return BankTransferOrder(tmp_path)


# ── LedgerStore ──────────────────────────────────────────────────────────────


def test_ledger_create_get(ledger: LedgerStore) -> None:
    entry = ledger.create("2025-07-15", "식대", 7000)
    assert entry["category"] == "식대"
    assert entry["date"] == "2025-07-15"
    assert entry["amount"] == 7000
    assert entry["corrected"] is False
    assert ledger.get(entry["receipt_id"]) == entry


def test_ledger_create_accepts_enum_category(ledger: LedgerStore) -> None:
    entry = ledger.create("2025-07-15", "소모품", 3000, note="휴지")
    assert entry["category"] == "소모품"
    assert entry["note"] == "휴지"


def test_ledger_create_missing_fields_raises_validation_error(ledger: LedgerStore) -> None:
    with pytest.raises(ValidationError):
        ledger.create()  # category/amount/date 누락
    with pytest.raises(ValidationError):
        ledger.create("2025-07-15", "식대", "not-an-amount")


def test_ledger_stale_state_new_instance_sees_entries(tmp_path: Path) -> None:
    first = LedgerStore(tmp_path)
    first.create("2025-07-15", "식대", 7000, note="설렁탕")
    again = LedgerStore(tmp_path)
    entries = again.list()
    assert len(entries) == 1
    assert entries[0]["category"] == "식대"
    entry_id = entries[0]["receipt_id"]
    assert again.get(entry_id)["amount"] == 7000
    # 그리고 다시 만들어도 누적된다
    again.create("2025-07-16", "교통비", 4500)
    assert len(list(LedgerStore(tmp_path).list())) == 2


def test_ledger_get_missing_raises_key_error(ledger: LedgerStore) -> None:
    with pytest.raises(KeyError):
        ledger.get("missing-id")


# ── classify_items ───────────────────────────────────────────────────────────


def test_classify_items_keyword_mapping() -> None:
    items = [
        {"name": "설렁탕", "price": 12000},
        {"name": "김밥", "price": 3500},
        {"name": "휴지", "price": 9800},
        {"name": "세제", "price": 5200},
        {"name": "월세", "price": 350000},
        {"name": "식자재", "price": 22000},
        {"name": "택시", "price": 8700},
        {"name": "전기요금", "price": 30000},
        {"name": "프린터토너", "price": 45000},
    ]
    entries = classify_items(items)
    categories = {entry.note: entry.category.value for entry in entries}
    assert categories == {
        "설렁탕": "식대",
        "김밥": "식대",
        "휴지": "소모품",
        "세제": "소모품",
        "월세": "임대료",
        "식자재": "재료비",
        "택시": "교통비",
        "전기요금": "관리비",
        "프린터토너": "기타",
    }


def test_classify_items_category_map_override() -> None:
    entries = classify_items(
        [{"name": "프린터토너", "price": 45000}],
        category_map={"프린터토너": "소모품"},
    )
    assert entries[0].category.value == "소모품"


def test_classify_items_malformed_item_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        classify_items([{"name": "설렁탕"}])  # price 누락


# ── BankTransferOrder ────────────────────────────────────────────────────────


def test_bank_transfer_create_default_awaiting_payment(orders: BankTransferOrder) -> None:
    order = orders.create("9,900원")
    assert order["status"] == "awaiting_payment"
    assert order["amount_krw"] == 9900
    account = order["bank_account"]
    assert {"bank", "holder", "account_number"} <= set(account)
    assert orders.get(order["id"])["status"] == "awaiting_payment"


def test_bank_transfer_legal_transitions(orders: BankTransferOrder) -> None:
    order = orders.create("9,900원")
    order_id = order["id"]
    orders.transition(order_id, "confirmed")
    assert orders.get(order_id)["status"] == "confirmed"
    orders.transition(order_id, "completed")
    assert orders.get(order_id)["status"] == "completed"


def test_bank_transfer_created_pasture_flow(orders: BankTransferOrder) -> None:
    order = orders.create("19,000원", status="created")
    assert order["status"] == "created"
    orders.transition(order["id"], "awaiting_payment")
    assert orders.get(order["id"])["status"] == "awaiting_payment"
    orders.transition(order["id"], "confirmed")
    orders.transition(order["id"], "completed")


def test_bank_transfer_illegal_transitions_raise(orders: BankTransferOrder) -> None:
    order = orders.create("9,900원")
    order_id = order["id"]
    # awaiting_payment → completed 는 불법 (confirmed를 건너뜀)
    with pytest.raises(InvalidTransition):
        orders.transition(order_id, "completed")
    assert orders.get(order_id)["status"] == "awaiting_payment"
    # confirmed 이후 이전 상태로 되돌아가기 불법
    orders.transition(order_id, "confirmed")
    with pytest.raises(InvalidTransition):
        orders.transition(order_id, "awaiting_payment")
    orders.transition(order_id, "completed")
    # completed 에서 더 전이 불법
    with pytest.raises(InvalidTransition):
        orders.transition(order_id, "confirmed")


def test_bank_transfer_same_status_noop(orders: BankTransferOrder) -> None:
    order = orders.create("9,900원", status="created")
    result = orders.transition(order["id"], "created")
    assert result["status"] == "created"  # 멱등 — 조용한 성공이지 무언가로의 no-op이 아님


def test_bank_transfer_stale_state_new_instance(tmp_path: Path) -> None:
    first = BankTransferOrder(tmp_path)
    order = first.create("99,000원")
    again = BankTransferOrder(tmp_path)
    assert again.get(order["id"])["status"] == "awaiting_payment"
    again.transition(order["id"], "confirmed")
    assert BankTransferOrder(tmp_path).get(order["id"])["status"] == "confirmed"


def test_bank_transfer_get_missing_raises_key_error(orders: BankTransferOrder) -> None:
    with pytest.raises(KeyError):
        orders.get("no-such-order")

# ── 다중 사용자 namespace 격리 (A1: 영수증 장부 개선) ─────────────────────────


def test_ledger_store_namespace_isolation(tmp_path: Path) -> None:
    """서로 다른 가게 코드(namespace)의 장부는 완전히 격리된다 (A1)."""
    store_a = LedgerStore(tmp_path, namespace="abcd")
    store_b = LedgerStore(tmp_path, namespace="efgh")

    entry = store_a.create("2025-07-15", "식대", 7000, note="설렁탕")

    # 같은 namespace에서만 보인다
    ids_a = {e["receipt_id"] for e in store_a.list()}
    ids_b = {e["receipt_id"] for e in store_b.list()}
    assert entry["receipt_id"] in ids_a
    assert entry["receipt_id"] not in ids_b
    assert len(ids_a) == 1 and len(ids_b) == 0


def test_ledger_store_namespace_default_is_default(tmp_path: Path) -> None:
    """namespace 미지정 시 'default' 저장소로 동작 — 기존 호출 호환 (A1)."""
    store = LedgerStore(tmp_path)
    store.create("2025-07-15", "식대", 5000)
    assert len(store.list()) == 1
    # 명시적 default와 같은 저장소
    same = LedgerStore(tmp_path, namespace="default")
    assert len(same.list()) == 1


def test_ledger_store_namespace_rejects_path_traversal(tmp_path: Path) -> None:
    """namespace에 경로 주입 문자를 넣으면 즉시 거부 (A1 보안)."""
    with pytest.raises(ValueError):
        LedgerStore(tmp_path, namespace="../../etc")
    with pytest.raises(ValueError):
        LedgerStore(tmp_path, namespace="ab cd")


# ── 가게 코드 PIN 잠금 (B1: 보안 강화) ───────────────────────────────────────


def test_store_pin_set_and_verify(tmp_path: Path) -> None:
    store = LedgerStore(tmp_path, namespace="abcd")
    assert store.has_pin() is False
    store.set_pin("1234")
    assert store.has_pin() is True
    ok, reason = store.verify_pin("1234")
    assert ok is True and reason == "ok"
    ok, reason = store.verify_pin("9999")
    assert ok is False and reason == "wrong"


def test_store_pin_not_set_reason(tmp_path: Path) -> None:
    store = LedgerStore(tmp_path, namespace="abcd")
    ok, reason = store.verify_pin("1234")
    assert ok is False and reason == "pin_not_set"


def test_store_pin_locks_after_5_failures(tmp_path: Path) -> None:
    store = LedgerStore(tmp_path, namespace="abcd")
    store.set_pin("1234")
    for _ in range(5):
        store.verify_pin("9999")
    ok, reason = store.verify_pin("1234")  # 맞는 PIN이어도 잠금
    assert ok is False and reason == "locked"


def test_store_pin_hash_not_plaintext(tmp_path: Path) -> None:
    store = LedgerStore(tmp_path, namespace="abcd")
    store.set_pin("1234")
    meta = (tmp_path / "ledger" / "abcd" / "meta.json").read_text(encoding="utf-8")
    assert "1234" not in meta
    assert "pin_hash" in meta


# ── 장부 강화: 카테고리 분석/전월 비교 (P1) ──────────────────────────────────


def test_monthly_report_category_breakdown(tmp_path: Path) -> None:
    store = LedgerStore(tmp_path, namespace="test")
    store.save({"store": "설렁탕집", "category": "식대", "total": 12000, "kind": "expense", "date": "2025-07-01"})
    store.save({"store": "김밥천국", "category": "식대", "total": 8000, "kind": "expense", "date": "2025-07-02"})
    store.save({"store": "택시", "category": "교통비", "total": 4800, "kind": "expense", "date": "2025-07-03"})
    report = store.monthly_report("2025-07")
    assert report["category_breakdown"] == {"식대": 20000, "교통비": 4800}
    assert report["top_stores"] == [("설렁탕집", 12000), ("김밥천국", 8000), ("택시", 4800)]
