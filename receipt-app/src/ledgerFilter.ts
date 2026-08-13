/**
 * 장부 거래 검색·필터·정렬 (고도화) — 순수 함수.
 * 웹/네이티브 화면과 분리해 로직을 테스트 가능하게 유지한다.
 */
import type { LedgerEntry } from "./types";

export type SortField = "date" | "amount";

export function filterAndSortEntries(
  entries: LedgerEntry[] | undefined,
  query: string,
  catFilter: string,
  sortBy: SortField,
  sortAsc: boolean
): LedgerEntry[] {
  let rows = entries ?? [];
  const q = query.trim().toLowerCase();
  if (q) {
    rows = rows.filter((e) => {
      const hay = [
        e.store || "",
        e.note || "",
        ...((e.items as { name?: string }[] | undefined) ?? []).map((it) => it.name || ""),
      ]
        .join(" ")
        .toLowerCase();
      return hay.includes(q);
    });
  }
  if (catFilter) {
    rows = rows.filter((e) => (e.category || "기타") === catFilter);
  }
  const dir = sortAsc ? 1 : -1;
  return [...rows].sort((a, b) => {
    if (sortBy === "amount") {
      const am = Number(a.total ?? a.amount ?? 0);
      const bm = Number(b.total ?? b.amount ?? 0);
      return (am - bm) * dir;
    }
    return String(a.date || "").localeCompare(String(b.date || "")) * dir;
  });
}
