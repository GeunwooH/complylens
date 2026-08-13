/**
 * W2-4: 장부 목록 + 월간 리포트 화면.
 * GET /api/ledger?month=YYYY-MM — 매출/지출/손익/미분류 요약 + 거래 목록.
 */
import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert,
  FlatList,
  Modal,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { createEntry, deleteEntry, fetchLedger, toKoreanError, updateEntry } from "../api";
import { currentMonth, fmtSignedWon, fmtWon, shiftMonth } from "../config";
import { COLORS, styles as themeStyles } from "../theme";
import { LedgerEntry, LedgerReport, ACCOUNT_CATEGORIES } from "../types";
import { filterAndSortEntries } from "../ledgerFilter";
import { Button, ErrorBanner, EmptyState, Spinner } from "../components/ui";
import { CategoryPickerModal } from "../components/CategoryPickerModal";

export function LedgerScreen() {
  const [month, setMonth] = useState(currentMonth());
  const [report, setReport] = useState<LedgerReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [showIncome, setShowIncome] = useState(false);
  const [incStore, setIncStore] = useState("");
  const [incAmount, setIncAmount] = useState("");
  const [incDate, setIncDate] = useState("");
  const [incSaving, setIncSaving] = useState(false);
  // T3: 장부 탭 거래 수정
  const [editEntry, setEditEntry] = useState<LedgerEntry | null>(null);
  const [editCategory, setEditCategory] = useState("기타");
  const [editAmount, setEditAmount] = useState("");
  const [editSaving, setEditSaving] = useState(false);
  const [showCategory, setShowCategory] = useState(false);
  // 고도화: 거래 검색·필터·정렬
  const [query, setQuery] = useState("");
  const [catFilter, setCatFilter] = useState("");
  const [sortBy, setSortBy] = useState<"date" | "amount">("date");
  const [sortAsc, setSortAsc] = useState(false);

  const openEdit = (item: LedgerEntry) => {
    setEditEntry(item);
    setEditCategory(item.category || "기타");
    setEditAmount(String(item.total ?? item.amount ?? ""));
  };

  const closeEdit = () => {
    setEditEntry(null);
    setEditCategory("기타");
    setEditAmount("");
  };

  const saveEdit = async () => {
    if (!editEntry) return;
    const amount = editAmount.replace(/[^\d]/g, "");
    if (!amount) {
      setError("금액을 입력해 주세요.");
      return;
    }
    setEditSaving(true);
    setError("");
    try {
      await updateEntry(editEntry.receipt_id, {
        category: editCategory,
        total: amount,
      });
      closeEdit();
      await load(month);
    } catch (e) {
      setError(await toKoreanError(e));
    } finally {
      setEditSaving(false);
    }
  };

  const closeIncome = () => {
    setShowIncome(false);
    setIncStore("");
    setIncAmount("");
    setIncDate("");
  };

  const saveIncome = async () => {
    const store = incStore.trim();
    const amount = incAmount.replace(/[^\d]/g, "");
    if (!store || !amount) {
      setError("내용과 금액을 입력해 주세요.");
      return;
    }
    setIncSaving(true);
    setError("");
    try {
      await createEntry({
        store,
        category: "기타",
        amount,
        date: incDate.trim() || undefined,
        kind: "income",
        note: "수동 입력",
      });
      closeIncome();
      await load(month);
    } catch (e) {
      setError(await toKoreanError(e));
    } finally {
      setIncSaving(false);
    }
  };

  const confirmDelete = (entryId: string, label: string) => {
    Alert.alert(
      "거래 삭제",
      `${label} 기록을 삭제할까요?`,
      [
        { text: "취소", style: "cancel" },
        {
          text: "삭제",
          style: "destructive",
          onPress: async () => {
            try {
              await deleteEntry(entryId);
              await load(month);
            } catch (e) {
              setError(await toKoreanError(e));
            }
          },
        },
      ]
    );
  };

  const load = useCallback(async (m: string, background = false) => {
    if (!background) setLoading(true);
    setError("");
    try {
      const data = await fetchLedger(m);
      // 방어: 필드 누락/형식 이탈 시에도 화면은 안 죽는다
      setReport({
        ...data,
        month: data.month || m,
        entries: Array.isArray(data.entries) ? data.entries : [],
        entry_count: Number(data.entry_count) || 0,
        revenue: Number(data.revenue) || 0,
        expense: Number(data.expense) || 0,
        profit: Number(data.profit) || 0,
        unclassified_count: Number(data.unclassified_count) || 0,
      });
    } catch (e) {
      setError(await toKoreanError(e));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  // 월 변경 시 로드
  useEffect(() => {
    load(month);
  }, [month, load]);

  // 다른 탭에서 저장하고 돌아오면 자동 새로고침
  useFocusEffect(
    useCallback(() => {
      if (report) load(month, true);
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [month])
  );

  const move = (delta: number) => {
    setRefreshing(false);
    setMonth((m) => shiftMonth(m, delta));
  };

  // 고도화: 검색어(거래처·품목) + 카테고리 필터 + 정렬 (순수 함수 ledgerFilter)
  const visibleEntries = useMemo(
    () => filterAndSortEntries(report?.entries, query, catFilter, sortBy, sortAsc),
    [report, query, catFilter, sortBy, sortAsc]
  );

  return (
    <View style={themeStyles.screen}>
      <View style={styles.monthRow}>
        <Pressable onPress={() => move(-1)} style={styles.monthArrow}>
          <Text style={styles.monthArrowText}>‹</Text>
        </Pressable>
        <Text style={styles.monthLabel}>{month}</Text>
        <Pressable onPress={() => move(1)} style={styles.monthArrow}>
          <Text style={styles.monthArrowText}>›</Text>
        </Pressable>

      </View>
      {/* 고도화: 검색 · 필터 · 정렬 (FlatList 밖 — 항상 노출, 웹 인터랙션 안정) */}
      <View style={styles.filterBox}>
        <TextInput
          style={styles.searchInput}
          value={query}
          onChangeText={setQuery}
          placeholder="거래처·품목 검색"
        />
        <View style={styles.chipRow}>
          {["", ...ACCOUNT_CATEGORIES.map((c) => c.value)].map((cat) => {
            const active = catFilter === cat;
            return (
              <Pressable
                key={cat || "전체"}
                onPress={() => setCatFilter(active ? "" : cat)}
                style={[
                  styles.chip,
                  active && { backgroundColor: COLORS.primary },
                ]}
              >
                <Text style={[styles.chipText, active && { color: "#FFF" }]}>
                  {cat || "전체"}
                </Text>
              </Pressable>
            );
          })}
        </View>
        <View style={styles.sortRow}>
          <Pressable onPress={() => { setSortBy("date"); setSortAsc(sortBy !== "date" ? false : !sortAsc); }}>
            <Text style={[styles.sortText, sortBy === "date" && styles.sortTextActive]}>
              날짜 {sortBy === "date" ? (sortAsc ? "↑" : "↓") : ""}
            </Text>
          </Pressable>
          <Pressable onPress={() => { setSortBy("amount"); setSortAsc(sortBy !== "amount" ? false : !sortAsc); }}>
            <Text style={[styles.sortText, sortBy === "amount" && styles.sortTextActive]}>
              금액 {sortBy === "amount" ? (sortAsc ? "↑" : "↓") : ""}
            </Text>
          </Pressable>
        </View>
      </View>
      <FlatList
        data={visibleEntries}
        keyExtractor={(item) => item.receipt_id || `e-${item.store}-${item.total}`}
        contentContainerStyle={styles.listContent}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => {
              setRefreshing(true);
              load(month, true);
            }}
          />
        }
        ListHeaderComponent={
          <View>
            <ErrorBanner message={error} />
            {loading && !report ? (
              <Spinner label="장부 불러오는 중…" />
            ) : (
              <View>
                {report ? (
                  <View style={themeStyles.card}>
                    <Text style={styles.summaryTitle}>
                      {report.month} 요약 · {report.entry_count}건
                    </Text>
                    <View style={styles.summaryGrid}>
                      <SummaryCell label="매출" value={fmtWon(report.revenue)} tone="good" />
                      <SummaryCell label="지출" value={fmtWon(report.expense)} tone="danger" />
                      <SummaryCell
                        label="손익"
                        value={fmtSignedWon(report.profit)}
                        tone={report.profit >= 0 ? "good" : "danger"}
                        sub={
                          report.prev_profit !== undefined
                            ? `전월 ${fmtSignedWon(report.prev_profit)}`
                            : undefined
                        }
                      />
                      <SummaryCell
                        label="미분류"
                        value={`${report.unclassified_count}건`}
                        tone={report.unclassified_count > 0 ? "warn" : "good"}
                      />
                    </View>
                    {report.category_breakdown &&
                    Object.keys(report.category_breakdown).length > 0 ? (
                      <View style={styles.analysisBlock}>
                        <Text style={styles.analysisTitle}>카테고리별 지출</Text>
                        {Object.entries(report.category_breakdown).map(([cat, amt]) => {
                          const max = Math.max(
                            ...Object.values(report.category_breakdown ?? {})
                          );
                          const ratio = max > 0 ? (amt / max) * 100 : 0;
                          return (
                            <View key={cat} style={styles.analysisRow}>
                              <Text style={styles.analysisLabel}>{cat}</Text>
                              <View style={styles.barTrack}>
                                <View
                                  style={[styles.barFill, { width: `${ratio}%` }]}
                                />
                              </View>
                              <Text style={styles.analysisAmount}>{fmtWon(amt)}</Text>
                            </View>
                          );
                        })}
                        {report.top_stores && report.top_stores.length > 0 ? (
                          <Text style={styles.topStores}>
                            주요 지출처: {report.top_stores.map(([s]) => s).join(" · ")}
                          </Text>
                        ) : null}
                      </View>
                    ) : null}
                    {(report.unclassified_count > 0 || report.needs_review_count > 0) ? (
                      <View style={styles.reviewBanner}>
                        <Text style={styles.reviewBannerText}>
                          ⚠️ 검토 필요: 미분류 {report.unclassified_count}건
                          {report.needs_review_count > 0
                            ? ` · 금액 불일치 ${report.needs_review_count}건`
                            : ""}
                        </Text>
                      </View>
                    ) : report.entry_count > 0 ? (
                      <View style={[styles.reviewBanner, styles.reviewBannerOk]}>
                        <Text style={styles.reviewBannerTextOk}>✓ 모든 항목이 정리됐어요</Text>
                      </View>
                    ) : null}
                  </View>
                ) : null}
                {/* 고도화: 검색 · 필터 · 정렬 */}
                <View style={styles.listHeaderRow}>
                  <Text style={styles.listHeaderText}>장부 목록</Text>
                  <View style={styles.headerBtns}>
                    <Button
                      label="+ 수입 기록"
                      onPress={() => setShowIncome(true)}
                      style={{ paddingVertical: 8, paddingHorizontal: 12, minHeight: 36 }}
                    />
                    <Button
                      label="새로고침"
                      kind="secondary"
                      onPress={() => load(month)}
                      style={{ paddingVertical: 8, paddingHorizontal: 12, minHeight: 36 }}
                    />
                  </View>
                </View>
                {!loading && report && report.entries.length === 0 ? (
                  <EmptyState
                    title="이 달의 장부 기록이 없습니다"
                    sub="촬영 탭에서 영수증을 찍으면 자동으로 기록됩니다."
                  />
                ) : null}
              </View>
            )}
          </View>
        }
        renderItem={({ item }) => {
          const unclassified =
            item.unclassified === true || item.category === "기타";
          return (
            <Pressable
              onPress={() => openEdit(item)}
              style={({ pressed }) => [
                themeStyles.card,
                styles.entryCard,
                pressed && { opacity: 0.75 },
              ]}
            >
              <View style={styles.entryLeft}>
                <View style={styles.entryTopRow}>
                  <Text style={styles.entryStore}>{item.store || "가게명 없음"}</Text>
                  {unclassified ? <Text style={styles.badgeUnclassified}>미분류</Text> : null}
                  {item.needs_review ? <Text style={styles.badgeReview}>검토</Text> : null}
                  {item.kind === "income" ? <Text style={styles.badgeIncome}>수입</Text> : null}
                </View>
                <Text style={styles.entryDate}>{item.date || "날짜 없음"}</Text>
              </View>
              <View style={styles.entryRight}>
                <Pressable
                  hitSlop={10}
                  onPress={() => confirmDelete(item.receipt_id, item.store || "이 거래")}
                >
                  <Text style={styles.deleteBtn}>✕</Text>
                </Pressable>
                <Text style={styles.entryCategory}>{item.category || "기타"}</Text>
                <Text
                  style={[
                    styles.entryAmount,
                    item.kind === "income" && { color: COLORS.success },
                  ]}
                >
                  {fmtWon(item.total ?? item.amount)}
                </Text>
              </View>
            </Pressable>
          );
        }}
      />

      <Modal visible={showIncome} transparent animationType="fade" onRequestClose={closeIncome}>
        <View style={styles.modalBackdrop}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>수입 기록 추가</Text>
            <TextInput
              style={styles.modalInput}
              value={incStore}
              onChangeText={setIncStore}
              placeholder="내용 (예: 현금 매출)"
            />
            <TextInput
              style={styles.modalInput}
              value={incAmount}
              onChangeText={(t) => setIncAmount(t.replace(/[^\d]/g, ""))}
              placeholder="금액 (원)"
              keyboardType="number-pad"
            />
            <TextInput
              style={styles.modalInput}
              value={incDate}
              onChangeText={setIncDate}
              placeholder="날짜 (YYYY-MM-DD, 비워두면 오늘)"
            />
            <View style={styles.modalBtnRow}>
              <Button label="취소" kind="secondary" onPress={closeIncome} />
              <Button
                label={incSaving ? "저장 중…" : "저장"}
                onPress={saveIncome}
                loading={incSaving}
              />
            </View>
          </View>
        </View>
      </Modal>

      {/* T3: 거래 수정 모달 */}
      <Modal visible={editEntry !== null} transparent animationType="fade" onRequestClose={closeEdit}>
        <View style={styles.modalBackdrop}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>거래 수정</Text>
            <Text style={styles.editStoreLabel}>{editEntry?.store || "가게명 없음"}</Text>
            <Pressable style={styles.categoryBtn} onPress={() => setShowCategory(true)}>
              <Text style={styles.categoryBtnText}>분류: {editCategory}</Text>
              <Text style={styles.categoryBtnHint}>탭해서 바꾸기 ▾</Text>
            </Pressable>
            <TextInput
              style={styles.modalInput}
              value={editAmount}
              onChangeText={(t) => setEditAmount(t.replace(/[^\d]/g, ""))}
              placeholder="금액 (원)"
              keyboardType="number-pad"
            />
            <Text style={styles.editHint}>
              분류를 고치면 다음에 같은 가게 영수증을 찍을 때부터 자동으로 반영됩니다.
            </Text>
            <View style={styles.modalBtnRow}>
              <Button label="취소" kind="secondary" onPress={closeEdit} />
              <Button
                label={editSaving ? "저장 중…" : "저장"}
                onPress={saveEdit}
                loading={editSaving}
              />
            </View>
          </View>
        </View>
      </Modal>
      <CategoryPickerModal
        visible={showCategory}
        selected={editCategory}
        onSelect={(value) => {
          setEditCategory(value);
          setShowCategory(false);
        }}
        onClose={() => setShowCategory(false)}
      />
    </View>
  );
}

function SummaryCell({
  label,
  value,
  tone,
  sub,
}: {
  label: string;
  value: string;
  tone: "good" | "danger" | "warn";
  sub?: string;
}) {
  const color =
    tone === "good" ? COLORS.success : tone === "danger" ? COLORS.danger : COLORS.warn;
  return (
    <View style={styles.summaryCell}>
      <Text style={styles.summaryCellLabel}>{label}</Text>
      <Text style={[styles.summaryCellValue, { color }]}>{value}</Text>
      {sub ? <Text style={styles.summaryCellSub}>{sub}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  monthRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 14,
    gap: 18,
  },
  monthArrow: {
    paddingHorizontal: 14,
    paddingVertical: 6,
  },
  monthArrowText: {
    fontSize: 26,
    color: COLORS.primary,
    fontWeight: "700",
  },
  monthLabel: {
    fontSize: 18,
    fontWeight: "700",
    color: COLORS.text,
    minWidth: 110,
    textAlign: "center",
  },
  listContent: {
    paddingHorizontal: 20,
    paddingBottom: 40,
  },
  summaryTitle: {
    fontSize: 15,
    fontWeight: "700",
    color: COLORS.textMuted,
    marginBottom: 12,
  },
  summaryGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10,
  },
  summaryCell: {
    flexBasis: "47%",
    backgroundColor: "#F7FAFC",
    borderRadius: 10,
    padding: 12,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  summaryCellLabel: {
    fontSize: 12,
    color: COLORS.textMuted,
  },
  summaryCellValue: {
    fontSize: 17,
    fontWeight: "700",
    marginTop: 4,
  },
  summaryCellSub: {
    fontSize: 11,
    color: COLORS.textMuted,
    marginTop: 3,
  },
  analysisBlock: {
    marginTop: 14,
    borderTopWidth: 1,
    borderTopColor: COLORS.border,
    paddingTop: 12,
  },
  analysisTitle: {
    fontSize: 13,
    fontWeight: "700",
    color: COLORS.textMuted,
    marginBottom: 10,
  },
  analysisRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 7,
  },
  analysisLabel: {
    width: 62,
    fontSize: 12,
    fontWeight: "600",
    color: COLORS.text,
  },
  barTrack: {
    flex: 1,
    height: 10,
    borderRadius: 5,
    backgroundColor: "#EDF2F7",
    marginHorizontal: 8,
    overflow: "hidden",
  },
  barFill: {
    height: "100%",
    borderRadius: 5,
    backgroundColor: COLORS.primary,
  },
  analysisAmount: {
    width: 76,
    fontSize: 12,
    fontWeight: "700",
    textAlign: "right",
    color: COLORS.text,
  },
  topStores: {
    marginTop: 8,
    fontSize: 12,
    color: COLORS.textMuted,
  },
  headerBtns: {
    flexDirection: "row",
    gap: 6,
  },
  filterBox: {
    marginTop: 12,
    backgroundColor: "#FFF",
    borderRadius: 10,
    borderWidth: 1,
    borderColor: COLORS.border,
    padding: 10,
  },
  searchInput: {
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 8,
    fontSize: 14,
    color: COLORS.text,
    backgroundColor: "#F7FAFC",
  },
  chipRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 6,
    marginTop: 8,
  },
  chip: {
    borderRadius: 999,
    backgroundColor: "#EDF2F7",
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
  chipText: {
    fontSize: 12,
    fontWeight: "600",
    color: COLORS.textMuted,
  },
  sortRow: {
    flexDirection: "row",
    gap: 14,
    marginTop: 8,
  },
  sortText: {
    fontSize: 12,
    fontWeight: "600",
    color: COLORS.textMuted,
  },
  sortTextActive: {
    color: COLORS.primary,
  },
  badgeIncome: {
    fontSize: 11,
    fontWeight: "700",
    color: "#065F46",
    backgroundColor: "#D1FAE5",
    borderRadius: 6,
    paddingHorizontal: 7,
    paddingVertical: 2,
    overflow: "hidden",
  },
  deleteBtn: {
    fontSize: 14,
    color: COLORS.danger,
    fontWeight: "700",
    marginBottom: 4,
  },
  modalBackdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.4)",
    justifyContent: "center",
    padding: 24,
  },
  modalCard: {
    backgroundColor: COLORS.bg,
    borderRadius: 16,
    padding: 20,
  },
  modalTitle: {
    fontSize: 17,
    fontWeight: "700",
    color: COLORS.text,
    marginBottom: 14,
  },
  modalInput: {
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 15,
    color: COLORS.text,
    backgroundColor: "#FFF",
    marginBottom: 10,
  },
  modalRow: {
    flexDirection: "row",
    gap: 10,
  },
  modalBtnRow: {
    flexDirection: "row",
    justifyContent: "flex-end",
    gap: 10,
    marginTop: 8,
  },
  editStoreLabel: {
    fontSize: 15,
    fontWeight: "700",
    color: COLORS.text,
    marginBottom: 12,
  },
  categoryBtn: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 12,
    backgroundColor: "#FFF",
    marginBottom: 10,
  },
  categoryBtnText: {
    fontSize: 15,
    color: COLORS.text,
    fontWeight: "600",
  },
  categoryBtnHint: {
    fontSize: 12,
    color: COLORS.textMuted,
  },
  editHint: {
    fontSize: 12,
    lineHeight: 17,
    color: COLORS.textMuted,
    marginBottom: 4,
  },
  listHeaderRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginTop: 20,
    marginBottom: 10,
  },
  listHeaderText: {
    fontSize: 17,
    fontWeight: "700",
    color: COLORS.text,
  },
  entryCard: {
    marginBottom: 10,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 12,
  },
  entryLeft: {
    flex: 1,
  },
  entryStore: {
    fontSize: 15,
    fontWeight: "600",
    color: COLORS.text,
  },
  entryTopRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  badgeUnclassified: {
    fontSize: 11,
    fontWeight: "700",
    color: "#92400E",
    backgroundColor: "#FEF3C7",
    borderRadius: 6,
    paddingHorizontal: 7,
    paddingVertical: 2,
    overflow: "hidden",
  },
  badgeReview: {
    fontSize: 11,
    fontWeight: "700",
    color: "#B91C1C",
    backgroundColor: "#FEE2E2",
    borderRadius: 6,
    paddingHorizontal: 7,
    paddingVertical: 2,
    overflow: "hidden",
  },
  reviewBanner: {
    marginTop: 12,
    backgroundColor: "#FEF3C7",
    borderRadius: 10,
    padding: 12,
  },
  reviewBannerOk: {
    backgroundColor: "#ECFDF5",
  },
  reviewBannerText: {
    fontSize: 13,
    fontWeight: "600",
    color: "#92400E",
  },
  reviewBannerTextOk: {
    fontSize: 13,
    fontWeight: "600",
    color: "#065F46",
  },
  entryDate: {
    fontSize: 12,
    color: COLORS.textMuted,
    marginTop: 3,
  },
  entryRight: {
    alignItems: "flex-end",
  },
  entryCategory: {
    fontSize: 12,
    color: COLORS.primaryDark,
    fontWeight: "600",
    marginBottom: 3,
  },
  entryAmount: {
    fontSize: 16,
    fontWeight: "700",
    color: COLORS.text,
  },
});