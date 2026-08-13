"""FastAPI 웹 앱 — 감사 업로드/조회/PDF/공개요약, API 키 인증."""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import uuid
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Final, assert_never

import pandas as pd
import stripe
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles

from complylens.audit.core import MissingCategoryError, evaluate_audit
from complylens.legal.kit import SignoffRequired, SignoffStore
from complylens.llm.gateway import (
    HallucinationDetected,
    LLMGateway,
    NoProviderAvailable,
    Provider,
)
from complylens.receipts.banktransfer import (
    BANK_TRANSFER_PRODUCTS,
    BankTransferOrderStore,
    product_amount_krw,
)
from complylens.receipts.banktransfer import (
    InvalidTransition as BankTransferInvalidTransition,
)
from complylens.receipts.export import entries_to_csv, entries_to_xlsx
from complylens.receipts.ocr import OCRUnavailableError, to_price
from complylens.receipts.service import ReceiptPipeline
from complylens.receipts.store import LedgerStore
from complylens.receipts.schema import ACCOUNT_CATEGORIES
from complylens.report.builder import (
    build_detailed_report_html,
    build_notice_text,
    build_public_summary_html,
    render_pdf,
)
from complylens.web.billing import (
    StripeConfigurationError,
    create_product_checkout_session,
)
from complylens.web.leads import LeadStore
from complylens.web.orders import (
    PRODUCTS,
    OrderStore,
    PaymentConflict,
    PaymentMethod,
    verify_btc_payment,
)
from complylens.web.stats import PVStore

app = FastAPI(title="ComplyLens", version="0.1.0")

# 웹(브라우저) 클라이언트에서 receipt API 호출 허용 — X-Store-Code 헤더 포함 (A~D 개선)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["X-Store-Code", "X-Store-Pin", "Content-Type"],
)

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
REQUIRED_CATEGORIES = ["male", "female"]
MAX_UPLOAD_BYTES: Final = 100 * 1024 * 1024
AUDIT_SLA_HOURS: Final = 72


class PaymentMode(StrEnum):
    BTC = "btc"
    STRIPE = "stripe"


def _payment_mode() -> PaymentMode:
    raw_mode = os.environ.get("COMPLYLENS_PAYMENT_MODE", PaymentMode.BTC.value).strip().lower()
    try:
        return PaymentMode(raw_mode)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail="invalid payment mode") from exc


def _require_api_key(api_key: str | None = Depends(_api_key_header)) -> None:
    expected = os.environ.get("COMPLYLENS_API_KEY")
    if not expected:
        raise HTTPException(status_code=503, detail="service not configured")
    if api_key != expected:
        raise HTTPException(status_code=401, detail="invalid or missing API key")


def _data_dir() -> Path:
    path = Path(os.environ.get("COMPLYLENS_DATA_DIR", "data"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def _audit_dir(audit_id: str) -> Path:
    if len(audit_id) != 12 or any(char not in "0123456789abcdef" for char in audit_id):
        raise HTTPException(status_code=404, detail="audit not found")
    return _data_dir() / audit_id


def _parse_csv(content: bytes) -> pd.DataFrame:
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"unreadable CSV: {exc}") from exc
    required = {"candidate_id", "category"}
    if not required.issubset(df.columns):
        raise HTTPException(status_code=400, detail=f"CSV must contain columns: {required}")
    if "selected" not in df.columns and "score" not in df.columns:
        raise HTTPException(status_code=400, detail="CSV must contain 'selected' or 'score' column")
    return df


def _llm_gateway() -> LLMGateway | None:
    if os.environ.get("COMPLYLENS_LLM_ENABLED") != "1":
        return None
    providers = [
        Provider("deepinfra", "https://api.deepinfra.com/v1", "DEEPINFRA_API_KEY", "deepseek-ai/DeepSeek-V4-Flash", "non_prc"),
        Provider("digitalocean", "https://inference.digitalocean.com/v1", "DIGITALOCEAN_API_KEY", "deepseek-v4-flash", "non_prc"),
        Provider("deepseek", "https://api.deepseek.com", "DEEPSEEK_API_KEY", "deepseek-v4-flash", "prc"),
    ]
    return LLMGateway(providers)


def _run_pipeline(df: pd.DataFrame, tool_description: str, audit_date: str) -> dict:
    score_col = "score" if "score" in df.columns else None
    audit = evaluate_audit(
        df,
        category_col="category",
        selection_col="selected",
        score_col=score_col,
        required_categories=REQUIRED_CATEGORIES,
    )
    narrative = (
        "This analysis was completed by the ComplyLens statistical engine. "
        "All figures are reported in the tables below."
    )
    gw = _llm_gateway()
    if gw is not None:
        try:
            narrative = gw.generate_narrative(
                "Write one neutral sentence describing a completed bias audit. "
                "Do not include any numbers.",
                sensitive=True,
            )
        except (HallucinationDetected, NoProviderAvailable):
            narrative = (
                "This audit was completed by the ComplyLens statistical engine. "
                "All figures are reported in the tables below."
            )
    return {
        "audit_json": audit,
        "narrative": narrative,
        "tool_description": tool_description,
        "audit_date": audit_date,
    }


@app.post("/api/audits")
def create_audit(
    file: UploadFile = File(...),  # noqa: B008 - FastAPI 의존성 주입 관용구
    tool_description: str = Form(..., min_length=1),
    _: None = Depends(_require_api_key),
) -> dict:
    if not tool_description.strip():
        raise HTTPException(status_code=400, detail="tool_description is required")
    processing_started_at = datetime.now(UTC)
    content = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="CSV exceeds the 100 MB limit")
    df = _parse_csv(content)
    audit_id = uuid.uuid4().hex[:12]
    audit_date = datetime.now(UTC).strftime("%Y-%m-%d")
    try:
        payload = _run_pipeline(df, tool_description.strip(), audit_date)
    except MissingCategoryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    record = {
        "audit_id": audit_id,
        "created_at": datetime.now(UTC).isoformat(),
        "processing_started_at": processing_started_at.isoformat(),
        "processing_completed_at": datetime.now(UTC).isoformat(),
        "sla_due_at": (
            processing_started_at + timedelta(hours=AUDIT_SLA_HOURS)
        ).isoformat(),
        "tool_description": payload["tool_description"],
        "audit_date": audit_date,
        "result": payload["audit_json"],
        "narrative": payload["narrative"],
    }
    base = _data_dir() / audit_id
    base.mkdir(parents=True, exist_ok=True)
    (base / "record.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    detailed_html = build_detailed_report_html(
        payload["audit_json"], payload["narrative"], payload["tool_description"]
    )
    render_pdf(detailed_html, base / "report.pdf")
    (base / "summary.html").write_text(
        build_public_summary_html(payload["audit_json"], payload["tool_description"], audit_date),
        encoding="utf-8",
    )
    (base / "notice.txt").write_text(
        build_notice_text(payload["tool_description"], audit_date), encoding="utf-8"
    )
    return {"audit_id": audit_id, "result": payload["audit_json"]}


def _load_record(audit_id: str) -> dict:
    record_path = _audit_dir(audit_id) / "record.json"
    if not record_path.exists():
        raise HTTPException(status_code=404, detail="audit not found")
    return json.loads(record_path.read_text(encoding="utf-8"))


@app.get("/api/audits/{audit_id}")
def get_audit(audit_id: str, _: None = Depends(_require_api_key)) -> dict:
    return _load_record(audit_id)


@app.get("/api/audits/{audit_id}/report.pdf")
def download_report(audit_id: str, _: None = Depends(_require_api_key)) -> FileResponse:
    audit_dir = _audit_dir(audit_id)
    try:
        SignoffStore(_data_dir()).require_signoff(audit_id)
    except SignoffRequired as exc:
        raise HTTPException(status_code=409, detail="independent-auditor signoff required") from exc
    pdf = audit_dir / "report.pdf"
    if not pdf.exists():
        raise HTTPException(status_code=404, detail="report not found")
    return FileResponse(pdf, media_type="application/pdf", filename=f"{audit_id}-report.pdf")


@app.post("/api/audits/{audit_id}/signoff")
def record_audit_signoff(
    audit_id: str,
    payload: dict,
    _: None = Depends(_require_api_key),
) -> dict[str, str]:
    _load_record(audit_id)
    signer = (payload.get("signer") or "").strip()
    if not signer:
        raise HTTPException(status_code=400, detail="signer is required")
    SignoffStore(_data_dir()).sign(audit_id, signer[:200])
    return {"audit_id": audit_id, "signer": signer[:200], "status": "signed"}


@app.get("/api/audits/{audit_id}/summary", response_class=HTMLResponse)
def public_summary(audit_id: str) -> str:
    audit_dir = _audit_dir(audit_id)
    try:
        SignoffStore(_data_dir()).require_signoff(audit_id)
    except SignoffRequired as exc:
        raise HTTPException(status_code=409, detail="independent-auditor signoff required") from exc
    summary = audit_dir / "summary.html"
    if not summary.exists():
        raise HTTPException(status_code=404, detail="summary not found")
    return summary.read_text(encoding="utf-8")


@app.post("/api/pv")
def record_pageview(payload: dict) -> dict:
    path = (payload.get("path") or "").strip()
    if not path or not path.startswith("/"):
        raise HTTPException(status_code=400, detail="valid path required")
    referrer = (payload.get("referrer") or "").strip()
    PVStore(_data_dir()).record(path, referrer)
    return {"status": "recorded"}


@app.get("/api/stats")
def get_stats(_: None = Depends(_require_api_key)) -> dict:
    return PVStore(_data_dir()).summary()


@app.post("/api/leads")
def create_lead(payload: dict) -> dict:
    email = (payload.get("email") or "").strip()
    message = (payload.get("message") or "").strip()
    if "@" not in email:
        raise HTTPException(status_code=400, detail="valid email required")
    if not message:
        raise HTTPException(status_code=400, detail="message required")
    store = LeadStore(_data_dir())
    lead = store.create(
        (payload.get("name") or "").strip(),
        (payload.get("company") or "").strip(),
        email,
        message,
        payload.get("attribution"),
    )
    return {"lead_id": lead["lead_id"], "status": "received"}


@app.get("/api/leads/{lead_id}")
def get_lead(lead_id: str, _: None = Depends(_require_api_key)) -> dict:
    store = LeadStore(_data_dir())
    try:
        return store.get(lead_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="lead not found") from exc


@app.post("/api/orders")
def create_order(request: Request, payload: dict) -> dict:
    # 무통장(계좌이체) 제품 주문 — receipt-ledger-saas Wave 1
    receipt_product = (payload.get("product") or "").strip()
    if receipt_product:
        return _create_bank_transfer_order(receipt_product, _store_code(request))
    email = (payload.get("email") or "").strip()
    product_id = payload.get("product_id") or ""
    if "@" not in email:
        raise HTTPException(status_code=400, detail="valid email required")
    if product_id not in PRODUCTS:
        raise HTTPException(status_code=400, detail="unknown product")
    product = PRODUCTS[product_id]
    # C2: 납품 파일이 없는 제품은 판매 차단
    product_file = _PRODUCTS_DIR / product["file"]
    if not product_file.exists():
        raise HTTPException(status_code=400, detail="product currently unavailable")
    payment_mode = _payment_mode()
    store = OrderStore(_data_dir())
    order = store.create(
        email,
        product_id,
        payload.get("attribution"),
        payment_method=PaymentMethod(payment_mode.value),
    )
    match payment_mode:
        case PaymentMode.BTC:
            return order
        case PaymentMode.STRIPE:
            public_url = os.environ.get("COMPLYLENS_PUBLIC_URL", "https://html.npopo.com").rstrip("/")
            success_url = os.environ.get(
                "STRIPE_SUCCESS_URL",
                f"{public_url}/pricing.html?payment=success&order_id={order['order_id']}",
            )
            cancel_url = os.environ.get(
                "STRIPE_CANCEL_URL",
                f"{public_url}/pricing.html?payment=cancel&order_id={order['order_id']}",
            )
            try:
                checkout = create_product_checkout_session(
                    order_id=order["order_id"],
                    product_id=product_id,
                    product_name=product["name"],
                    amount_usd=product["price_usd"],
                    customer_email=email,
                    success_url=success_url,
                    cancel_url=cancel_url,
                )
                order = store.attach_stripe_session(order["order_id"], checkout["session_id"])
            except StripeConfigurationError as exc:
                store.fail_checkout(order["order_id"], "Stripe payment is not configured")
                raise HTTPException(status_code=503, detail=str(exc)) from exc
            except stripe.error.StripeError as exc:
                store.fail_checkout(order["order_id"], "Stripe Checkout unavailable")
                raise HTTPException(status_code=502, detail="Stripe Checkout unavailable") from exc
            except PaymentConflict as exc:
                store.fail_checkout(order["order_id"], str(exc))
                raise HTTPException(status_code=502, detail="Stripe Checkout unavailable") from exc
            return {**order, **checkout}
        case unreachable:
            assert_never(unreachable)


@app.get("/api/payment-mode")
def get_payment_mode() -> dict[str, str]:
    return {"payment_method": _payment_mode().value}


@app.post("/api/stripe/webhook")
async def stripe_webhook(request: Request) -> dict[str, str]:
    if _payment_mode() is not PaymentMode.STRIPE:
        raise HTTPException(status_code=404, detail="Stripe payment is disabled")
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    signature = request.headers.get("stripe-signature")
    if not secret:
        raise HTTPException(status_code=503, detail="Stripe webhook is not configured")
    if not signature:
        raise HTTPException(status_code=400, detail="missing Stripe signature")
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(payload, signature, secret)
    except (ValueError, stripe.error.SignatureVerificationError) as exc:
        raise HTTPException(status_code=400, detail="invalid Stripe webhook") from exc
    if event["type"] != "checkout.session.completed":
        return {"status": "ignored"}
    session = event["data"]["object"]
    metadata = session.get("metadata") or {}
    order_id = metadata.get("order_id")
    session_id = session.get("id")
    product_id = metadata.get("product_id")
    event_id = event.get("id")
    if not isinstance(order_id, str) or not order_id:
        raise HTTPException(status_code=400, detail="Stripe session order_id is missing")
    if not isinstance(session_id, str) or not session_id:
        raise HTTPException(status_code=400, detail="Stripe session ID is missing")
    if not isinstance(product_id, str) or not product_id:
        raise HTTPException(status_code=400, detail="Stripe session product_id is missing")
    if not isinstance(event_id, str) or not event_id:
        raise HTTPException(status_code=400, detail="Stripe event ID is missing")
    if session.get("payment_status") != "paid":
        raise HTTPException(status_code=402, detail="Stripe payment is not complete")
    if session.get("currency") != "usd":
        raise HTTPException(status_code=402, detail="Stripe currency does not match order")
    store = OrderStore(_data_dir())
    try:
        order = store.get(order_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="order not found") from exc
    if order["product_id"] != product_id:
        raise HTTPException(status_code=400, detail="Stripe product does not match order")
    if order["payment_method"] != PaymentMethod.STRIPE.value:
        raise HTTPException(status_code=400, detail="Stripe session does not match payment method")
    product = PRODUCTS[product_id]
    if session.get("amount_total") != product["price_usd"] * 100:
        raise HTTPException(status_code=402, detail="Stripe amount does not match order")
    try:
        store.confirm_stripe(order_id, session_id, event_id)
    except PaymentConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"order_id": order_id, "status": "confirmed"}


@app.post("/api/orders/{order_id}/confirm")
def confirm_order(order_id: str, payload: dict) -> dict:
    store = OrderStore(_data_dir())
    try:
        order = store.get(order_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="order not found") from exc
    if order["payment_method"] != PaymentMethod.BTC.value:
        raise HTTPException(status_code=409, detail="Stripe orders require Checkout confirmation")
    if order["status"] == "confirmed":
        return {"order_id": order_id, "status": "confirmed"}
    txid = (payload.get("txid") or "").strip()
    # C3: txid 1회용 — 전역 중복 거부
    if store.txid_used(txid, exclude_order_id=order_id):
        raise HTTPException(status_code=409, detail="txid already used for another order")
    if not verify_btc_payment(txid, order["btc_address"], order["amount_sat"]):
        raise HTTPException(status_code=402, detail="payment not verified")
    try:
        store.confirm(order_id, txid)
    except PaymentConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"order_id": order_id, "status": "confirmed"}


@app.get("/api/orders/{order_id}/download", response_class=HTMLResponse)
def download_product(order_id: str) -> str:
    store = OrderStore(_data_dir())
    try:
        order = store.get(order_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="order not found") from exc
    if order["status"] != "confirmed":
        raise HTTPException(status_code=403, detail="payment not confirmed")
    product = PRODUCTS[order["product_id"]]
    file = _PRODUCTS_DIR / product["file"]
    if not file.exists():
        raise HTTPException(status_code=404, detail="product file missing")
    return file.read_text(encoding="utf-8")


# ─ 영수증/장부 (receipt-ledger-saas Wave 1) ------------------------------------

_RECEIPT_MAX_BYTES: Final = 10 * 1024 * 1024
_IMAGE_CONTENT_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
_MONTH_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
# G4: 월 영수증 업로드 한도 (테스트에서 RECEIPT_MONTHLY_UPLOAD_LIMIT로 축소 가능)
def _receipt_monthly_limit() -> int:
    """G4: 월 영수증 업로드 한도 — 요청 시점에 읽어 재시작 없이 조절 가능.

    유료(confirmed 주문) 사용자 기준. 기본 200장,
    RECEIPT_MONTHLY_UPLOAD_LIMIT 환경변수로 재정의 (테스트 축소용).
    """
    raw = os.environ.get("RECEIPT_MONTHLY_UPLOAD_LIMIT", "").strip()
    if raw.isdigit():
        return int(raw)
    return 200


def _receipt_free_monthly_limit() -> int:
    """무료 티어 월 업로드 한도 — 기본 5장, RECEIPT_FREE_MONTHLY_LIMIT로 조절.

    캐시노트식 '무료 습관 → 유료 전환' 진입점 (monetization 축 A1).
    무료 사용자는 내보내기·무제한 업로드가 잠기고, 한도 도달 시 결제를 유도한다.
    """
    raw = os.environ.get("RECEIPT_FREE_MONTHLY_LIMIT", "").strip()
    if raw.isdigit():
        return int(raw)
    return 5


def _looks_like_image(content: bytes) -> bool:
    return content.startswith(
        (b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff", b"GIF87a", b"GIF89a")
    ) or (len(content) > 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP")


def _receipt_pipeline(namespace: str = "default") -> ReceiptPipeline:
    # G5: OCR 원본 이미지를 data/receipt-images/{store}/에 보관 (증빙 보존)
    return ReceiptPipeline(
        _data_dir(),
        namespace=namespace,
        images_dir=_data_dir() / "receipt-images",
    )


def _has_active_subscription(namespace: str) -> bool:
    """G4: confirmed/completed 무통장 주문 보유 여부 — 내보내기 게이트."""
    orders = BankTransferOrderStore(_data_dir()).list()
    return any(
        order.get("store_code") == namespace
        and order.get("status") in ("confirmed", "completed")
        for order in orders
    )


_STORE_CODE_PATTERN = re.compile(r"^[A-Za-z0-9]{1,16}$")


def _store_code(request: Request) -> str:
    """X-Store-Code 헤더를 검증한다 — 없거나 형식이 잘못되면 400."""
    code = (request.headers.get("X-Store-Code") or "").strip()
    if not _STORE_CODE_PATTERN.fullmatch(code):
        raise HTTPException(
            status_code=400,
            detail="X-Store-Code header required (1~16자 영숫자 가게 코드)",
        )
    return code


def _require_pin(request: Request, namespace: str) -> None:
    """가게 코드 PIN 검증 — 없으면 428, 실패 403, 5회 실패 잠금 429."""
    pin = (request.headers.get("X-Store-Pin") or "").strip()
    if not pin:
        raise HTTPException(status_code=400, detail="X-Store-Pin header required")
    ok, reason = LedgerStore(_data_dir(), namespace=namespace).verify_pin(pin)
    if not ok:
        if reason == "pin_not_set":
            raise HTTPException(
                status_code=428,
                detail="가게 코드에 PIN이 설정되지 않았습니다 — POST /api/store 로 PIN을 설정해 주세요.",
            )
        if reason == "locked":
            raise HTTPException(
                status_code=429,
                detail="PIN 실패가 5회 누적되어 10분간 잠겼습니다.",
            )
        raise HTTPException(status_code=403, detail="가게 코드 PIN이 올바르지 않습니다.")


def _current_month() -> str:
    return datetime.now(UTC).strftime("%Y-%m")


# T4: 기장의무 판정 — 소득세법 시행령 제208조 (업종군별 복식/기준경비율 기준)
# 가군(도소매·부동산매매 등) / 나군(제조·음식점·운수 등) / 다군(부동산임대·서비스 등)
_JUDGMENT_TABLE: Final[dict[str, dict[str, int]]] = {
    "가": {"complex": 300_000_000, "standard_ratio": 60_000_000},
    "나": {"complex": 150_000_000, "standard_ratio": 36_000_000},
    "다": {"complex": 75_000_000, "standard_ratio": 24_000_000},
}
_JUDGMENT_GROUP_DESC: Final[dict[str, str]] = {
    "가": "도소매·부동산매매 등",
    "나": "제조·음식점·운수 등",
    "다": "부동산임대·서비스·교육 등",
}


@app.post("/api/ledger-judgment")
def ledger_judgment(payload: dict) -> dict:
    """기장의무 판정 (T4) — 소득세법 시행령 제208조 기준.

    업종군 + 직전연도 수입금액으로 복식부기/간편장부(기준·단순경비율)를 판정한다.
    전문직은 수입금액 무관 복식부기, 당해연도 신규 개업은 간편장부.
    판정은 안내용이며 과세당국의 개별 판단을 대체하지 않는다.
    """
    group = str(payload.get("industry_group") or "").strip()
    if group not in _JUDGMENT_TABLE:
        raise HTTPException(status_code=400, detail="industry_group must be 가/나/다")
    try:
        revenue = to_price(payload.get("revenue"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="revenue must be a non-negative amount") from exc
    if revenue is None or revenue < 0:
        raise HTTPException(status_code=400, detail="revenue must be a non-negative amount")
    professional = bool(payload.get("professional"))
    new_business = bool(payload.get("new_business"))
    thresholds = _JUDGMENT_TABLE[group]
    group_desc = _JUDGMENT_GROUP_DESC[group]
    if professional:
        obligation, reason = (
            "복식부기",
            "전문직(변호사·의사 등)은 수입금액과 관계없이 복식부기 의무자입니다.",
        )
    elif new_business:
        obligation, reason = (
            "간편장부",
            "당해연도 신규 개업자는 간편장부 대상자입니다.",
        )
    elif revenue >= thresholds["complex"]:
        obligation, reason = (
            "복식부기",
            f"{group}군({group_desc}) 복식부기 기준(연 {thresholds['complex']:,}원) 이상입니다.",
        )
    elif revenue >= thresholds["standard_ratio"]:
        obligation, reason = (
            "간편장부",
            f"{group}군({group_desc}) — 연 {thresholds['standard_ratio']:,}원 이상으로 기준경비율 적용 대상입니다.",
        )
    else:
        obligation, reason = (
            "간편장부",
            f"{group}군({group_desc}) — 연 {thresholds['standard_ratio']:,}원 미만으로 단순경비율 적용 대상입니다.",
        )
    return {
        "obligation": obligation,
        "reason": reason,
        "kang": group,
        "revenue": revenue,
        "professional": professional,
        "new_business": new_business,
    }


def _validate_month(month: str) -> str:
    if not _MONTH_PATTERN.match(month):
        raise HTTPException(status_code=400, detail="month must be YYYY-MM")
    return month


@app.post("/api/store")
def setup_store_pin(request: Request, payload: dict) -> dict:
    """가게 코드에 PIN 설정/변경 — 첫 실행 시 필수 (B2 보안).

    G3: PIN 변경은 기존 PIN(current_pin) 검증을 통과해야 한다 —
    가게 코드만 아는 공격자가 PIN을 덮어쓰는 것을 차단한다.
    """
    namespace = _store_code(request)
    pin = str(payload.get("pin") or "").strip()
    if not pin:
        raise HTTPException(status_code=400, detail="pin required")
    store = LedgerStore(_data_dir(), namespace=namespace)
    if store.has_pin():
        current = str(payload.get("current_pin") or "").strip()
        if not current:
            raise HTTPException(
                status_code=400,
                detail="current_pin required — PIN을 변경하려면 기존 PIN을 함께 보내야 합니다",
            )
        ok, reason = store.verify_pin(current)
        if not ok:
            if reason == "locked":
                raise HTTPException(
                    status_code=429, detail="PIN 실패가 5회 누적되어 10분간 잠겼습니다."
                )
            raise HTTPException(status_code=403, detail="기존 PIN이 올바르지 않습니다.")
    try:
        store.set_pin(pin)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"store_code": namespace, "pin_set": True}


@app.post("/api/entries")
def create_entry(request: Request, payload: dict) -> dict:
    """수동 장부 기록 — 수입(income)/지출(expense) 등록 (P2)."""
    namespace = _store_code(request)
    _require_pin(request, namespace)
    kind = str(payload.get("kind") or "expense")
    if kind not in ("income", "expense"):
        raise HTTPException(status_code=400, detail="kind must be income or expense")
    category = str(payload.get("category") or "").strip()
    if category not in ACCOUNT_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"unknown category: {category}")
    amount = to_price(payload.get("amount"))
    if amount is None or amount <= 0:
        raise HTTPException(status_code=400, detail="amount must be a valid positive amount")
    store_name = str(payload.get("store") or "").strip()
    if not store_name:
        raise HTTPException(status_code=400, detail="store required")
    date = str(payload.get("date") or "").strip()
    note = str(payload.get("note") or "").strip()
    entry = LedgerStore(_data_dir(), namespace=namespace).save(
        {
            "kind": kind,
            "store": store_name,
            "category": category,
            "amount": amount,
            "total": amount,
            "date": date or None,
            "note": note,
            "source": "manual",
        }
    )
    return entry


@app.delete("/api/entries/{entry_id}")
def delete_entry(request: Request, entry_id: str) -> dict:
    """장부 거래 삭제 (P2)."""
    namespace = _store_code(request)
    _require_pin(request, namespace)
    try:
        LedgerStore(_data_dir(), namespace=namespace).delete(entry_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="entry not found") from exc
    return {"deleted": entry_id}


@app.patch("/api/entries/{entry_id}")
def update_entry(request: Request, entry_id: str, payload: dict) -> dict:
    """장부 거래 수정 (T3 — 무료 티어 장부 고도화).

    카테고리/금액/품목/날짜를 수정한다. OCR로 들어온 영수증 거래(ocr_model 존재)가
    카테고리를 바꾸면 few-shot 샘플을 저장해 다음 같은 가게 인식에 반영한다
    (촬영 카드 수정과 동일한 학습 루프). 수동 등록(수입 등)은 학습에서 제외.
    """
    namespace = _store_code(request)
    _require_pin(request, namespace)
    store = LedgerStore(_data_dir(), namespace=namespace)
    try:
        current = store.get(entry_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="entry not found") from exc
    changes: dict = {}
    if "category" in payload:
        category = str(payload["category"] or "").strip()
        if category not in ACCOUNT_CATEGORIES:
            raise HTTPException(status_code=400, detail=f"unknown category: {category}")
        changes["category"] = category
    if "total" in payload:
        total = to_price(payload["total"])
        if total is None or total <= 0:
            raise HTTPException(status_code=400, detail="total must be a valid positive amount")
        changes["total"] = total
    if "date" in payload:
        date = str(payload["date"] or "").strip()
        if not date:
            raise HTTPException(status_code=400, detail="date cannot be empty")
        changes["date"] = date[:32]
    if "items" in payload:
        if not isinstance(payload["items"], list):
            raise HTTPException(status_code=400, detail="items must be a list")
        items: list[dict] = []
        for item in payload["items"]:
            name = str((item or {}).get("name") or "").strip() if isinstance(item, dict) else ""
            price = to_price((item or {}).get("price") if isinstance(item, dict) else None)
            if name and price is not None and price > 0:
                items.append({"name": name, "price": price})
        changes["items"] = items
    if not changes:
        raise HTTPException(status_code=400, detail="no changes provided")
    updated = store.update(entry_id, changes)
    # few-shot: OCR 영수증 + 카테고리 실제 변경일 때만 학습 샘플 저장
    if (
        current.get("ocr_model")
        and changes.get("category")
        and changes["category"] != current.get("category")
    ):
        store.record_correction(
            entry_id,
            original={
                "store": current.get("store", ""),
                "category": current.get("category", "기타"),
            },
            corrected={"category": changes["category"]},
        )
    return {"entry_id": entry_id, "updated": updated}


@app.post("/api/receipts")
def create_receipt(request: Request, file: UploadFile = File(...)) -> dict:  # noqa: B008
    namespace = _store_code(request)
    _require_pin(request, namespace)
    if file is None:
        raise HTTPException(status_code=400, detail="image file is required")
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type not in _IMAGE_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="image file required (png/jpeg/webp/gif)")
    content = file.file.read(_RECEIPT_MAX_BYTES + 1)
    if not content:
        raise HTTPException(status_code=400, detail="empty upload")
    if len(content) > _RECEIPT_MAX_BYTES:
        raise HTTPException(status_code=413, detail="image exceeds the 10 MB limit")
    if not _looks_like_image(content):
        raise HTTPException(status_code=400, detail="file content is not a readable image")
    # G4/A1: 월 업로드 한도 — 구독 여부에 따라 무료 5장 / 유료 200장
    store = LedgerStore(_data_dir(), namespace=namespace)
    month_count = store.count_uploads_in_month(_current_month())
    if _has_active_subscription(namespace):
        limit = _receipt_monthly_limit()
        if month_count >= limit:
            raise HTTPException(
                status_code=402,
                detail=f"이번 달 영수증 {limit}장 한도에 도달했습니다 — 더 필요하면 지원팀에 문의하세요.",
            )
    else:
        free_limit = _receipt_free_monthly_limit()
        if month_count >= free_limit:
            raise HTTPException(
                status_code=402,
                detail=f"무료 티어는 월 {free_limit}장까지 이용할 수 있습니다. 앱의 결제 안내에서 입금 확인을 하면 월 {_receipt_monthly_limit()}장으로 확대됩니다.",
            )
    # G2: 이미지 해시 멱등성 — 타임아웃 후 재업로드·오프라인 큐 재전송 시 중복 기록 차단
    image_sha256 = hashlib.sha256(content).hexdigest()
    try:
        return _receipt_pipeline(namespace).process(
            content, content_type, image_sha256=image_sha256
        )
    except OCRUnavailableError as exc:
        raise HTTPException(status_code=422, detail=f"OCR 처리에 실패했습니다: {exc}") from exc


@app.post("/api/events")
def track_event(request: Request, payload: dict) -> dict:
    """G7: 클라이언트 이벤트 계측 — data/events/{store}/{yyyymm}.jsonl 누적.

    fire-and-forget 로깅용. 이벤트는 제품 사용 데이터로, OCR 원본과 분리되어
    개인정보(영수증 이미지)를 담지 않는다. 실패해도 요청 흐름을 막지 않는다.
    """
    namespace = _store_code(request)
    _require_pin(request, namespace)
    event = str(payload.get("event") or "").strip()
    if not event:
        raise HTTPException(status_code=400, detail="event required")
    meta = payload.get("meta") or {}
    if not isinstance(meta, dict):
        raise HTTPException(status_code=400, detail="meta must be an object")
    ev_dir = _data_dir() / "events" / namespace
    ev_dir.mkdir(parents=True, exist_ok=True)
    line = {"ts": datetime.now(UTC).isoformat(), "event": event, "meta": meta}
    with (ev_dir / f"{_current_month()}.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(line, ensure_ascii=False) + "\n")
    return {"ok": True, "event": event}


@app.patch("/api/receipts/{receipt_id}/correct")
def correct_receipt(request: Request, receipt_id: str, payload: dict) -> dict:
    namespace = _store_code(request)
    _require_pin(request, namespace)
    if not payload:
        raise HTTPException(status_code=400, detail="correction payload required")
    pipeline = _receipt_pipeline(namespace)
    try:
        updated = pipeline.correct(receipt_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="receipt not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "receipt_id": updated["receipt_id"],
        "store": updated["store"],
        "date": updated["date"],
        "items": updated["items"],
        "total": updated["total"],
        "vat": updated["vat"],
        "payment": updated["payment"],
        "category": updated["category"],
        "category_source": updated["category_source"],
        "needs_review": updated["needs_review"],
        "warnings": updated["warnings"],
        "corrected": True,
    }


@app.get("/api/ledger")
def ledger_report(request: Request, month: str | None = None) -> dict:
    namespace = _store_code(request)
    _require_pin(request, namespace)
    month = _validate_month(month or _current_month())
    store = LedgerStore(_data_dir(), namespace=namespace)
    report = store.monthly_report(month)
    # P1: 전월 비교 — prev_expense/prev_profit (비교할 데이터 없으면 0)
    year, mon = (int(part) for part in month.split("-"))
    if mon == 1:
        prev_month = f"{year - 1}-12"
    else:
        prev_month = f"{year:04d}-{mon - 1:02d}"
    prev = store.monthly_report(prev_month)
    report["prev_expense"] = prev["expense"]
    report["prev_profit"] = prev["profit"]
    return {**report, "entries": store.list_entries(month)}


@app.get("/api/export")
def export_ledger(request: Request, month: str | None = None, format: str = "csv") -> Response:
    namespace = _store_code(request)
    _require_pin(request, namespace)
    # G4: 내보내기(신고 준비 파일)는 유료 구독 기능 — confirmed/completed 주문 필요
    if not _has_active_subscription(namespace):
        raise HTTPException(
            status_code=402,
            detail="내보내기는 유료 구독 기능입니다 — 앱에서 결제(입금 확인) 후 이용하세요.",
        )
    month = _validate_month(month or _current_month())
    entries = LedgerStore(_data_dir(), namespace=namespace).list_entries(month)
    if format == "csv":
        content = entries_to_csv(entries)
        media_type = "text/csv; charset=utf-8"
        filename = f"receipt-ledger-{month}.csv"
    elif format in ("excel", "xlsx"):
        content = entries_to_xlsx(entries)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"receipt-ledger-{month}.xlsx"
    else:
        raise HTTPException(status_code=400, detail="format must be csv or excel")
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─ 무통장(계좌이체) 주문 — 입금 안내 + 사용자 확인 상태머신 ----------------------

def _bank_guidance(order: dict) -> str:
    bank = order["bank_account"]
    return (
        f"{order['description']} {order['amount_krw']:,}원을 "
        f"{bank['bank']} {bank['account_number']} ({bank['holder']}) 계좌로 입금해 주세요. "
        f'입금 후 PATCH /api/orders/{order["id"]} {{"action": "confirm"}} 로 '
        "입금을 확인하면 구독이 시작됩니다."
    )


def _create_bank_transfer_order(product_id: str, namespace: str) -> dict:
    if product_id not in BANK_TRANSFER_PRODUCTS:
        raise HTTPException(status_code=400, detail="unknown product")
    product = BANK_TRANSFER_PRODUCTS[product_id]
    store = BankTransferOrderStore(_data_dir())
    order = store.create(
        amount=product_amount_krw(product_id),
        description=product["name"],
        status="created",
        store_code=namespace,
    )
    order = store.transition(order["id"], "awaiting_payment")
    return {
        "order_id": order["id"],
        "product_id": product_id,
        "product_name": product["name"],
        "status": order["status"],
        "amount_krw": order["amount_krw"],
        "bank": order["bank_account"],
        "instructions": _bank_guidance(order),
        "transitions": ["created", "awaiting_payment", "confirmed", "completed"],
    }


@app.patch("/api/orders/{order_id}")
def update_bank_transfer_order(order_id: str, payload: dict) -> dict:
    action = payload.get("action")
    if action not in ("confirm", "complete"):
        raise HTTPException(status_code=400, detail="action must be confirm or complete")
    store = BankTransferOrderStore(_data_dir())
    try:
        if action == "confirm":
            order = store.transition(order_id, "confirmed")
        else:
            order = store.transition(order_id, "completed")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="order not found") from exc
    except BankTransferInvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "order_id": order_id,
        "status": order["status"],
    }


# C1: 제품 파일은 StaticFiles 마운트 밖 (web/products/) — 무결제 접근 차단
_PRODUCTS_DIR = Path(__file__).parent / "products"


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "frame-ancestors 'none'"
    )
    return response


_STATIC_DIR = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="static")
