/**
 * W2-6: 온보딩 — 사업장 등록 + 사용 계정과목 설정.
 * 단일 사용자 인증 없음 (v1 플래그만 AsyncStorage에 저장).
 */
import React, { useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { ACCOUNT_CATEGORIES, CATEGORY_VALUES, OnboardSettings, generateStoreCode, isValidStoreCode } from "../types";
import { COLORS, styles as themeStyles } from "../theme";
import { Button, Input } from "../components/ui";
import { fetchJudgment, JudgmentResult, toKoreanError } from "../api";

export function OnboardingScreen({
  onComplete,
  existing,
}: {
  onComplete: (settings: OnboardSettings) => void;
  existing?: OnboardSettings;
}) {
  const [businessName, setBusinessName] = useState(existing?.businessName ?? "");
  const [storeCode, setStoreCode] = useState(existing?.storeCode ?? "");
  const [storePin, setStorePin] = useState("");
  const [selected, setSelected] = useState<string[]>(
    existing?.categories?.length ? existing.categories : [...CATEGORY_VALUES]
  );
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  // T4: 기장의무 판정 입력 (선택 — 안 하면 건너뜀)
  const [jGroup, setJGroup] = useState(existing?.industryGroup ?? "");
  const [jRevenue, setJRevenue] = useState(
    existing?.prevRevenue != null ? String(existing.prevRevenue) : ""
  );
  const [jResult, setJResult] = useState<JudgmentResult | null>(null);
  const [jBusy, setJBusy] = useState(false);

  const checkJudgment = async () => {
    if (!jGroup) {
      setError("업종군을 선택해 주세요.");
      return;
    }
    const revenue = jRevenue.replace(/[^\d]/g, "");
    if (!revenue) {
      setError("직전연도 매출을 입력해 주세요.");
      return;
    }
    setJBusy(true);
    setError("");
    try {
      setJResult(await fetchJudgment({ industry_group: jGroup, revenue }));
    } catch (e) {
      setError(await toKoreanError(e));
    } finally {
      setJBusy(false);
    }
  };

  const toggle = (value: string) => {
    setSelected((prev) => {
      if (value === "기타") return prev; // 기타는 항상 유지 (분류 실패 대비)
      return prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value];
    });
  };

  const done = async () => {
    const name = businessName.trim();
    if (!name) {
      setError("사업장 이름을 입력해 주세요.");
      return;
    }
    if (!isValidStoreCode(storeCode)) {
      setError("가게 코드는 영문/숫자만 1~16자로 입력해 주세요.");
      return;
    }
    if (!/^\d{4}$/.test(storePin)) {
      setError("PIN은 숫자 4자리로 입력해 주세요.");
      return;
    }
    const categories = selected.includes("기타") ? selected : [...selected, "기타"];
    setSaving(true);
    setError("");
    try {
      await onComplete({
        businessName: name,
        categories,
        storeCode: storeCode.trim(),
        storePin,
        onboarded: true,
        industryGroup: jGroup || undefined,
        prevRevenue: jRevenue.replace(/[^\d]/g, "") || undefined,
      });
    } catch {
      setError("PIN 등록에 실패했습니다. 네트워크를 확인하고 다시 시도해 주세요.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <ScrollView style={themeStyles.screen} contentContainerStyle={styles.content}>
      <Text style={themeStyles.title}>시작하기</Text>
      <Text style={themeStyles.subtitle}>
        영수증 장부 사용을 위한 기본 설정입니다. 1분이면 끝나요.
      </Text>
      <View style={themeStyles.spacer} />

      {error ? (
        <View style={styles.errorBox}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      ) : null}

      <View style={themeStyles.card}>
        <Text style={styles.label}>사업장 이름</Text>
        <Input
          value={businessName}
          onChangeText={setBusinessName}
          placeholder="예: 성수 카페"
        />
        <View style={styles.gap} />
        <Text style={styles.label}>가게 코드</Text>
        <View style={styles.codeRow}>
          <View style={styles.codeInputWrap}>
            <Input
              value={storeCode}
              onChangeText={(t) => setStoreCode(t.replace(/[^A-Za-z0-9]/g, ""))}
              placeholder="예: 7K2M"
            />
          </View>
          <Pressable style={styles.genButton} onPress={() => setStoreCode(generateStoreCode())}>
            <Text style={styles.genButtonText}>자동 생성</Text>
          </Pressable>
        </View>
        <Text style={styles.codeHint}>
          같은 가게에서 쓸 폰들은 같은 코드를 입력하세요. 코드가 다르면 장부가 분리됩니다.{"\n"}
          자동 생성한 코드는 반드시 메모해 두세요 — 잊으면 내보내기 탭에서 확인할 수 있습니다.
        </Text>
        <View style={styles.gap} />
        <Text style={styles.label}>잠금 PIN</Text>
        <Input
          value={storePin}
          onChangeText={(t) => setStorePin(t.replace(/[^0-9]/g, "").slice(0, 4))}
          placeholder="숫자 4자리"
          secureTextEntry
        />
        <Text style={styles.codeHint}>
          가게 코드를 아는 다른 사람도 PIN 없이는 장부를 보거나 수정할 수 없습니다. 같은 가게 폰들은 같은 PIN을 입력하세요.
        </Text>
        <Text style={styles.privacyNote}>
          영수증 이미지는 OCR 인식을 위해 Google(미국) Gemini로, 품목·거래처 분류를 위해 OpenAI(미국)로 전송될 수 있습니다 (개인정보 처리방침 참조). 시작하면 위 내용에 동의한 것으로 간주합니다.
        </Text>
        <View style={styles.gap} />
        <Text style={styles.label}>기장 의무 확인 (선택 — 10초면 끝나요)</Text>
        <Text style={styles.codeHint}>
          업종군과 직전연도 매출을 입력하면 복식부기인지 간편장부인지 알려드립니다.
          모르면 건너뛰어도 됩니다.
        </Text>
        <View style={styles.groupRow}>
          {(["가", "나", "다"] as const).map((g) => (
            <Pressable
              key={g}
              onPress={() => setJGroup(jGroup === g ? "" : g)}
              style={[styles.groupBtn, jGroup === g && { backgroundColor: COLORS.primary }]}
            >
              <Text style={[styles.groupBtnText, jGroup === g && { color: "#FFF" }]}>
                {g === "가" ? "가: 도소매 등" : g === "나" ? "나: 음식점·제조" : "다: 서비스·임대"}
              </Text>
            </Pressable>
          ))}
        </View>
        <TextInput
          style={styles.jRevenueInput}
          value={jRevenue}
          onChangeText={(t) => setJRevenue(t.replace(/[^\d]/g, ""))}
          placeholder="직전연도 매출 (원)"
          keyboardType="number-pad"
        />
        <Button
          label={jBusy ? "판정 중…" : "기장 의무 판정"}
          kind="secondary"
          onPress={checkJudgment}
          loading={jBusy}
          style={{ marginTop: 8 }}
        />
        {jResult ? (
          <View style={styles.jResultBox}>
            <Text style={styles.jResultTitle}>판정 결과: {jResult.obligation}</Text>
            <Text style={styles.jResultReason}>{jResult.reason}</Text>
            <Text style={styles.jResultNote}>
              참고: 간편장부 대상자가 장부를 쓰면 기장세액공제 20%(연 최대 100만 원)를 받을 수 있습니다.
              이 판정은 안내용이며 과세당국의 개별 판단을 대체하지 않습니다.
            </Text>
          </View>
        ) : null}
        <View style={styles.gap} />
        <Text style={styles.label}>
          사용 계정과목 — 장부에서 쓰는 분류만 켜두세요 (기타는 필수)
        </Text>
        <View style={styles.categoryList}>
          {ACCOUNT_CATEGORIES.map((cat) => {
            const active = selected.includes(cat.value);
            const locked = cat.value === "기타";
            return (
              <Pressable
                key={cat.value}
                onPress={() => toggle(cat.value)}
                disabled={locked}
                style={({ pressed }) => [
                  styles.categoryItem,
                  active && styles.categoryItemActive,
                  locked && styles.categoryItemLocked,
                  pressed && { opacity: 0.8 },
                ]}
              >
                <View style={[styles.check, active && styles.checkActive]}>
                  {active ? <Text style={styles.checkMark}>✓</Text> : null}
                </View>
                <View style={styles.categoryTextWrap}>
                  <Text style={[styles.categoryName, active && { color: COLORS.primary }]}>
                    {cat.value}
                  </Text>
                  <Text style={styles.categoryHint}>{cat.hint}</Text>
                </View>
                {locked ? <Text style={styles.lockedText}>필수</Text> : null}
              </Pressable>
            );
          })}
        </View>
      </View>

      <View style={themeStyles.spacer} />
      <Button label="저장하고 시작하기" onPress={done} loading={saving} />
      <Text style={styles.footnote}>
        온보딩 정보는 이 기기에만 저장됩니다. 가게 코드로 같은 장부를 공유합니다.
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: {
    padding: 20,
    paddingBottom: 48,
  },
  label: {
    fontSize: 14,
    fontWeight: "600",
    color: COLORS.textMuted,
    marginBottom: 8,
  },
  gap: {
    height: 18,
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
  },
  categoryList: {
    marginTop: 4,
  },
  categoryItem: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 10,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: COLORS.border,
  },
  categoryItemActive: {
    backgroundColor: COLORS.chipBg,
  },
  categoryItemLocked: {
    opacity: 0.75,
  },
  check: {
    width: 22,
    height: 22,
    borderRadius: 6,
    borderWidth: 2,
    borderColor: COLORS.border,
    alignItems: "center",
    justifyContent: "center",
    marginRight: 10,
  },
  checkActive: {
    backgroundColor: COLORS.primary,
    borderColor: COLORS.primary,
  },
  checkMark: {
    color: "#FFF",
    fontSize: 13,
    fontWeight: "700",
  },
  categoryTextWrap: {
    flex: 1,
  },
  categoryName: {
    fontSize: 15,
    fontWeight: "600",
    color: COLORS.text,
  },
  categoryHint: {
    fontSize: 12,
    color: COLORS.textMuted,
    marginTop: 2,
  },
  lockedText: {
    fontSize: 12,
    fontWeight: "600",
    color: COLORS.textMuted,
  },
  codeRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  codeInputWrap: {
    flex: 1,
  },
  genButton: {
    paddingHorizontal: 14,
    paddingVertical: 12,
    borderRadius: 10,
    backgroundColor: COLORS.primary,
  },
  genButtonText: {
    color: "#FFF",
    fontSize: 13,
    fontWeight: "600",
  },
  codeHint: {
    marginTop: 8,
    fontSize: 12,
    lineHeight: 17,
    color: COLORS.textMuted,
  },
  groupRow: {
    flexDirection: "row",
    gap: 8,
    marginTop: 10,
  },
  groupBtn: {
    flex: 1,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: COLORS.border,
    paddingVertical: 10,
    alignItems: "center",
    backgroundColor: "#FFF",
  },
  groupBtnText: {
    fontSize: 12,
    fontWeight: "700",
    color: COLORS.text,
  },
  jRevenueInput: {
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 15,
    color: COLORS.text,
    backgroundColor: "#FFF",
    marginTop: 10,
  },
  jResultBox: {
    marginTop: 10,
    backgroundColor: "#E8F1FF",
    borderRadius: 10,
    padding: 12,
  },
  jResultTitle: {
    fontSize: 14,
    fontWeight: "800",
    color: COLORS.primaryDark,
  },
  jResultReason: {
    fontSize: 13,
    lineHeight: 19,
    color: COLORS.text,
    marginTop: 4,
  },
  jResultNote: {
    fontSize: 11,
    lineHeight: 16,
    color: COLORS.textMuted,
    marginTop: 6,
  },
  privacyNote: {
    marginTop: 10,
    padding: 10,
    borderRadius: 8,
    backgroundColor: COLORS.chipBg,
    fontSize: 11,
    lineHeight: 16,
    color: COLORS.textMuted,
  },
  footnote: {
    marginTop: 14,
    fontSize: 12,
    lineHeight: 18,
    color: COLORS.textMuted,
    textAlign: "center",
  },
});