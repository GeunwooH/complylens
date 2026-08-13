/**
 * 백엔드 API 클라이언트 — fetch 기반, 실패 시 한국어 오류 메시지 반환.
 * 모든 함수는 성공 시 파싱된 객체, 실패 시 Error(한국어 메시지)를 throw.
 */
import { API_BASE_URL } from "./config";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { Platform } from "react-native";
import { File as FSFile } from "expo-file-system";
import {
  BankOrder,
  ExportResponse,
  LedgerReport,
  ReceiptCard,
  parseBankOrder,
  parseLedgerReport,
  parseReceiptCard,
  toNum,
} from "./types";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

/** D2: 요청 타임아웃(15초) 전용 오류 — toKoreanError가 한국어 메시지로 변환. */
export class TimeoutError extends Error {
  constructor() {
    super("요청 시간이 초과되었습니다.");
    this.name = "TimeoutError";
  }
}

/** fetch + 15초 타임아웃 (AbortController) — 네트워크 지연 시 한국어 오류 유도. */
const REQUEST_TIMEOUT_MS = 15000;

export async function fetchWithTimeout(
  url: string,
  init?: RequestInit,
  timeoutMs: number = REQUEST_TIMEOUT_MS
): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } catch (e) {
    if (e instanceof Error && e.name === "AbortError") {
      throw new TimeoutError();
    }
    throw e;
  } finally {
    clearTimeout(timer);
  }
}

/* ── D1: 오프라인 업로드 대기열 (AsyncStorage) ────────────────── */

const UPLOAD_QUEUE_KEY = "receipt-app:upload-queue:v1";

export interface QueuedUpload {
  uri: string;
  name: string;
  type: string;
  queuedAt: string;
}

/** 오프라인 상태인지 — fetch TypeError(네트워크) 또는 타임아웃. */
export function isOfflineError(e: unknown): boolean {
  if (e instanceof TimeoutError) return true;
  if (e instanceof TypeError) return true; // fetch 네트워크 실패
  return false;
}

export async function loadUploadQueue(): Promise<QueuedUpload[]> {
  try {
    const raw = await AsyncStorage.getItem(UPLOAD_QUEUE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (q): q is QueuedUpload =>
        typeof q === "object" && q !== null && typeof (q as QueuedUpload).uri === "string"
    );
  } catch {
    return [];
  }
}

export async function enqueueUpload(
  source: UploadSource
): Promise<QueuedUpload[]> {
  const queue = await loadUploadQueue();
  const item: QueuedUpload = {
    uri: source.uri,
    name: source.name,
    type: source.type,
    queuedAt: new Date().toISOString(),
  };
  const next = [...queue, item];
  await AsyncStorage.setItem(UPLOAD_QUEUE_KEY, JSON.stringify(next));
  return next;
}

export async function removeFromQueue(queuedAt: string): Promise<void> {
  const queue = await loadUploadQueue();
  await AsyncStorage.setItem(
    UPLOAD_QUEUE_KEY,
    JSON.stringify(queue.filter((q) => q.queuedAt !== queuedAt))
  );
}

/** 대기열 재시도 — 오프라인이면 중단, 성공한 항목은 제거. */
export async function flushUploadQueue(): Promise<{
  uploaded: number;
  pending: number;
}> {
  const queue = await loadUploadQueue();
  let uploaded = 0;
  for (const item of [...queue]) {
    try {
      await uploadReceipt(item);
      uploaded += 1;
      await removeFromQueue(item.queuedAt);
    } catch (e) {
      if (isOfflineError(e)) break; // 아직 오프라인 — 나머지는 다음 기회에
      await removeFromQueue(item.queuedAt); // 영구 실패 항목은 제거
    }
  }
  const remaining = await loadUploadQueue();
  return { uploaded, pending: remaining.length };
}

/* ── 다중 사용자: 가게 코드(namespace) 헤더 (A4/A5) ───────────── */

let _storeCode = "";
let _storePin = "";

/** 온보딩에서 설정한 가게 코드를 주입한다 — 모든 API 호출에 X-Store-Code 헤더로 전달. */
export function setStoreCode(code: string): void {
  _storeCode = code.trim();
}

/** 가게 코드 잠금 PIN — 모든 장부 API에 X-Store-Pin 헤더로 전달. */
export function setStorePin(pin: string): void {
  _storePin = pin.trim();
}

function _headers(extra?: Record<string, string>): Record<string, string> {
  return { "X-Store-Code": _storeCode, "X-Store-Pin": _storePin, ...extra };
}

async function readDetail(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // JSON 아님 — 본문 생략
  }
  return "";
}

/** 응답을 한국어 오류 메시지로 변환 (offline/500/4xx 모두) */
export async function toKoreanError(e: unknown): Promise<string> {
  if (e instanceof TimeoutError) return e.message;
  if (e instanceof ApiError) return e.message;
  if (e instanceof TypeError) {
    return "서버에 연결할 수 없습니다. 네트워크나 서버 상태를 확인해 주세요.";
  }
  if (e instanceof Error && e.message) return e.message;
  return "알 수 없는 오류가 발생했습니다.";
}

async function ensureStatus(res: Response, fallback: string): Promise<void> {
  if (res.ok) return;
  const detail = await readDetail(res);
  let message = fallback;
  if (res.status >= 500) {
    message = "서버에 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.";
  } else if (detail) {
    // 402(결제/한도)는 서버 안내 문구를 그대로 — '요청에 실패했습니다' 접두어 제거
    message = res.status === 402 ? detail : `요청에 실패했습니다: ${detail}`;
  }
  throw new ApiError(res.status, message);
}

/**
 * API 호출 래퍼 — 428(PIN 미설정) 응답 시 저장된 PIN으로 자동 등록 후 재시도.
 * 시작 시 자동 등록이 실패했더라도 첫 API 호출에서 복구되어 428을 보지 않는다.
 */
async function apiFetch(
  url: string,
  init?: RequestInit,
  timeoutMs?: number
): Promise<Response> {
  let res = await fetchWithTimeout(url, init, timeoutMs);
  if (res.status === 428 && _storeCode && _storePin) {
    try {
      await setupStorePin(_storeCode, _storePin);
      res = await fetchWithTimeout(url, init, timeoutMs);
    } catch {
      // 자동 등록 실패 — 원래 응답을 그대로 전달해 사용자에게 표시
    }
  }
  return res;
}

/* ── W2-2: 업로드 → OCR 카드 ───────────────────────────────── */

export interface UploadSource {
  uri: string; // 로컬 파일 uri (file://) 또는 web의 data/blob uri
  name: string;
  type: string; // mime type
}

export async function uploadReceipt(source: UploadSource): Promise<ReceiptCard> {
  const form = new FormData();
  if (Platform.OS === "web") {
    // 웹: 전역 File/Blob 사용 (expo-file-system은 웹 미지원)
    const resp = await fetchWithTimeout(source.uri);
    const blob = await resp.blob();
    form.append("file", new File([blob], source.name, { type: source.type }));
  } else {
    // 네이티브: expo-file-system File — expo/fetch convertFormData가 bytes()로 처리
    form.append("file", new FSFile(source.uri) as unknown as Blob);
  }

  const res = await apiFetch(`${API_BASE_URL}/api/receipts`, {
    method: "POST",
    headers: _headers(),
    body: form,
  });
  await ensureStatus(res, "영수증을 처리하지 못했습니다.");
  return parseReceiptCard(await res.json());
}

/* ── W2-3: 1클릭 수정 → PATCH ──────────────────────────────── */

export interface CorrectionPayload {
  category: string;
  items: { name: string; price: number | string }[];
  total: number | string;
}

export async function correctReceipt(
  receiptId: string,
  payload: CorrectionPayload
): Promise<ReceiptCard> {
  const res = await apiFetch(
    `${API_BASE_URL}/api/receipts/${receiptId}/correct`,
    {
      method: "PATCH",
      headers: _headers({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
    }
  );
  await ensureStatus(res, "수정 내용을 저장하지 못했습니다.");
  return parseReceiptCard(await res.json());
}

/* ── W2-4: 월간 장부 리포트 ────────────────────────────────── */

export async function fetchLedger(month: string): Promise<LedgerReport> {
  const res = await apiFetch(
    `${API_BASE_URL}/api/ledger?month=${encodeURIComponent(month)}`,
    { headers: _headers() }
  );
  await ensureStatus(res, "장부를 불러오지 못했습니다.");
  return parseLedgerReport(await res.json());
}

/* ── W2-5: 내보내기 + 무통장 ───────────────────────────────── */

export async function fetchExport(
  month: string,
  format: "csv" | "excel"
): Promise<ExportResponse> {
  const res = await apiFetch(
    `${API_BASE_URL}/api/export?month=${encodeURIComponent(month)}&format=${format}`,
    { headers: _headers() }
  );
  await ensureStatus(res, "파일을 내보내지 못했습니다.");
  const disposition = res.headers.get("content-disposition") ?? "";
  const match = disposition.match(/filename="?([^";]+)"?/);
  const filename =
    match?.[1] ?? `receipt-ledger-${month}.${format === "csv" ? "csv" : "xlsx"}`;
  return {
    filename,
    mimeType: res.headers.get("content-type") ?? "application/octet-stream",
    bytes: await res.arrayBuffer(),
  };
}

export async function createBankOrder(): Promise<BankOrder> {
  const res = await apiFetch(`${API_BASE_URL}/api/orders`, {
    method: "POST",
    headers: _headers({ "Content-Type": "application/json" }),
    body: JSON.stringify({ product: "receipt-ledger-lite" }),
  });
  await ensureStatus(res, "입금 안내를 생성하지 못했습니다.");
  return parseBankOrder(await res.json());
}

export async function confirmBankOrder(orderId: string): Promise<string> {
  const res = await apiFetch(`${API_BASE_URL}/api/orders/${orderId}`, {
    method: "PATCH",
    headers: _headers({ "Content-Type": "application/json" }),
    body: JSON.stringify({ action: "confirm" }),
  });
  await ensureStatus(res, "입금 확인을 처리하지 못했습니다.");
  const body = (await res.json()) as { status?: unknown };
  return typeof body.status === "string" ? body.status : "unknown";
}

export { toNum };
/* ── P2: 수동 장부 기록(수입/지출) + 삭제 ─────────────────────── */

export interface NewEntryPayload {
  store: string;
  category: string;
  amount: string | number;
  date?: string;
  kind: "income" | "expense";
  note?: string;
}

export async function createEntry(payload: NewEntryPayload): Promise<unknown> {
  const res = await apiFetch(`${API_BASE_URL}/api/entries`, {
    method: "POST",
    headers: _headers({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
  });
  await ensureStatus(res, "장부 기록을 저장하지 못했습니다.");
  return res.json();
}

export async function deleteEntry(entryId: string): Promise<void> {
  const res = await apiFetch(`${API_BASE_URL}/api/entries/${entryId}`, {
    method: "DELETE",
    headers: _headers(),
  });
  await ensureStatus(res, "장부 기록을 삭제하지 못했습니다.");
}

/* ── T3: 장부 거래 수정 (무료 티어 장부 고도화) ────────────────── */

export interface UpdateEntryPayload {
  category?: string;
  total?: number | string;
  date?: string;
}

export async function updateEntry(
  entryId: string,
  payload: UpdateEntryPayload
): Promise<unknown> {
  const res = await apiFetch(`${API_BASE_URL}/api/entries/${entryId}`, {
    method: "PATCH",
    headers: _headers({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
  });
  await ensureStatus(res, "장부 기록을 수정하지 못했습니다.");
  return res.json();
}

/* ── 온보딩: 가게 코드 PIN 등록 (백엔드 필수) ─────────────────── */

export async function setupStorePin(code: string, pin: string): Promise<void> {
  const res = await fetchWithTimeout(`${API_BASE_URL}/api/store`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Store-Code": code.trim() },
    body: JSON.stringify({ pin }),
  });
  await ensureStatus(res, "PIN 설정에 실패했습니다.");
}

/* ── P0-G7: 이벤트 계측 (fire-and-forget) ─────────────────────── */

/**
 * 제품 사용 이벤트를 서버에 기록한다 (POST /api/events).
 * 업로드/수정/내보내기/결제 진입/입금 확인/앱 재방문.
 * 계측 실패는 사용자 흐름을 절대 막지 않는다 — 실패는 조용히 무시.
 */
export async function trackEvent(
  event: string,
  meta?: Record<string, unknown>
): Promise<void> {
  try {
    const res = await apiFetch(`${API_BASE_URL}/api/events`, {
      method: "POST",
      headers: _headers({ "Content-Type": "application/json" }),
      body: JSON.stringify({ event, meta: meta ?? {} }),
    });
    if (!res.ok) {
      // 계측 실패는 로그 없이 무시 (사용자 흐름 보호 우선)
    }
  } catch {
    // 네트워크/타임아웃 오류 무시
  }
}

/* ── T4: 기장의무 판정 (무료 티어 장부 고도화) ─────────────────── */

export interface JudgmentPayload {
  industry_group: string; // 가/나/다
  revenue: number | string;
  professional?: boolean;
  new_business?: boolean;
}

export interface JudgmentResult {
  obligation: string;
  reason: string;
  kang: string;
  revenue: number;
  professional: boolean;
  new_business: boolean;
}

export async function fetchJudgment(
  payload: JudgmentPayload
): Promise<JudgmentResult> {
  const res = await apiFetch(`${API_BASE_URL}/api/ledger-judgment`, {
    method: "POST",
    headers: _headers({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
  });
  await ensureStatus(res, "기장 의무를 판정하지 못했습니다.");
  return res.json();
}
