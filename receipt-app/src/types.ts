/**
 * 백엔드 API 응답 타입과 방어적 파싱 헬퍼.
 * 서버 응답에 필드가 없거나 형식이 달라져도 앱이 죽지 않게 전부 기본값으로 안전하게 내린다.
 */

export interface ReceiptItem {
  name: string;
  price: number | string;
}

/** POST /api/receipts 카드 + PATCH .../correct 응답 공통 */
export interface ReceiptCard {
  receipt_id: string;
  store: string;
  date: string;
  items: ReceiptItem[];
  total: number | string;
  vat?: number | string | null;
  payment?: string | null;
  category: string;
  category_confidence?: number | null;
  category_source?: string;
  confidence?: string;
  needs_review?: boolean;
  warnings?: string[];
  corrected?: boolean;
}

export interface LedgerEntry {
  receipt_id: string;
  kind?: string;
  store?: string;
  date?: string | null;
  total?: number | string | null;
  amount?: number | string | null;
  category?: string;
  note?: string;
  items?: { name?: string; price?: number | string }[];
  needs_review?: boolean;
  unclassified?: boolean;
}

export interface LedgerReport {
  month: string;
  entry_count: number;
  revenue: number;
  expense: number;
  profit: number;
  unclassified_count: number;
  needs_review_count: number;
  category_breakdown?: Record<string, number>;
  top_stores?: [string, number][];
  prev_expense?: number;
  prev_profit?: number;
  entries: LedgerEntry[];
}

export interface BankOrder {
  order_id: string;
  product_id?: string;
  product_name?: string;
  status: string;
  amount_krw: number;
  bank: {
    bank: string;
    holder: string;
    account_number: string;
  };
  instructions: string;
  transitions?: string[];
}

export interface ExportResponse {
  filename: string;
  mimeType: string;
  bytes: ArrayBuffer;
}

/* ── 방어 파싱 ─────────────────────────────────────────────── */

function toNum(value: unknown, fallback = 0): number {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const n = Number(String(value).replace(/[^\d.-]/g, ""));
    return Number.isFinite(n) ? n : fallback;
  }
  return fallback;
}

function toStr(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

/** 백엔드 금액은 숫자 또는 "1,500" 문자열 — 동적 값 변환용 */
export { toNum };

export function parseReceiptCard(raw: unknown): ReceiptCard {
  const r = (raw ?? {}) as Record<string, unknown>;
  const rawItems = Array.isArray(r.items) ? r.items : [];
  const items: ReceiptItem[] = rawItems
    .map((it) => {
      const obj = (it ?? {}) as Record<string, unknown>;
      return { name: toStr(obj.name, "품목"), price: toNum(obj.price) };
    })
    .filter((it) => it.name.length > 0);
  return {
    receipt_id: toStr(r.receipt_id, "unknown"),
    store: toStr(r.store, "가게명 없음"),
    date: toStr(r.date, ""),
    items,
    total: toNum(r.total),
    vat: r.vat == null ? null : toNum(r.vat),
    payment: r.payment == null ? null : toStr(r.payment),
    category: toStr(r.category, "기타"),
    category_confidence: r.category_confidence == null ? null : toNum(r.category_confidence),
    category_source: toStr(r.category_source, "rule"),
    confidence: toStr(r.confidence, "high"),
    needs_review: Boolean(r.needs_review),
    warnings: Array.isArray(r.warnings)
      ? r.warnings.map((w) => String(w)).filter(Boolean)
      : [],
    corrected: Boolean(r.corrected),
  };
}

export function parseLedgerReport(raw: unknown): LedgerReport {
  const r = (raw ?? {}) as Record<string, unknown>;
  const rawEntries = Array.isArray(r.entries) ? r.entries : [];
  const entries: LedgerEntry[] = rawEntries
    .map((e) => {
      const obj = (e ?? {}) as Record<string, unknown>;
      return {
        receipt_id: toStr(obj.receipt_id, ""),
        kind: toStr(obj.kind, "expense"),
        store: toStr(obj.store, ""),
        date: obj.date == null ? null : String(obj.date),
        total: obj.total == null ? null : toNum(obj.total),
        amount: obj.amount == null ? null : toNum(obj.amount),
        category: toStr(obj.category, "기타"),
        note: toStr(obj.note, ""),
        needs_review: Boolean(obj.needs_review),
        unclassified: Boolean(obj.unclassified),
      };
    })
    .filter((e) => e.receipt_id.length > 0);
  const rawBreakdown = r.category_breakdown;
  const category_breakdown: Record<string, number> = {};
  if (rawBreakdown && typeof rawBreakdown === "object") {
    for (const [k, v] of Object.entries(rawBreakdown)) {
      category_breakdown[k] = toNum(v);
    }
  }
  const rawTop = Array.isArray(r.top_stores) ? r.top_stores : [];
  const top_stores: [string, number][] = rawTop
    .map((t) => {
      if (Array.isArray(t) && typeof t[0] === "string") {
        return [t[0], toNum(t[1])] as [string, number];
      }
      return null;
    })
    .filter((t): t is [string, number] => t !== null);
  return {
    month: toStr(r.month, ""),
    entry_count: toNum(r.entry_count),
    revenue: toNum(r.revenue),
    expense: toNum(r.expense),
    profit: toNum(r.profit),
    unclassified_count: toNum(r.unclassified_count),
    needs_review_count: toNum(r.needs_review_count),
    category_breakdown,
    top_stores,
    prev_expense: toNum(r.prev_expense, NaN),
    prev_profit: toNum(r.prev_profit, NaN),
    entries,
  };
}

export function parseBankOrder(raw: unknown): BankOrder {
  const r = (raw ?? {}) as Record<string, unknown>;
  const bank = (r.bank ?? {}) as Record<string, unknown>;
  const fallbackBank = { bank: "—", holder: "—", account_number: "—" };
  return {
    order_id: toStr(r.order_id, "unknown"),
    product_id: toStr(r.product_id, ""),
    product_name: toStr(r.product_name, "영수증 장부 Light"),
    status: toStr(r.status, "awaiting_payment"),
    amount_krw: toNum(r.amount_krw),
    bank: {
      bank: toStr(bank.bank, fallbackBank.bank),
      holder: toStr(bank.holder, fallbackBank.holder),
      account_number: toStr(bank.account_number, fallbackBank.account_number),
    },
    instructions: toStr(r.instructions, "입금 후 확인 버튼을 눌러 주세요."),
    transitions: Array.isArray(r.transitions)
      ? r.transitions.map((t) => String(t))
      : [],
  };
}

/** 계정과목 (백엔드 ACCOUNT_CATEGORIES와 동일) */
export const ACCOUNT_CATEGORIES: { value: string; hint: string }[] = [
  { value: "식대", hint: "식비, 음료, 다과" },
  { value: "소모품", hint: "사무용품 등 소모성 물품" },
  { value: "임대료", hint: "가게·사무실 임차료" },
  { value: "재료비", hint: "원재료, 상품 매입" },
  { value: "교통비", hint: "대중교통, 택시, 주유" },
  { value: "관리비", hint: "전기·수도·가스 등 공과금" },
  { value: "기타", hint: "분류가 어려운 지출" },
];

export const CATEGORY_VALUES: string[] = ACCOUNT_CATEGORIES.map((c) => c.value);

/** 온보딩 저장값 */
export interface OnboardSettings {
  businessName: string;
  categories: string[]; // 사용자가 사용하는 계정과목
  storeCode: string; // 가게 코드(namespace) — 같은 가게 폰들은 같은 코드
  storePin: string; // 가게 코드 잠금 PIN — 코드를 아는 사람도 PIN 없이는 장부 접근 불가
  onboarded: boolean;
  // T4: 기장의무 판정 입력 (선택)
  industryGroup?: string; // 가/나/다
  prevRevenue?: number | string; // 직전연도 수입금액
}

/**
 * 가게 코드 생성 — 4자리 영숫자 (혼동 문자 I/O/0/1 제외).
 * 같은 가게에서 쓸 모든 폰이 같은 코드를 입력해야 장부가 공유된다.
 */
export function generateStoreCode(): string {
  const alphabet = "ABCDEFGHJKMNPQRSTUVWXYZ23456789";
  const bytes = new Uint32Array(4);
  // crypto.getRandomValues는 RN/웹 모두 지원
  if (typeof crypto !== "undefined" && typeof crypto.getRandomValues === "function") {
    crypto.getRandomValues(bytes);
  } else {
    for (let i = 0; i < 4; i++) bytes[i] = Math.floor(Math.random() * 0xffffffff);
  }
  return Array.from(bytes, (b) => alphabet[b % alphabet.length]).join("");
}

/** 가게 코드 형식 검증 — 1~16자 영숫자 (백엔드 X-Store-Code 계약과 동일). */
export function isValidStoreCode(code: string): boolean {
  return /^[A-Za-z0-9]{1,16}$/.test(code.trim());
}