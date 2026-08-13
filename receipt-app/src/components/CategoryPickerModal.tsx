/**
 * 계정과목 선택 모달 — 품목/분류 드롭다운 수정 (W2-3).
 */
import React from "react";
import { Modal, Pressable, StyleSheet, Text, View } from "react-native";
import { ACCOUNT_CATEGORIES } from "../types";
import { COLORS } from "../theme";

export function CategoryPickerModal({
  visible,
  selected,
  onSelect,
  onClose,
  highlightValues,
}: {
  visible: boolean;
  selected: string;
  onSelect: (value: string) => void;
  onClose: () => void;
  /** 온보딩에서 활성화한 과목만 강조 (그 외도 선택 가능) */
  highlightValues?: string[];
}) {
  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <View style={styles.overlay}>
        <Pressable style={StyleSheet.absoluteFill} onPress={onClose} />
        <View style={styles.sheet}>
          <Text style={styles.title}>계정과목 선택</Text>
          {ACCOUNT_CATEGORIES.map((cat) => {
            const active = cat.value === selected;
            const recommended = highlightValues?.includes(cat.value);
            return (
              <Pressable
                key={cat.value}
                onPress={() => {
                  onSelect(cat.value);
                  onClose();
                }}
                style={({ pressed }) => [
                  styles.option,
                  active && styles.optionActive,
                  pressed && { opacity: 0.8 },
                ]}
              >
                <View style={styles.optionNameWrap}>
                  <Text style={[styles.optionTitle, active && { color: COLORS.primary }]}>
                    {cat.value}
                  </Text>
                  <Text style={styles.optionHint}>{cat.hint}</Text>
                </View>
                {recommended && !active ? (
                  <Text style={styles.recommended}>사용 중</Text>
                ) : null}
              </Pressable>
            );
          })}
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.45)",
    justifyContent: "center",
    padding: 24,
  },
  sheet: {
    backgroundColor: "#FFF",
    borderRadius: 16,
    padding: 20,
  },
  title: {
    fontSize: 18,
    fontWeight: "700",
    color: COLORS.text,
    marginBottom: 14,
  },
  option: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingVertical: 12,
    paddingHorizontal: 12,
    borderRadius: 10,
    marginBottom: 6,
  },
  optionActive: {
    backgroundColor: COLORS.chipBg,
  },
  optionNameWrap: {
    flex: 1,
  },
  optionTitle: {
    fontSize: 16,
    fontWeight: "600",
    color: COLORS.text,
  },
  optionHint: {
    fontSize: 12,
    color: COLORS.textMuted,
    marginTop: 2,
  },
  recommended: {
    fontSize: 12,
    fontWeight: "600",
    color: COLORS.success,
    marginLeft: 8,
  },
});