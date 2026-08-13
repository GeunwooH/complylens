/** 공용 테마 — 소상공인용 간결한 한국어 UI */
import { StyleSheet } from "react-native";

export const COLORS = {
  primary: "#2B6CB0",
  primaryDark: "#1E4E8C",
  bg: "#F5F7FA",
  card: "#FFFFFF",
  border: "#E2E8F0",
  text: "#1A202C",
  textMuted: "#718096",
  success: "#2F855A",
  danger: "#C53030",
  warn: "#B7791F",
  chipBg: "#EBF4FF",
};

export const SHADOW = {
  shadowColor: "#000",
  shadowOpacity: 0.06,
  shadowRadius: 6,
  shadowOffset: { width: 0, height: 2 },
  elevation: 2,
};

export const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: COLORS.bg,
  },
  card: {
    backgroundColor: COLORS.card,
    borderRadius: 14,
    padding: 16,
    borderWidth: 1,
    borderColor: COLORS.border,
    ...SHADOW,
  },
  title: {
    fontSize: 24,
    fontWeight: "700",
    color: COLORS.text,
  },
  subtitle: {
    fontSize: 14,
    color: COLORS.textMuted,
    marginTop: 4,
  },
  label: {
    fontSize: 13,
    fontWeight: "600",
    color: COLORS.textMuted,
    marginBottom: 6,
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
  },
  spacer: {
    height: 16,
  },
});

/** 공용 버튼 스타일 참조용 */
export const buttonStyles = StyleSheet.create({
  primary: {
    backgroundColor: COLORS.primary,
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: "center",
  },
  primaryText: {
    color: "#FFF",
    fontSize: 16,
    fontWeight: "700",
  },
  secondary: {
    backgroundColor: "#EDF2F7",
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: "center",
  },
  secondaryText: {
    color: COLORS.primaryDark,
    fontSize: 16,
    fontWeight: "600",
  },
});