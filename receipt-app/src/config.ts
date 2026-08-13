/**
 * 앱 전역 설정.
 * - API_BASE_URL: 로컬 백엔드 기본값. EXPO_PUBLIC_API_URL 환경변수로 변경 가능
 *   (빌드/실행 시 export EXPO_PUBLIC_API_URL=http://192.168.x.x:8000).
 *   Android 에뮬레이터에서는 http://10.0.2.2:8000 사용.
 */
export const API_BASE_URL: string =
  process.env.EXPO_PUBLIC_API_URL ?? "https://receipt-api.npopo.com";

/** 월간 리포트 기본 월 (로컬 시간 기준 YYYY-MM) */
export function currentMonth(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

/** YYYY-MM → N달 이동한 월 문자열 */
export function shiftMonth(month: string, delta: number): string {
  const [y, m] = month.split("-").map(Number);
  const date = new Date(y, (m - 1) + delta, 1);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
}

/** 원화 표시: 7800 → "7,800원" (숫자/문자 무관, 무효 값은 "0원") */
export function fmtWon(value: number | string | null | undefined): string {
  const n = Number(String(value ?? "").replace(/[^\d.-]/g, ""));
  if (!Number.isFinite(n)) return "0원";
  return `${Math.round(n).toLocaleString("ko-KR")}원`;
}

/** 손익 부호 표시: -26800 → "-26,800원" (양수면 부호 생략) */
export function fmtSignedWon(value: number): string {
  if (!Number.isFinite(value)) return "0원";
  const sign = value < 0 ? "-" : "";
  return `${sign}${Math.abs(Math.round(value)).toLocaleString("ko-KR")}원`;
}