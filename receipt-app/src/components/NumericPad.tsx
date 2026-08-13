/**
 * 숫자 키패드 모달 — 금액 탭 → 숫자패드 (W2-3 1클릭 수정).
 * 내부 상태는 숫자 문자열(digits)만 유지하고, 표시는 천 단위 콤마.
 * 결정적 — 타이머/딜레이 없음.
 */
import React, { useMemo, useState } from "react";
import {
  Modal,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { COLORS } from "../theme";

const KEYS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"];

function groupThousands(digits: string): string {
  const n = Number(digits);
  if (!digits || !Number.isFinite(n)) return "0";
  return n.toLocaleString("ko-KR");
}

export function NumericKeypadModal({
  visible,
  title,
  initialValue,
  onConfirm,
  onClose,
}: {
  visible: boolean;
  title: string;
  initialValue: string; // "7800" 또는 "7,800"
  onConfirm: (value: number) => void;
  onClose: () => void;
}) {
  const digits = useMemo(() => String(initialValue).replace(/[^\d]/g, ""), [
    initialValue,
    visible,
  ]);
  const [buffer, setBuffer] = useState(digits);

  // visible이 바뀔 때마다 초기값 재설정
  React.useEffect(() => {
    if (visible) setBuffer(digits);
  }, [visible, digits]);

  const press = (key: string) => {
    setBuffer((prev) => {
      if (key === "⌫") return prev.slice(0, -1);
      if (prev.length >= 10) return prev;
      if (prev === "0" && key !== "0") return key;
      return prev === "0" && key === "0" ? prev : prev + key;
    });
  };

  const display = groupThousands(buffer) + "원";
  const canConfirm = buffer.length > 0;

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <View style={styles.overlay}>
        <View style={styles.sheet}>
          <View style={styles.header}>
            <Text style={styles.title}>{title}</Text>
            <Pressable onPress={onClose} hitSlop={12}>
              <Text style={styles.close}>취소</Text>
            </Pressable>
          </View>
          <Text style={styles.display}>{display}</Text>
          <View style={styles.pad}>
            {KEYS.map((key) => (
              <Pressable
                key={key}
                onPress={() => press(key)}
                style={({ pressed }) => [styles.key, pressed && { backgroundColor: "#E2E8F0" }]}
              >
                <Text style={styles.keyText}>{key}</Text>
              </Pressable>
            ))}
            <Pressable
              onPress={() => press("⌫")}
              style={({ pressed }) => [styles.key, pressed && { backgroundColor: "#E2E8F0" }]}
            >
              <Text style={styles.keyText}>⌫</Text>
            </Pressable>
          </View>
          <Pressable
            onPress={() => canConfirm && onConfirm(Number(buffer || "0"))}
            disabled={!canConfirm}
            style={({ pressed }) => [
              styles.confirm,
              !canConfirm && { opacity: 0.4 },
              pressed && canConfirm && { opacity: 0.85 },
            ]}
          >
            <Text style={styles.confirmText}>확인</Text>
          </Pressable>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.45)",
    justifyContent: "flex-end",
  },
  sheet: {
    backgroundColor: "#FFF",
    borderTopLeftRadius: 18,
    borderTopRightRadius: 18,
    padding: 20,
    paddingBottom: 36,
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 14,
  },
  title: {
    fontSize: 17,
    fontWeight: "700",
    color: COLORS.text,
  },
  close: {
    fontSize: 15,
    color: COLORS.textMuted,
    fontWeight: "600",
  },
  display: {
    fontSize: 30,
    fontWeight: "700",
    color: COLORS.primary,
    textAlign: "center",
    marginBottom: 18,
  },
  pad: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-between",
    gap: 10,
  },
  key: {
    width: "31%",
    paddingVertical: 16,
    borderRadius: 12,
    backgroundColor: "#F7FAFC",
    alignItems: "center",
    marginBottom: 10,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  keyText: {
    fontSize: 22,
    fontWeight: "600",
    color: COLORS.text,
  },
  confirm: {
    marginTop: 6,
    backgroundColor: COLORS.primary,
    borderRadius: 12,
    paddingVertical: 15,
    alignItems: "center",
  },
  confirmText: {
    color: "#FFF",
    fontSize: 17,
    fontWeight: "700",
  },
});