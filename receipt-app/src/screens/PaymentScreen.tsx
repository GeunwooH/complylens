/**
 * W2-5: 무통장(계좌이체) 입금 안내 화면.
 * POST /api/orders 결과(계좌 + 입금 안내) 표시, 입금 확인 → PATCH confirm.
 */
import React, { useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { RouteProp, useRoute } from "@react-navigation/native";
import { confirmBankOrder, toKoreanError, trackEvent } from "../api";
import { fmtWon } from "../config";
import { RootStackParamList } from "../navigation";
import { COLORS, styles as themeStyles } from "../theme";
import { Chip, Button, ErrorBanner, InfoRow, Spinner } from "../components/ui";

type Route = RouteProp<RootStackParamList, "Payment">;

export function PaymentScreen() {
  const route = useRoute<Route>();
  const [order, setOrder] = useState(route.params.order);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const confirm = async () => {
    setBusy(true);
    setError("");
    try {
      const status = await confirmBankOrder(order.order_id);
      setOrder((o) => ({ ...o, status }));
      trackEvent("payment_confirmed", { product: order.product_id }).catch(() => {});
    } catch (e) {
      setError(await toKoreanError(e));
    } finally {
      setBusy(false);
    }
  };

  const confirmed = order.status === "confirmed" || order.status === "completed";

  return (
    <View style={themeStyles.screen}>
      <View style={styles.content}>
        <Text style={themeStyles.title}>무통장 입금 안내</Text>
        <Text style={themeStyles.subtitle}>아래 계좌로 입금을 완료해 주세요.</Text>
        <View style={themeStyles.spacer} />

        <ErrorBanner message={error} />
        {busy ? <Spinner label="처리 중…" /> : null}

        <View style={themeStyles.card}>
          <View style={styles.productRow}>
            <Text style={styles.productName}>{order.product_name || "영수증 장부 Light"}</Text>
            <Chip
              label={
                confirmed
                  ? "입금 확인됨"
                  : order.status === "awaiting_payment"
                    ? "입금 대기"
                    : order.status
              }
              tone={confirmed ? "good" : "warn"}
            />
          </View>
          <View style={styles.bankBox}>
            <Text style={styles.amount}>{fmtWon(order.amount_krw)}</Text>
            <Text style={styles.bankLine}>
              {order.bank.bank} {order.bank.account_number}
            </Text>
            <Text style={styles.holder}>예금주: {order.bank.holder}</Text>
          </View>
          <InfoRow label="주문번호" value={order.order_id} />
          <View style={styles.instructionsBox}>
            <Text style={styles.instructionsTitle}>입금 방법</Text>
            <Text style={styles.instructionsText}>{order.instructions}</Text>
          </View>
        </View>

        <View style={themeStyles.spacer} />
        <Button
          label={confirmed ? "입금 확인 완료" : "입금했습니다 — 확인"}
          onPress={confirm}
          loading={busy}
          disabled={confirmed}
        />
        <Text style={styles.footnote}>
          입금 후 확인 버튼을 누르면 구독이 시작됩니다. 확인 전까지는 결제가 진행되지
          않습니다.
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  content: {
    padding: 20,
  },
  productRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 14,
  },
  productName: {
    fontSize: 16,
    fontWeight: "700",
    color: COLORS.text,
  },
  bankBox: {
    backgroundColor: "#F7FAFC",
    borderRadius: 12,
    borderWidth: 1,
    borderColor: COLORS.border,
    padding: 16,
    alignItems: "center",
    marginBottom: 8,
  },
  amount: {
    fontSize: 26,
    fontWeight: "800",
    color: COLORS.primary,
    marginBottom: 6,
  },
  bankLine: {
    fontSize: 16,
    fontWeight: "700",
    color: COLORS.text,
  },
  holder: {
    fontSize: 13,
    color: COLORS.textMuted,
    marginTop: 4,
  },
  instructionsBox: {
    marginTop: 14,
    backgroundColor: COLORS.chipBg,
    borderRadius: 10,
    padding: 14,
  },
  instructionsTitle: {
    fontSize: 13,
    fontWeight: "700",
    color: COLORS.primaryDark,
    marginBottom: 6,
  },
  instructionsText: {
    fontSize: 13,
    lineHeight: 20,
    color: COLORS.primaryDark,
  },
  footnote: {
    marginTop: 12,
    fontSize: 12,
    lineHeight: 18,
    color: COLORS.textMuted,
  },
});