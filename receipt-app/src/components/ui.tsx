/** 공용 UI 부품 — 버튼/오류 배너/정보 행/칩/입력/로딩/빈 상태 */
import React from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  TextStyle,
  View,
  ViewStyle,
  StyleProp,
} from "react-native";
import { COLORS } from "../theme";

/* ── Button ─────────────────────────────────────────────────── */

export function Button({
  label,
  onPress,
  kind = "primary",
  disabled,
  loading,
  style,
}: {
  label: string;
  onPress: () => void;
  kind?: "primary" | "secondary" | "danger";
  disabled?: boolean;
  loading?: boolean;
  style?: StyleProp<ViewStyle>;
}) {
  const isSolid = kind !== "secondary";
  const bg = kind === "danger" ? COLORS.danger : isSolid ? COLORS.primary : "#EDF2F7";
  const fg = isSolid ? "#FFF" : COLORS.primaryDark;
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled || loading}
      style={({ pressed }) => [
        styles.button,
        { backgroundColor: bg },
        pressed && { opacity: 0.85 },
        (disabled || loading) && { opacity: 0.5 },
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={fg} />
      ) : (
        <Text style={[styles.buttonText, { color: fg }]}>{label}</Text>
      )}
    </Pressable>
  );
}

/* ── ErrorBanner ────────────────────────────────────────────── */

export function ErrorBanner({ message }: { message: string }) {
  if (!message) return null;
  return (
    <View style={styles.errorBox}>
      <Text style={styles.errorText}>{message}</Text>
    </View>
  );
}

/* ── InfoRow ────────────────────────────────────────────────── */

export function InfoRow({
  label,
  value,
  valueColor,
  onPress,
}: {
  label: string;
  value: string;
  valueColor?: string;
  onPress?: () => void;
}) {
  const body = (
    <View style={styles.infoRow}>
      <Text style={styles.infoLabel}>{label}</Text>
      <Text
        style={[styles.infoValue, valueColor ? { color: valueColor } : null]}
        numberOfLines={2}
      >
        {value}
      </Text>
    </View>
  );
  if (!onPress) return body;
  return (
    <Pressable onPress={onPress} style={({ pressed }) => [pressed && { opacity: 0.7 }]}>
      {body}
    </Pressable>
  );
}

/* ── Chip ───────────────────────────────────────────────────── */

export function Chip({
  label,
  tone = "neutral",
}: {
  label: string;
  tone?: "neutral" | "good" | "warn";
}) {
  const bg =
    tone === "good" ? "#DCF7EC" : tone === "warn" ? "#FEF3E7" : COLORS.chipBg;
  const fg =
    tone === "good" ? COLORS.success : tone === "warn" ? COLORS.warn : COLORS.primaryDark;
  return (
    <View style={[styles.chip, { backgroundColor: bg }]}>
      <Text style={[styles.chipText, { color: fg }]}>{label}</Text>
    </View>
  );
}

/* ── Input ──────────────────────────────────────────────────── */

export function Input({
  value,
  onChangeText,
  placeholder,
  style,
  textStyle,
  editable = true,
  autoFocus,
  selectTextOnFocus,
  secureTextEntry,
}: {
  value: string;
  onChangeText: (t: string) => void;
  placeholder?: string;
  style?: StyleProp<ViewStyle>;
  textStyle?: TextStyle;
  editable?: boolean;
  autoFocus?: boolean;
  selectTextOnFocus?: boolean;
  secureTextEntry?: boolean;
}) {
  return (
    <TextInput
      value={value}
      onChangeText={onChangeText}
      placeholder={placeholder}
      placeholderTextColor="#A0AEC0"
      style={[styles.input, textStyle, style]}
      editable={editable}
      autoFocus={autoFocus}
      selectTextOnFocus={selectTextOnFocus}
      secureTextEntry={secureTextEntry}
    />
  );
}

/* ── Spinner / EmptyState / SectionTitle ────────────────────── */

export function Spinner({ label }: { label?: string }) {
  return (
    <View style={styles.spinnerBox}>
      <ActivityIndicator size="large" color={COLORS.primary} />
      {label ? <Text style={styles.spinnerLabel}>{label}</Text> : null}
    </View>
  );
}

export function EmptyState({ title, sub }: { title: string; sub?: string }) {
  return (
    <View style={styles.emptyBox}>
      <Text style={styles.emptyTitle}>{title}</Text>
      {sub ? <Text style={styles.emptySub}>{sub}</Text> : null}
    </View>
  );
}

export function SectionTitle({ children }: { children: React.ReactNode }) {
  return <Text style={styles.sectionTitle}>{children}</Text>;
}

/* ── styles ─────────────────────────────────────────────────── */

const styles = StyleSheet.create({
  button: {
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: "center",
    justifyContent: "center",
    minHeight: 48,
  },
  buttonText: {
    fontSize: 16,
    fontWeight: "700",
  },
  errorBox: {
    backgroundColor: "#FFF5F5",
    borderColor: "#FEB2B2",
    borderWidth: 1,
    borderRadius: 10,
    padding: 12,
    marginBottom: 12,
  },
  errorText: {
    color: COLORS.danger,
    fontSize: 14,
    lineHeight: 20,
  },
  infoRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 8,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: COLORS.border,
  },
  infoLabel: {
    fontSize: 14,
    color: COLORS.textMuted,
  },
  infoValue: {
    fontSize: 15,
    fontWeight: "600",
    color: COLORS.text,
    flex: 1,
    textAlign: "right",
    marginLeft: 12,
  },
  chip: {
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  chipText: {
    fontSize: 13,
    fontWeight: "600",
  },
  input: {
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 15,
    color: COLORS.text,
    backgroundColor: "#FFF",
  },
  spinnerBox: {
    alignItems: "center",
    paddingVertical: 40,
  },
  spinnerLabel: {
    marginTop: 12,
    color: COLORS.textMuted,
    fontSize: 14,
  },
  emptyBox: {
    alignItems: "center",
    paddingVertical: 48,
    paddingHorizontal: 24,
  },
  emptyTitle: {
    fontSize: 16,
    fontWeight: "600",
    color: COLORS.textMuted,
  },
  emptySub: {
    marginTop: 8,
    fontSize: 13,
    color: COLORS.textMuted,
    textAlign: "center",
  },
  sectionTitle: {
    fontSize: 17,
    fontWeight: "700",
    color: COLORS.text,
    marginBottom: 12,
  },
});