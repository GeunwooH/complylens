/**
 * W2-5: 내보내기 + 무통장 결제 진입 화면.
 * - GET /api/export (csv/excel) → 다운로드 & 공유
 * - POST /api/orders → 무통장 입금 안내 화면으로 이동
 */
import React, { useEffect, useState } from "react";
import { Platform, Pressable, StyleSheet, Text, View } from "react-native";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { File, Paths } from "expo-file-system";
import * as Sharing from "expo-sharing";
import * as Clipboard from "expo-clipboard";
import { createBankOrder, fetchExport, toKoreanError, trackEvent } from "../api";
import { loadSettings } from "../settings";
import { currentMonth, shiftMonth } from "../config";
import { RootStackParamList } from "../navigation";
import { COLORS, styles as themeStyles } from "../theme";
import { Button, ErrorBanner, SectionTitle } from "../components/ui";

type Nav = NativeStackNavigationProp<RootStackParamList>;

export function ExportScreen() {
  const navigation = useNavigation<Nav>();
  const [month, setMonth] = useState(currentMonth());
  const [busy, setBusy] = useState<"csv" | "excel" | "order" | null>(null);
  const [error, setError] = useState("");
  const [storeCode, setStoreCode] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    loadSettings().then((s) => setStoreCode(s.storeCode));
  }, []);

  const copyCode = async () => {
    if (!storeCode) return;
    await Clipboard.setStringAsync(storeCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const exportFile = async (format: "csv" | "excel") => {
    setBusy(format);
    setError("");
    try {
      const data = await fetchExport(month, format);
      if (Platform.OS === "web") {
        downloadOnWeb(data.filename, data.mimeType, data.bytes);
      } else {
        const file = new File(Paths.cache, data.filename);
        if (file.exists) file.delete();
        file.write(new Uint8Array(data.bytes));
        if (await Sharing.isAvailableAsync()) {
          await Sharing.shareAsync(file.uri, {
            mimeType: data.mimeType,
            dialogTitle: `${data.filename} 저장/공유`,
          });
        }
      }
      trackEvent("export_downloaded", { format }).catch(() => {});
    } catch (e) {
      setError(await toKoreanError(e));
    } finally {
      setBusy(null);
    }
  };

  const startPayment = async () => {
    setBusy("order");
    setError("");
    try {
      const order = await createBankOrder();
      navigation.navigate("Payment", { order });
      trackEvent("payment_started").catch(() => {});
    } catch (e) {
      setError(await toKoreanError(e));
    } finally {
      setBusy(null);
    }
  };

  const move = (delta: number) => setMonth((m) => shiftMonth(m, delta));

  return (
    <View style={themeStyles.screen}>
      <View style={styles.monthRow}>
        <Button label="‹" kind="secondary" onPress={() => move(-1)} style={styles.monthBtn} />
        <Text style={styles.monthLabel}>{month}</Text>
        <Button label="›" kind="secondary" onPress={() => move(1)} style={styles.monthBtn} />
      </View>
      <View style={styles.content}>
        <ErrorBanner message={error} />

        <SectionTitle>내 가게 코드</SectionTitle>
        <View style={themeStyles.card}>
          <Text style={styles.desc}>
            이 코드를 알면 같은 가게의 다른 폰에서도 같은 장부를 봅니다. 잊지 않도록 메모해 두세요.
          </Text>
          <View style={styles.codeRow}>
            <Text style={styles.codeText}>{storeCode || "—"}</Text>
            <Pressable style={styles.copyBtn} onPress={copyCode}>
              <Text style={styles.copyBtnText}>{copied ? "복사됨 ✓" : "복사"}</Text>
            </Pressable>
          </View>
        </View>
        <View style={themeStyles.spacer} />

        <SectionTitle>장부 내보내기</SectionTitle>
        <View style={themeStyles.card}>
          <Text style={styles.desc}>
            {month} 장부를 신고 준비용 정리 파일로 내보냅니다. (CSV/엑셀 — 적격증빙·신고서 대체 아님)
          </Text>
          <Button
            label="CSV 내보내기"
            onPress={() => exportFile("csv")}
            loading={busy === "csv"}
            style={{ marginTop: 12 }}
          />
          <Button
            label="엑셀 내보내기"
            kind="secondary"
            onPress={() => exportFile("excel")}
            loading={busy === "excel"}
            style={{ marginTop: 10 }}
          />
        </View>

        <View style={themeStyles.spacer} />

        <SectionTitle>결제 안내</SectionTitle>
        <View style={themeStyles.card}>
          <Text style={styles.desc}>
            무료로 월 5장까지 이용할 수 있습니다. 내보내기와 무제한 촬영은 월 9,900원 정액제로
            무통장(계좌이체) 결제 후 사용할 수 있습니다.
          </Text>
          <Button
            label="무통장 입금 안내 받기"
            onPress={startPayment}
            loading={busy === "order"}
            style={{ marginTop: 12 }}
          />
        </View>

        <View style={styles.hintBox}>
          <Text style={styles.hintText}>
            내보낸 파일은 신고 준비용 정리 초안입니다. 적격증빙·세금신고서를 대체하지 않으며, 정확한 신고는 세무사·세무대리인의 검토를 권장합니다.
          </Text>
        </View>
      </View>
    </View>
  );
}

function downloadOnWeb(filename: string, mimeType: string, bytes: ArrayBuffer) {
  if (typeof document === "undefined") return;
  const blob = new Blob([bytes], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

const styles = StyleSheet.create({
  monthRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 14,
    paddingVertical: 14,
  },
  monthBtn: {
    paddingVertical: 6,
    paddingHorizontal: 14,
    minHeight: 36,
  },
  monthLabel: {
    fontSize: 18,
    fontWeight: "700",
    color: COLORS.text,
    minWidth: 110,
    textAlign: "center",
  },
  content: {
    paddingHorizontal: 20,
    paddingBottom: 40,
  },
  desc: {
    fontSize: 14,
    lineHeight: 20,
    color: COLORS.textMuted,
  },
  codeRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginTop: 12,
  },
  codeText: {
    fontSize: 24,
    fontWeight: "800",
    letterSpacing: 4,
    color: COLORS.primaryDark,
  },
  copyBtn: {
    backgroundColor: COLORS.primary,
    borderRadius: 10,
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  copyBtnText: {
    color: "#FFF",
    fontSize: 13,
    fontWeight: "700",
  },
  hintBox: {
    marginTop: 20,
    backgroundColor: COLORS.chipBg,
    borderRadius: 10,
    padding: 14,
  },
  hintText: {
    fontSize: 13,
    lineHeight: 19,
    color: COLORS.primaryDark,
  },
});