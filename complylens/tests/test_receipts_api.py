"""영수증/장부/무통장 API 테스트 (W1-2~W1-6) — 결정적, 네트워크/모델 호출 없음.

- POST /api/receipts: 이미지 → OCR(monkeypatch) → 분류 → 카드 응답 + 장부 저장
- PATCH /api/receipts/{id}/correct: 수정 → few-shot 재학습 샘플 저장
- GET /api/ledger: 월간 리포트 (매출/지출/손익/미분류)
- GET /api/export: CSV/Excel 다운로드
- POST /api/orders {"product": ...}: 무통장 안내 + PATCH 확인 상태머신
- 오류 사례: 비이미지 4xx, OCR 실패 422, 잘못된 month 400, 불법 전이 409
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from complylens.receipts.classify import Classification
from complylens.receipts.ocr import ReceiptExtraction, ReceiptItem
from complylens.receipts.store import LedgerStore
from complylens.web.app import app

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"fake-image-bytes" * 4

_DEFAULT_CARD = {
    "store": "GS25 강남점",
    "date": "2025-07-15",
    "items": [("삼각김밥", 1500), ("바나나우유", 1800), ("도시락", 4500)],
    "total": 7800,
    "vat": 709,
    "payment": "신용카드",
    "needs_review": False,
    "warnings": [],
}


def _extraction(**overrides) -> ReceiptExtraction:
    data = {**_DEFAULT_CARD, **overrides}
    return ReceiptExtraction(
        store=data["store"],
        date=data["date"],
        items=[ReceiptItem(name=name, price=price) for name, price in data["items"]],
        total=data["total"],
        vat=data["vat"],
        payment=data["payment"],
        model="gemini-flash-lite-latest",
        needs_review=data["needs_review"],
        warnings=data["warnings"],
    )


def _fake_extract(self, image_bytes: bytes, mime_type: str = "image/png") -> ReceiptExtraction:
    return _extraction()


class _OCROverride:
    """GeminiOCRClient.extract를 임시 교체하는 컨텍스트 매니저 (테스트 전용)."""

    def __init__(self, func) -> None:
        self.func = func
        self._module = None

    def __enter__(self):
        from complylens.receipts import ocr as ocr_module

        self._module = ocr_module
        self._original = ocr_module.GeminiOCRClient.extract
        ocr_module.GeminiOCRClient.extract = self.func
        return self

    def __exit__(self, *exc) -> bool:
        self._module.GeminiOCRClient.extract = self._original
        return False


def _upload(client: TestClient) -> dict:
    resp = client.post(
        "/api/receipts",
        headers={"X-Store-Code": "test", "X-Store-Pin": "1234"},
        files={"file": ("gs25.png", io.BytesIO(PNG_BYTES), "image/png")},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.fixture()
def client(tmp_path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("COMPLYLENS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("OPENAI_API_KEY", "")  # GPT 분류 끔 → 결정적 규칙 폴백
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setattr(
        "complylens.receipts.ocr.GeminiOCRClient.extract",
        _fake_extract,
    )
    monkeypatch.setattr(
        "complylens.receipts.classify.CategoryClassifier.classify",
        lambda self, text, item_names=None: Classification("식대", 0.95, "llm"),
    )
    LedgerStore(tmp_path, namespace="test").set_pin("1234")
    return TestClient(app)


# ── POST /api/receipts ──────────────────────────────────────────────────────


def test_receipt_upload_returns_card_and_saves_ledger(client: TestClient, tmp_path: Path) -> None:
    card = _upload(client)
    assert card["store"] == "GS25 강남점"
    assert card["total"] == 7800
    assert card["date"] == "2025-07-15"
    assert len(card["items"]) == 3
    assert card["category"] == "식대"
    assert card["needs_review"] is False
    assert card["confidence"] == "high"
    assert card["ocr_model"] == "gemini-flash-lite-latest"

    entry = LedgerStore(tmp_path, namespace="test").get(card["receipt_id"])
    assert entry["category"] == "식대"
    assert entry["store"] == "GS25 강남점"
    assert entry["total"] == 7800


def test_receipt_upload_mismatch_flags_low_confidence(client: TestClient) -> None:
    with _OCROverride(
        lambda self, image_bytes, mime_type="image/png": _extraction(
            store="이마트 성수점",
            items=[("우유", 2980), ("계란", 79470)],
            total=78350,
            needs_review=True,
            warnings=["물품 합계(82450)가 총액(78350)과 일치하지 않습니다 — 검토 필요"],
        )
    ):
        card = _upload(client)
    assert card["needs_review"] is True
    assert card["confidence"] == "low"
    assert card["warnings"]
    # 조용히 수용하지 않는다 — low confidence 카드로 반환
    assert card["total"] == 78350


def test_receipt_upload_rejects_non_image(client: TestClient) -> None:
    resp = client.post(
        "/api/receipts",
        files={"file": ("notes.txt", io.BytesIO(b"plain text"), "text/plain")},
    )
    assert resp.status_code == 400
    resp2 = client.post(
        "/api/receipts",
        files={"file": ("fake.png", io.BytesIO(b"not an image"), "image/png")},
    )
    assert resp2.status_code == 400


def test_receipt_upload_ocr_failure_422(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from complylens.receipts.ocr import OCRUnavailableError

    def fail(self, image_bytes: bytes, mime_type: str = "image/png") -> ReceiptExtraction:
        raise OCRUnavailableError("gemini unavailable")

    monkeypatch.setattr("complylens.receipts.ocr.GeminiOCRClient.extract", fail)
    resp = client.post(
        "/api/receipts",
        headers={"X-Store-Code": "test", "X-Store-Pin": "1234"},
        files={"file": ("r.png", io.BytesIO(PNG_BYTES), "image/png")},
    )
    assert resp.status_code == 422


# ── PATCH /api/receipts/{id}/correct ────────────────────────────────────────


def test_correct_receipt_saves_few_shot_sample(client: TestClient, tmp_path: Path) -> None:
    card = _upload(client)
    resp = client.patch(
        f"/api/receipts/{card['receipt_id']}/correct",
        headers={"X-Store-Code": "test", "X-Store-Pin": "1234"},
        json={
            "category": "소모품",
            "items": [{"name": "삼각김밥", "price": "1,500"}, {"name": "바나나우유", "price": "1,800"}, {"name": "도시락", "price": "4,500"}],
            "total": "7,800",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["category"] == "소모품"
    assert body["corrected"] is True
    assert body["needs_review"] is False

    ledger = LedgerStore(tmp_path, namespace="test")
    updated = ledger.get(card["receipt_id"])
    assert updated["category"] == "소모품"
    assert updated["category_source"] == "manual"
    sample = ledger.get_correction(card["receipt_id"])
    assert sample is not None
    assert sample["original"]["category"] == "식대"
    assert sample["corrected"]["category"] == "소모품"
    assert sample["receipt_id"] == card["receipt_id"]


def test_correct_receipt_invalid_category_400(client: TestClient) -> None:
    card = _upload(client)
    resp = client.patch(f"/api/receipts/{card['receipt_id']}/correct", json={"category": "없는과목"})
    assert resp.status_code == 400


def test_correct_receipt_missing_404(client: TestClient) -> None:
    resp = client.patch(
        "/api/receipts/ffffffffffff/correct",
        headers={"X-Store-Code": "test", "X-Store-Pin": "1234"},
        json={"store": "가게"},
    )
    assert resp.status_code == 404


# ── GET /api/ledger ─────────────────────────────────────────────────────────


def _seed_ledger(tmp_path: Path) -> None:
    ledger = LedgerStore(tmp_path, namespace="test")
    ledger.create("2025-07-01", "식대", 12000, note="설렁탕")
    ledger.create("2025-07-02", "교통비", 4800, note="택시")
    ledger.create("2025-07-03", "기타", 10000, note="프린터토너")
    ledger.create("2025-08-01", "식대", 5000, note="다음 달")


def test_ledger_monthly_report(client: TestClient, tmp_path: Path) -> None:
    _seed_ledger(tmp_path)
    resp = client.get(
        "/api/ledger", headers={"X-Store-Code": "test", "X-Store-Pin": "1234"}, params={"month": "2025-07"}
    )
    assert resp.status_code == 200
    report = resp.json()
    assert report["month"] == "2025-07"
    assert report["entry_count"] == 3
    assert report["expense"] == 26800
    assert report["revenue"] == 0
    assert report["profit"] == -26800
    assert report["unclassified_count"] == 1  # 기타


def test_ledger_default_month_and_invalid_month(client: TestClient) -> None:
    assert client.get("/api/ledger", headers={"X-Store-Code": "test", "X-Store-Pin": "1234"}).status_code == 200
    resp = client.get(
        "/api/ledger", headers={"X-Store-Code": "test", "X-Store-Pin": "1234"}, params={"month": "2025-13"}
    )
    assert resp.status_code == 400


# ── GET /api/export ─────────────────────────────────────────────────────────


def _subscribe(client: TestClient) -> str:
    """무통장 주문 생성 → 입금 확인(confirm) → 구독 활성화 (G4 게이팅 해제)."""
    resp = client.post(
        "/api/orders",
        headers={"X-Store-Code": "test", "X-Store-Pin": "1234"},
        json={"product": "receipt-ledger-lite"},
    )
    assert resp.status_code == 200, resp.text
    order_id = resp.json()["order_id"]
    confirm = client.patch(
        f"/api/orders/{order_id}",
        headers={"X-Store-Code": "test", "X-Store-Pin": "1234"},
        json={"action": "confirm"},
    )
    assert confirm.status_code == 200, confirm.text
    return order_id


def test_export_csv(client: TestClient, tmp_path: Path) -> None:
    _seed_ledger(tmp_path)
    _subscribe(client)  # G4: 내보내기는 유료 구독 기능
    resp = client.get(
        "/api/export",
        headers={"X-Store-Code": "test", "X-Store-Pin": "1234"},
        params={"month": "2025-07", "format": "csv"},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "receipt-ledger-2025-07.csv" in resp.headers["content-disposition"]
    text = resp.content.decode("utf-8-sig")
    assert "일자" in text
    assert "택시" in text
    assert "설렁탕" in text


def test_export_excel(client: TestClient, tmp_path: Path) -> None:
    _seed_ledger(tmp_path)
    _subscribe(client)
    resp = client.get(
        "/api/export",
        headers={"X-Store-Code": "test", "X-Store-Pin": "1234"},
        params={"month": "2025-07", "format": "excel"},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    with zipfile.ZipFile(io.BytesIO(resp.content)) as archive:
        names = archive.namelist()
        assert "xl/worksheets/sheet1.xml" in names
        sheet = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
        assert "택시" in sheet


def test_export_requires_subscription_402(client: TestClient) -> None:
    """G4: confirmed 주문 없이 내보내기 시도 → 402 Payment Required."""
    resp = client.get(
        "/api/export",
        headers={"X-Store-Code": "test", "X-Store-Pin": "1234"},
        params={"month": "2025-07", "format": "csv"},
    )
    assert resp.status_code == 402
    assert "유료 구독" in resp.json()["detail"]


def test_export_errors(client: TestClient) -> None:
    headers = {"X-Store-Code": "test"}
    assert client.get("/api/export", headers=headers, params={"format": "pdf"}).status_code == 400
    assert client.get("/api/export", headers=headers, params={"month": "bad"}).status_code == 400


# ── 무통장 주문 (W1-6) ─────────────────────────────────────────────────────


def test_bank_transfer_order_flow(client: TestClient) -> None:
    headers = {"X-Store-Code": "test", "X-Store-Pin": "1234"}
    resp = client.post("/api/orders", headers=headers, json={"product": "receipt-ledger-lite"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "awaiting_payment"
    assert body["amount_krw"] == 9900
    assert {"bank", "holder", "account_number"} <= set(body["bank"])
    assert "입금" in body["instructions"]

    order_id = body["order_id"]
    confirm = client.patch(f"/api/orders/{order_id}", headers=headers, json={"action": "confirm"})
    assert confirm.status_code == 200
    assert confirm.json()["status"] == "confirmed"

    complete = client.patch(f"/api/orders/{order_id}", headers=headers, json={"action": "complete"})
    assert complete.status_code == 200
    assert complete.json()["status"] == "completed"


def test_bank_transfer_illegal_transition_409(client: TestClient) -> None:
    headers = {"X-Store-Code": "test", "X-Store-Pin": "1234"}
    body = client.post("/api/orders", headers=headers, json={"product": "receipt-ledger-lite"}).json()
    order_id = body["order_id"]
    # awaiting_payment → completed 는 불법 (confirmed 건너뜁)
    resp = client.patch(f"/api/orders/{order_id}", headers=headers, json={"action": "complete"})
    assert resp.status_code == 409
    assert resp.json()["detail"].startswith("cannot go")


def test_bank_transfer_bad_requests(client: TestClient) -> None:
    headers = {"X-Store-Code": "test", "X-Store-Pin": "1234"}
    assert client.post("/api/orders", headers=headers, json={"product": "nope"}).status_code == 400
    # product 체크가 우선 — email 유무와 무관하게 무통장 경로
    resp = client.post(
        "/api/orders", headers=headers, json={"product": "receipt-ledger-lite", "email": "x@y.z"}
    )
    assert resp.status_code == 200
    order_id = resp.json()["order_id"]
    assert client.patch(f"/api/orders/{order_id}", headers=headers, json={"action": "nope"}).status_code == 400
    assert client.patch("/api/orders/deadbeef", headers=headers, json={"action": "confirm"}).status_code == 404


def test_order_requires_store_code_400(client: TestClient) -> None:
    """무통장 주문도 가게 코드 헤더가 필요하다 (G4 게이팅 매칭용)."""
    resp = client.post("/api/orders", json={"product": "receipt-ledger-lite"})
    assert resp.status_code == 400
    assert "X-Store-Code" in resp.json()["detail"]

# ── 다중 사용자 X-Store-Code 격리 (A2/A4: 영수증 장부 개선) ──────────────────


def test_receipt_upload_without_store_code_400(client: TestClient) -> None:
    """X-Store-Code 헤더 없이 업로드하면 400 (A4)."""
    resp = client.post(
        "/api/receipts",
        files={"file": ("gs25.png", io.BytesIO(PNG_BYTES), "image/png")},
    )
    assert resp.status_code == 400
    assert "X-Store-Code" in resp.json()["detail"]


def test_ledger_isolated_between_store_codes(client: TestClient, tmp_path: Path) -> None:
    """다른 가게 코드의 장부는 서로 보이지 않는다 (A1)."""
    LedgerStore(tmp_path, namespace="abcd").set_pin("1234")
    LedgerStore(tmp_path, namespace="efgh").set_pin("1234")
    resp = client.post(
        "/api/receipts",
        headers={"X-Store-Code": "abcd", "X-Store-Pin": "1234"},
        files={"file": ("gs25.png", io.BytesIO(PNG_BYTES), "image/png")},
    )
    assert resp.status_code == 200, resp.text

    mine = client.get("/api/ledger", headers={"X-Store-Code": "abcd", "X-Store-Pin": "1234"}, params={"month": "2025-07"})
    other = client.get("/api/ledger", headers={"X-Store-Code": "efgh", "X-Store-Pin": "1234"}, params={"month": "2025-07"})
    assert mine.status_code == 200
    assert other.status_code == 200
    assert mine.json()["entry_count"] >= 1
    assert other.json()["entry_count"] == 0


# ── C1/C2: 합계 검증 + few-shot 학습 (영수증 장부 개선) ──────────────────────


def test_receipt_upload_items_total_mismatch_adds_warning(client: TestClient) -> None:
    """OCR이 경고를 안 줘도 품목 합계 ≠ 총액이면 needs_review + 경고 (C1)."""
    with _OCROverride(
        lambda self, image_bytes, mime_type="image/png": _extraction(
            store="이마트 성수점",
            items=[("우유", 2980), ("계란", 79470)],
            total=78350,
            needs_review=False,  # OCR 자체는 경고 없음
            warnings=[],  # OCR 경고 없음
        )
    ):
        card = _upload(client)
    assert card["needs_review"] is True
    assert any("합계" in w for w in card["warnings"]), card["warnings"]


def test_correct_teaches_classifier_for_same_store(client: TestClient) -> None:
    """수정(few-shot) 후 같은 가게 영수증은 수정한 분류로 자동 분류 (C2)."""
    card = _upload(client)  # fixture: 항상 "식대" 분류, store=GS25 강남점
    assert card["category"] == "식대"

    resp = client.patch(
        f"/api/receipts/{card['receipt_id']}/correct",
        headers={"X-Store-Code": "test", "X-Store-Pin": "1234"},
        json={"category": "소모품"},
    )
    assert resp.status_code == 200

    # 같은 가게 재업로드 → correction 규칙이 "식대" → "소모품"으로 override
    # (같은 이미지를 다시 올리면 G2 멱등성으로 중복 처리되므로 다른 바이트 사용)
    card2 = client.post(
        "/api/receipts",
        headers={"X-Store-Code": "test", "X-Store-Pin": "1234"},
        files={"file": ("gs25b.png", io.BytesIO(PNG_BYTES + b"-2"), "image/png")},
    ).json()
    assert card2["category"] == "소모품"
    assert card2["category_source"] == "correction"


# ── 가게 코드 PIN 라우트 (B2: 보안 강화) ─────────────────────────────────────


def test_receipt_upload_without_pin_428(client: TestClient, tmp_path: Path) -> None:
    LedgerStore(tmp_path, namespace="nopin").set_pin("1234")
    resp = client.post(
        "/api/receipts",
        headers={"X-Store-Code": "nopin"},  # PIN 헤더 없음
        files={"file": ("r.png", io.BytesIO(PNG_BYTES), "image/png")},
    )
    assert resp.status_code == 400  # X-Store-Pin header required
    assert "X-Store-Pin" in resp.json()["detail"]


def test_receipt_upload_wrong_pin_403(client: TestClient, tmp_path: Path) -> None:
    LedgerStore(tmp_path, namespace="wrongpin").set_pin("1234")
    resp = client.post(
        "/api/receipts",
        headers={"X-Store-Code": "wrongpin", "X-Store-Pin": "9999"},
        files={"file": ("r.png", io.BytesIO(PNG_BYTES), "image/png")},
    )
    assert resp.status_code == 403


def test_receipt_upload_pin_not_set_428(client: TestClient, tmp_path: Path) -> None:
    LedgerStore(tmp_path, namespace="nopin2")  # PIN 미설정
    resp = client.post(
        "/api/receipts",
        headers={"X-Store-Code": "nopin2", "X-Store-Pin": "1234"},
        files={"file": ("r.png", io.BytesIO(PNG_BYTES), "image/png")},
    )
    assert resp.status_code == 428


def test_receipt_upload_pin_locked_after_failures(client: TestClient, tmp_path: Path) -> None:
    store = LedgerStore(tmp_path, namespace="lockpin")
    store.set_pin("1234")
    for _ in range(5):
        client.post(
            "/api/receipts",
            headers={"X-Store-Code": "lockpin", "X-Store-Pin": "9999"},
            files={"file": ("r.png", io.BytesIO(PNG_BYTES), "image/png")},
        )
    resp = client.post(
        "/api/receipts",
        headers={"X-Store-Code": "lockpin", "X-Store-Pin": "1234"},  # 맞는 PIN
        files={"file": ("r.png", io.BytesIO(PNG_BYTES), "image/png")},
    )
    assert resp.status_code == 429


def test_setup_store_pin_endpoint(client: TestClient) -> None:
    resp = client.post(
        "/api/store",
        headers={"X-Store-Code": "newcode"},
        json={"pin": "5678"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["pin_set"] is True
    # 설정 후 PIN으로 접근 가능
    up = client.post(
        "/api/receipts",
        headers={"X-Store-Code": "newcode", "X-Store-Pin": "5678"},
        files={"file": ("r.png", io.BytesIO(PNG_BYTES), "image/png")},
    )
    assert up.status_code == 200, up.text


# ── 장부 강화: 전월 비교 (P1) ────────────────────────────────────────────────


def test_ledger_report_prev_month_comparison(client: TestClient, tmp_path: Path) -> None:
    _seed_ledger(tmp_path)  # 2025-07: 3건 26800 / 2025-08: 1건 5000
    headers = {"X-Store-Code": "test", "X-Store-Pin": "1234"}
    resp = client.get("/api/ledger", headers=headers, params={"month": "2025-07"})
    assert resp.status_code == 200
    report = resp.json()
    assert "prev_expense" in report and "prev_profit" in report
    assert report["prev_expense"] == 0  # 6월 데이터 없음

    resp2 = client.get("/api/ledger", headers=headers, params={"month": "2025-08"})
    assert resp2.status_code == 200
    assert resp2.json()["prev_expense"] == 26800
    assert resp2.json()["prev_profit"] == -26800


# ── 장부 강화: 수입 등록 + 거래 삭제 (P2) ────────────────────────────────────


def test_add_income_entry_reflects_revenue(client: TestClient, tmp_path: Path) -> None:
    _seed_ledger(tmp_path)
    resp = client.post(
        "/api/entries",
        headers={"X-Store-Code": "test", "X-Store-Pin": "1234"},
        json={
            "store": "현금 매출",
            "category": "식대",
            "amount": "50,000",
            "date": "2025-07-10",
            "kind": "income",
            "note": "일 매출",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["kind"] == "income"
    assert body["category"] == "식대"

    report = client.get(
        "/api/ledger",
        headers={"X-Store-Code": "test", "X-Store-Pin": "1234"},
        params={"month": "2025-07"},
    ).json()
    assert report["revenue"] == 50000
    assert report["profit"] == -26800 + 50000


def test_add_entry_invalid_kind_400(client: TestClient) -> None:
    resp = client.post(
        "/api/entries",
        headers={"X-Store-Code": "test", "X-Store-Pin": "1234"},
        json={"store": "x", "category": "식대", "amount": 1000, "kind": "투자"},
    )
    assert resp.status_code == 400


def test_delete_entry_removes_from_ledger(client: TestClient) -> None:
    card = _upload(client)
    resp = client.delete(
        f"/api/entries/{card['receipt_id']}",
        headers={"X-Store-Code": "test", "X-Store-Pin": "1234"},
    )
    assert resp.status_code == 200
    report = client.get(
        "/api/ledger",
        headers={"X-Store-Code": "test", "X-Store-Pin": "1234"},
        params={"month": "2025-07"},
    ).json()
    assert card["receipt_id"] not in [e["receipt_id"] for e in report["entries"]]


def test_delete_entry_missing_404(client: TestClient) -> None:
    resp = client.delete(
        "/api/entries/ffffffffffff",
        headers={"X-Store-Code": "test", "X-Store-Pin": "1234"},
    )
    assert resp.status_code == 404


# ── P0 gate: G2 멱등성 / G3 PIN 변경 / G4 게이팅 / G5 원본 보관 / G7 이벤트 ──


def test_upload_duplicate_image_is_idempotent(client: TestClient, tmp_path: Path) -> None:
    """G2: 같은 이미지를 두 번 올리면 같은 receipt_id + duplicate=True, 장부 1건만."""
    first = _upload(client)
    second = _upload(client)
    assert first["receipt_id"] == second["receipt_id"]
    assert second.get("duplicate") is True
    entries = LedgerStore(tmp_path, namespace="test").list_entries("2025-07")
    assert sum(1 for e in entries if e.get("ocr_model")) == 1


def test_upload_duplicate_only_within_window(client: TestClient, tmp_path: Path) -> None:
    """G2: 다른 내용의 이미지는 중복으로 보지 않는다 (해시가 다르면 별도 기록)."""
    first = _upload(client)
    other = client.post(
        "/api/receipts",
        headers={"X-Store-Code": "test", "X-Store-Pin": "1234"},
        files={"file": ("gs25.png", io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"different" * 4), "image/png")},
    )
    assert other.status_code == 200, other.text
    assert other.json()["receipt_id"] != first["receipt_id"]
    assert other.json().get("duplicate") is None


def test_pin_change_requires_current_pin(client: TestClient) -> None:
    """G3: 기존 PIN 없이는 변경 불가, 틀리면 403, 맞으면 200."""
    headers = {"X-Store-Code": "test", "X-Store-Pin": "1234"}
    # current_pin 없이 시도 → 400
    resp = client.post("/api/store", headers=headers, json={"pin": "5678"})
    assert resp.status_code == 400
    assert "current_pin" in resp.json()["detail"]
    # 틀린 기존 PIN → 403
    resp = client.post("/api/store", headers=headers, json={"pin": "5678", "current_pin": "9999"})
    assert resp.status_code == 403
    # 올바른 기존 PIN → 변경 성공, 새 PIN으로 접근 가능
    resp = client.post("/api/store", headers=headers, json={"pin": "5678", "current_pin": "1234"})
    assert resp.status_code == 200
    ok = client.get(
        "/api/ledger", headers={"X-Store-Code": "test", "X-Store-Pin": "5678"}, params={"month": "2025-07"}
    )
    assert ok.status_code == 200
    old = client.get(
        "/api/ledger", headers={"X-Store-Code": "test", "X-Store-Pin": "1234"}, params={"month": "2025-07"}
    )
    assert old.status_code == 403


def test_monthly_free_tier_limit_402(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A1: 무료 티어 한도를 넘는 업로드는 402 + 결제 유도 문구."""
    monkeypatch.setenv("RECEIPT_FREE_MONTHLY_LIMIT", "1")
    monkeypatch.setenv("COMPLYLENS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setattr(
        "complylens.receipts.ocr.GeminiOCRClient.extract", _fake_extract
    )
    monkeypatch.setattr(
        "complylens.receipts.classify.CategoryClassifier.classify",
        lambda self, text, item_names=None: Classification("식대", 0.95, "llm"),
    )
    LedgerStore(tmp_path, namespace="test").set_pin("1234")
    client = TestClient(app)

    first = _upload(client)
    assert first["receipt_id"]
    second = client.post(
        "/api/receipts",
        headers={"X-Store-Code": "test", "X-Store-Pin": "1234"},
        files={"file": ("b.png", io.BytesIO(PNG_BYTES + b"x"), "image/png")},
    )
    assert second.status_code == 402
    assert "무료 티어" in second.json()["detail"]
    assert "입금 확인" in second.json()["detail"]


def test_paid_subscription_applies_paid_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A1: 구독(confirmed) 사용자는 유료 한도가 적용된다 — 무료 한도와 분리."""
    monkeypatch.setenv("RECEIPT_FREE_MONTHLY_LIMIT", "1")  # 무료 1장
    monkeypatch.setenv("RECEIPT_MONTHLY_UPLOAD_LIMIT", "2")  # 유료 2장
    monkeypatch.setenv("COMPLYLENS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setattr(
        "complylens.receipts.ocr.GeminiOCRClient.extract", _fake_extract
    )
    monkeypatch.setattr(
        "complylens.receipts.classify.CategoryClassifier.classify",
        lambda self, text, item_names=None: Classification("식대", 0.95, "llm"),
    )
    LedgerStore(tmp_path, namespace="test").set_pin("1234")
    client = TestClient(app)
    headers = {"X-Store-Code": "test", "X-Store-Pin": "1234"}

    # 구독 활성화 (confirmed 주문)
    order = client.post("/api/orders", headers=headers, json={"product": "receipt-ledger-lite"})
    assert order.status_code == 200
    assert (
        client.patch(
            f"/api/orders/{order.json()['order_id']}", headers=headers, json={"action": "confirm"}
        ).status_code
        == 200
    )

    # 무료 한도(1)를 넘겨도 유료 한도(2)까지 업로드 가능 (서로 다른 이미지)
    def _upload_bytes(mark: bytes) -> str:
        resp = client.post(
            "/api/receipts",
            headers=headers,
            files={"file": ("r.png", io.BytesIO(PNG_BYTES + mark), "image/png")},
        )
        assert resp.status_code == 200, resp.text
        return resp.json()["receipt_id"]

    assert _upload_bytes(b"-1")
    assert _upload_bytes(b"-2")
    third = client.post(
        "/api/receipts",
        headers=headers,
        files={"file": ("c.png", io.BytesIO(PNG_BYTES + b"y"), "image/png")},
    )
    assert third.status_code == 402
    assert "한도에 도달" in third.json()["detail"]
    assert "무료 티어" not in third.json()["detail"]


def test_upload_persists_original_image(client: TestClient, tmp_path: Path) -> None:
    """G5: 업로드 원본 이미지가 data/receipt-images/ 아래에 보관된다."""
    card = _upload(client)
    images = list((tmp_path / "receipt-images" / "test").glob(f"{card['receipt_id']}.*"))
    assert len(images) == 1
    assert images[0].read_bytes() == PNG_BYTES
    entry = LedgerStore(tmp_path, namespace="test").get(card["receipt_id"])
    assert entry["image_path"] == f"test/{card['receipt_id']}.png"


def test_events_endpoint_records_jsonl(client: TestClient, tmp_path: Path) -> None:
    """G7: POST /api/events가 data/events/{store}/{month}.jsonl에 누적한다."""
    headers = {"X-Store-Code": "test", "X-Store-Pin": "1234"}
    resp = client.post("/api/events", headers=headers, json={"event": "export_downloaded", "meta": {"format": "csv"}})
    assert resp.status_code == 200
    assert resp.json()["event"] == "export_downloaded"
    assert client.post("/api/events", headers=headers, json={}).status_code == 400
    # 2026-08 기준 현재 월 파일에 기록됨
    from datetime import UTC, datetime

    month = datetime.now(UTC).strftime("%Y-%m")
    path = tmp_path / "events" / "test" / f"{month}.jsonl"
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert '"event": "export_downloaded"' in lines[0]


# ── T3: 장부 탭 거래 수정 + few-shot 학습 (무료 티어 장부 고도화) ────────────


def test_patch_entry_updates_category_and_records_correction(
    client: TestClient, tmp_path: Path
) -> None:
    """T3: OCR 영수증 거래 카테고리 수정 → 장부 반영 + few-shot 샘플 저장."""
    card = _upload(client)
    headers = {"X-Store-Code": "test", "X-Store-Pin": "1234"}
    resp = client.patch(
        f"/api/entries/{card['receipt_id']}",
        headers=headers,
        json={"category": "교통비"},
    )
    assert resp.status_code == 200, resp.text
    entry = LedgerStore(tmp_path, namespace="test").get(card["receipt_id"])
    assert entry["category"] == "교통비"
    corrections = LedgerStore(tmp_path, namespace="test").list_corrections()
    assert len(corrections) == 1
    assert corrections[0]["corrected"]["category"] == "교통비"


def test_patch_entry_updates_total_and_date(client: TestClient, tmp_path: Path) -> None:
    """T3: 금액·날짜도 수정 가능."""
    card = _upload(client)
    headers = {"X-Store-Code": "test", "X-Store-Pin": "1234"}
    resp = client.patch(
        f"/api/entries/{card['receipt_id']}",
        headers=headers,
        json={"total": 9000, "date": "2025-07-16"},
    )
    assert resp.status_code == 200, resp.text
    entry = LedgerStore(tmp_path, namespace="test").get(card["receipt_id"])
    assert entry["total"] == 9000
    assert entry["date"] == "2025-07-16"
    # 카테고리 변경 없음 → correction 샘플 추가 없음
    assert len(LedgerStore(tmp_path, namespace="test").list_corrections()) == 0


def test_patch_entry_manual_income_does_not_learn(client: TestClient, tmp_path: Path) -> None:
    """T3 edge: 수동 등록(수입) 수정은 few-shot 학습에서 제외된다."""
    headers = {"X-Store-Code": "test", "X-Store-Pin": "1234"}
    created = client.post(
        "/api/entries", headers=headers,
        json={"kind": "income", "category": "기타", "amount": 50000, "store": "현금 매출"},
    )
    assert created.status_code == 200, created.text
    entry_id = created.json()["receipt_id"]
    resp = client.patch(
        f"/api/entries/{entry_id}", headers=headers, json={"category": "소모품"}
    )
    assert resp.status_code == 200, resp.text
    assert LedgerStore(tmp_path, namespace="test").list_corrections() == []


def test_patch_entry_validation(client: TestClient) -> None:
    """T3: 없는 거래 404, 잘못된 카테고리 400, 빈 요청 400."""
    headers = {"X-Store-Code": "test", "X-Store-Pin": "1234"}
    assert (
        client.patch("/api/entries/deadbeef", headers=headers, json={"category": "식대"}).status_code
        == 404
    )
    card = _upload(client)
    assert (
        client.patch(
            f"/api/entries/{card['receipt_id']}", headers=headers, json={"category": "없는분류"}
        ).status_code
        == 400
    )
    assert (
        client.patch(
            f"/api/entries/{card['receipt_id']}", headers=headers, json={}
        ).status_code
        == 400
    )
