/**
 * OCR 결과 카드 + 1클릭 수정 UI (W2-2 결과 표시, W2-3 수정).
 * - 금액(총액/부가세/품목 가격) 탭 → 숫자 키패드
 * - 품목명 탭 → 텍스트 수정
 * - 분류 탭 → 계정과목 드롭다운
 * - "수정 저장" → PATCH /api/receipts/{id}/correct
 */
import React, { useMemo, useState } from "react";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { correctReceipt, toKoreanError, trackEvent } from "../api";
import { COLORS } from "../theme";
import { fmtWon } from "../config";
import { ReceiptCard as CardType } from "../types";
import { NumericKeypadModal } from "./NumericPad";
import { CategoryPickerModal } from "./CategoryPickerModal";
import { Button, Chip, ErrorBanner, SectionTitle } from "./ui";

type PadTarget = "total" | "vat" | `item-${number}` | null;

export function ReceiptCard({
  card,
  activeCategories,
  onUpdated,
  onViewLedger,
}: {
  card: CardType;
  activeCategories?: string[];
  onUpdated: (updated: CardType) => void;
  onViewLedger?: () => void;
}) {
  const [category, setCategory] = useState(card.category);
  const [items, setItems] = useState(card.items.map((it) => ({ ...it })));
  const [total, setTotal] = useState<number | string>(card.total);
  const [vat, setVat] = useState<number | string | null>(card.vat ?? null);
  const [padTarget, setPadTarget] = useState<PadTarget>(null);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const dirty = useMemo(
    () =>
      category !== card.category ||
      total !== card.total ||
      JSON.stringify(items) !== JSON.stringify(card.items),
    [category, total, items, card]
  );

  const padIndex = padTarget !== null && padTarget.startsWith("item-")
    ? Number(padTarget.slice(5))
    : -1;
  const padInitial =
    padTarget === "total"
      ? String(total)
      : padTarget === "vat"
        ? String(vat ?? "")
        : padTarget !== null
          ? String(items[padIndex]?.price ?? "")
          : "0";
  const padTitle =
    padTarget === "total"
      ? "총액 수정"
      : padTarget === "vat"
        ? "부가세 수정"
        : padTarget !== null
          ? `품목 금액 수정 (${items[padIndex]?.name ?? "품목"})`
          : "금액 수정";

  const applyPad = (amount: number) => {
    if (padTarget === "total") setTotal(amount);
    else if (padTarget === "vat") setVat(amount);
    else if (padTarget !== null) {
      setItems((prev) =>
        prev.map((it, i) => (i === padIndex ? { ...it, price: amount } : it))
      );
    }
    setPadTarget(null);
  };

  const renameItem = (index: number, name: string) => {
    setItems((prev) => prev.map((it, i) => (i === index ? { ...it, name } : it)));
  };

  const save = async () => {
    setSaving(true);
    setError("");
    try {
      const updated = await correctReceipt(card.receipt_id, {
        category,
        items,
        total,
      });
      onUpdated(updated);
      trackEvent("receipt_corrected", { category }).catch(() => {});
    } catch (e) {
      setError(await toKoreanError(e));
    } finally {
      setSaving(false);
    }
  };

  const confidenceTone = card.confidence === "low" || card.needs_review ? "warn" : "good";
  const ratioLabel =
    typeof card.category_confidence === "number"
      ? Math.round(card.category_confidence * 100)
      : null;

  return (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <Text style={styles.store}>{card.store}</Text>
        <Chip
          label={card.confidence === "low" ? "검토 필요" : "인식 완료"}
          tone={confidenceTone}
        />
      </View>
      <Text style={styles.date}>
        {card.date || "날짜 없음"} · {card.payment || "결제수단 미상"}
      </Text>

      {card.warnings && card.warnings.length > 0 ? (
        <View style={styles.warnBox}>
          {card.warnings.map((w, i) => (
            <Text key={i} style={styles.warnText}>
              ⚠ {w}
            </Text>
          ))}
        </View>
      ) : null}

      <SectionTitle>품목 (금액 탭 → 수정)</SectionTitle>
      {items.map((item, idx) => (
        <View key={`${item.name}-${idx}`} style={styles.itemRow}>
          <TextInput
            value={item.name}
            onChangeText={(t) => renameItem(idx, t)}
            style={styles.itemNameInput}
            placeholder="품목명"
            placeholderTextColor="#A0AEC0"
            maxLength={40}
          />
          <Pressable
            style={({ pressed }) => [styles.itemPrice, pressed && { opacity: 0.6 }]}
            onPress={() => setPadTarget(`item-${idx}` as PadTarget)}
          >
            <Text style={styles.itemPriceText}>{fmtWon(item.price)}</Text>
          </Pressable>
        </View>
      ))}
      <View style={styles.sumBox}>
        <Pressable style={styles.sumRow} onPress={() => setPadTarget("total")}>
          <Text style={styles.sumLabel}>총액</Text>
          <Text style={styles.sumValue}>{fmtWon(total)}</Text>
        </Pressable>
        <Pressable style={styles.sumRow} onPress={() => setPadTarget("vat")}>
          <Text style={styles.sumLabel}>부가세</Text>
          <Text style={styles.sumValue}>{vat == null ? "—" : fmtWon(vat)}</Text>
        </Pressable>
      </View>

      <SectionTitle>분류</SectionTitle>
      <Pressable style={styles.categoryRow} onPress={() => setPickerOpen(true)}>
        <Text style={styles.categoryLabel}>계정과목</Text>
        <View style={styles.categoryValueWrap}>
          <Text style={styles.categoryValue}>{category}</Text>
          {ratioLabel !== null ? (
            <Text style={styles.categoryRatio}>자동분류 {ratioLabel}%</Text>
          ) : null}
          <Text style={styles.categoryCaret}>▾</Text>
        </View>
      </Pressable>

      <ErrorBanner message={error} />

      <View style={styles.actions}>
        <Button
          label={saving ? "저장 중…" : "수정 저장"}
          onPress={save}
          loading={saving}
          disabled={!dirty && !error}
        />
        {onViewLedger ? (
          <Button
            label="장부 보기"
            kind="secondary"
            onPress={onViewLedger}
            style={{ marginTop: 8 }}
          />
        ) : null}
      </View>

      <NumericKeypadModal
        visible={padTarget !== null}
        title={padTitle}
        initialValue={padInitial}
        onConfirm={applyPad}
        onClose={() => setPadTarget(null)}
      />
      <CategoryPickerModal
        visible={pickerOpen}
        selected={category}
        highlightValues={activeCategories}
        onSelect={setCategory}
        onClose={() => setPickerOpen(false)}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: COLORS.card,
    borderRadius: 14,
    padding: 16,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  cardHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 6,
  },
  store: {
    fontSize: 19,
    fontWeight: "700",
    color: COLORS.text,
    flex: 1,
    marginRight: 10,
  },
  date: {
    fontSize: 13,
    color: COLORS.textMuted,
    marginBottom: 12,
  },
  warnBox: {
    backgroundColor: "#FFF5F0",
    borderRadius: 8,
    padding: 10,
    marginBottom: 12,
  },
  warnText: {
    fontSize: 12,
    lineHeight: 18,
    color: COLORS.warn,
  },
  itemRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 8,
  },
  itemNameInput: {
    flex: 1,
    fontSize: 15,
    color: COLORS.text,
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 8,
    marginRight: 8,
    backgroundColor: "#FFF",
  },
  itemPrice: {
    minWidth: 96,
    alignItems: "flex-end",
    justifyContent: "center",
    paddingVertical: 8,
    paddingHorizontal: 10,
    backgroundColor: COLORS.chipBg,
    borderRadius: 8,
  },
  itemPriceText: {
    fontSize: 15,
    fontWeight: "700",
    color: COLORS.primaryDark,
  },
  sumBox: {
    marginTop: 4,
    borderTopWidth: 1,
    borderTopColor: COLORS.border,
    paddingTop: 4,
  },
  sumRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 8,
  },
  sumLabel: {
    fontSize: 14,
    color: COLORS.textMuted,
  },
  sumValue: {
    fontSize: 17,
    fontWeight: "700",
    color: COLORS.text,
  },
  categoryRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 12,
    backgroundColor: COLORS.chipBg,
    borderRadius: 10,
    paddingHorizontal: 12,
  },
  categoryLabel: {
    fontSize: 14,
    color: COLORS.textMuted,
  },
  categoryValueWrap: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  categoryValue: {
    fontSize: 16,
    fontWeight: "700",
    color: COLORS.primaryDark,
  },
  categoryRatio: {
    fontSize: 12,
    color: COLORS.textMuted,
  },
  categoryCaret: {
    fontSize: 14,
    color: COLORS.primary,
  },
  actions: {
    marginTop: 14,
  },
});