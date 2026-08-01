"""FastAPI 웹 앱 — 감사 업로드/조회/PDF/공개요약, API 키 인증."""
from __future__ import annotations

import io
import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles

from complylens.audit.core import MissingCategoryError, evaluate_audit
from complylens.llm.gateway import (
    HallucinationDetected,
    LLMGateway,
    NoProviderAvailable,
    Provider,
)
from complylens.report.builder import (
    build_detailed_report_html,
    build_notice_text,
    build_public_summary_html,
    render_pdf,
)
from complylens.web.leads import LeadStore
from complylens.web.orders import PRODUCTS, OrderStore, verify_btc_payment
from complylens.web.stats import PVStore

app = FastAPI(title="ComplyLens", version="0.1.0")

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
REQUIRED_CATEGORIES = ["male", "female"]


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
                "This audit was completed by the Complify statistical engine. "
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
    df = _parse_csv(file.file.read())
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
    record_path = _data_dir() / audit_id / "record.json"
    if not record_path.exists():
        raise HTTPException(status_code=404, detail="audit not found")
    return json.loads(record_path.read_text(encoding="utf-8"))


@app.get("/api/audits/{audit_id}")
def get_audit(audit_id: str, _: None = Depends(_require_api_key)) -> dict:
    return _load_record(audit_id)


@app.get("/api/audits/{audit_id}/report.pdf")
def download_report(audit_id: str, _: None = Depends(_require_api_key)) -> FileResponse:
    pdf = _data_dir() / audit_id / "report.pdf"
    if not pdf.exists():
        raise HTTPException(status_code=404, detail="report not found")
    return FileResponse(pdf, media_type="application/pdf", filename=f"{audit_id}-report.pdf")


@app.get("/api/audits/{audit_id}/summary", response_class=HTMLResponse)
def public_summary(audit_id: str) -> str:
    summary = _data_dir() / audit_id / "summary.html"
    if not summary.exists():
        raise HTTPException(status_code=404, detail="summary not found")
    return summary.read_text(encoding="utf-8")


@app.post("/api/pv")
def record_pageview(payload: dict) -> dict:
    path = (payload.get("path") or "").strip()
    if not path or not path.startswith("/"):
        raise HTTPException(status_code=400, detail="valid path required")
    PVStore(_data_dir()).record(path)
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
    )
    return {"lead_id": lead["lead_id"], "status": "received"}


@app.get("/api/leads/{lead_id}")
def get_lead(lead_id: str) -> dict:
    store = LeadStore(_data_dir())
    try:
        return store.get(lead_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="lead not found") from exc


@app.post("/api/orders")
def create_order(payload: dict) -> dict:
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
    store = OrderStore(_data_dir())
    order = store.create(email, product_id)
    return {
        "order_id": order["order_id"],
        "status": order["status"],
        "product_name": order["product_name"],
        "amount_btc": order["amount_btc"],
        "amount_sat": order["amount_sat"],
        "btc_address": order["btc_address"],
    }


@app.post("/api/orders/{order_id}/confirm")
def confirm_order(order_id: str, payload: dict) -> dict:
    store = OrderStore(_data_dir())
    try:
        order = store.get(order_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="order not found") from exc
    if order["status"] == "confirmed":
        return {"order_id": order_id, "status": "confirmed"}
    txid = (payload.get("txid") or "").strip()
    # C3: txid 1회용 — 전역 중복 거부
    if store.txid_used(txid, exclude_order_id=order_id):
        raise HTTPException(status_code=409, detail="txid already used for another order")
    if not verify_btc_payment(txid, order["btc_address"], order["amount_sat"]):
        raise HTTPException(status_code=402, detail="payment not verified")
    store.confirm(order_id, txid)
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
