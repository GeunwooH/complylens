/**
 * W2-2: 촬영/갤러리 → 업로드 → OCR 결과 카드.
 * 카메라 권한 + 갤러리 권한 처리, 업로드 중 스피너, 한국어 오류 메시지.
 */
import React, { useRef, useState } from "react";
import {
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { CameraView, useCameraPermissions } from "expo-camera";
import * as ImagePicker from "expo-image-picker";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useNavigation } from "@react-navigation/native";
import { uploadReceipt, toKoreanError, enqueueUpload, isOfflineError, loadUploadQueue, flushUploadQueue, trackEvent } from "../api";
import { COLORS, styles as themeStyles } from "../theme";
import { ReceiptCard as CardType } from "../types";
import { RootStackParamList } from "../navigation";
import { ReceiptCard } from "../components/ReceiptCard";
import { Button, ErrorBanner, Spinner } from "../components/ui";

const ABS_FILL = { position: "absolute" as const, top: 0, left: 0, right: 0, bottom: 0 };

export function CaptureScreen({
  activeCategories,
}: {
  activeCategories?: string[];
}) {
  const navigation =
    useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const cameraRef = useRef<CameraView>(null);
  const [permission, requestPermission] = useCameraPermissions();
  const [mode, setMode] = useState<"idle" | "camera">("idle");
  const [busy, setBusy] = useState(false);
  const [card, setCard] = useState<CardType | null>(null);
  const [error, setError] = useState("");

  const clearAll = () => {
    setCard(null);
    setError("");
    setMode("idle");
  };

  /** 카드 초기화 후 바로 카메라 재진입 (B1 재촬영 UX). */
  const reshoot = () => {
    clearAll();
    openCamera();
  };

  const handleUpload = async (source: { uri: string; name: string; type: string }) => {
    setBusy(true);
    setError("");
    try {
      const result = await uploadReceipt(source);
      setCard(result);
      setMode("idle");
      trackEvent("receipt_uploaded", {
        needs_review: result.needs_review,
        duplicate: Boolean((result as { duplicate?: boolean }).duplicate),
      }).catch(() => {});
    } catch (e) {
      // D1: 오프라인/타임아웃이면 대기열에 저장하고 안내
      if (isOfflineError(e)) {
        try {
          const queue = await enqueueUpload(source);
          setError(
            `네트워크가 불안정해 대기열에 저장했습니다. (대기 ${queue.length}건) 연결되면 자동으로 업로드됩니다.`
          );
        } catch {
          setError(await toKoreanError(e));
        }
      } else {
        setError(await toKoreanError(e));
        trackEvent("receipt_upload_failed").catch(() => {});
      }
    } finally {
      setBusy(false);
    }
  };

  /** 앱 시작/화면 진입 시 대기열 자동 재시도 (D1). */
  const retryQueue = async () => {
    const queue = await loadUploadQueue();
    if (!queue.length) return;
    setBusy(true);
    try {
      const { uploaded, pending } = await flushUploadQueue();
      if (uploaded > 0) setError(`대기 중이던 영수증 ${uploaded}건을 업로드했습니다.`);
      else if (pending > 0) setError(`대기열 ${pending}건 — 네트워크 연결을 확인해 주세요.`);
    } finally {
      setBusy(false);
    }
  };

  const openCamera = async () => {
    setError("");    if (!permission?.granted) {
      const res = await requestPermission();
      if (!res.granted) {
        setError("카메라 권한이 없습니다. iOS 설정 > 개인정보 보호에서 권한을 허용해 주세요.");
        return;
      }
    }
    setMode("camera");
  };

  const capture = async () => {
    if (!cameraRef.current) return;
    const photo = await cameraRef.current.takePictureAsync({ quality: 0.9 });
    if (!photo?.uri) {
      setError("사진을 찍지 못했습니다. 다시 시도해 주세요.");
      return;
    }
    await handleUpload({ uri: photo.uri, name: "receipt.jpg", type: "image/jpeg" });
  };

  const pickFromGallery = async () => {
    setError("");
    if (Platform.OS !== "web") {
      const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!perm.granted) {
        setError("사진 보관함 권한이 필요합니다. iOS 설정에서 권한을 허용해 주세요.");
        return;
      }
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.9,
    });
    if (result.canceled || !result.assets?.length) return;
    const asset = result.assets[0];
    const name = asset.fileName ?? "receipt.jpg";
    const type = asset.mimeType ?? "image/jpeg";
    await handleUpload({ uri: asset.uri, name, type });
  };

  return (
    <View style={themeStyles.screen}>
      {/* 업로드 진행 중 오버레이 */}
      {busy ? (
        <View style={styles.overlay}>
          <Spinner label="영수증 인식 중… (최대 30초)" />
        </View>
      ) : null}

      {mode === "camera" ? (
        <View style={styles.cameraWrap}>
          <CameraView ref={cameraRef} style={ABS_FILL} facing="back" />
          <View style={styles.cameraControls}>
            <Pressable style={styles.shutter} onPress={capture}>
              <View style={styles.shutterInner} />
            </Pressable>
            <Pressable style={styles.cameraCancel} onPress={() => setMode("idle")}>
              <Text style={styles.cameraCancelText}>취소</Text>
            </Pressable>
          </View>
        </View>
      ) : (
        <ScrollView contentContainerStyle={styles.content}>
          {card ? (
            <View key={card.receipt_id}>
              <Text style={themeStyles.title}>인식 결과</Text>
              <Text style={themeStyles.subtitle}>
                금액·품목·분류를 탭해서 바로 수정할 수 있어요.
              </Text>
              <View style={themeStyles.spacer} />
              <ReceiptCard
                card={card}
                activeCategories={activeCategories}
                onUpdated={setCard}
                onViewLedger={() => navigation.navigate("Main", { screen: "Ledger" })}
              />
              <Button
                label="새 영수증 촬영"
                kind="secondary"
                onPress={reshoot}
                style={{ marginTop: 12 }}
              />
            </View>
          ) : (
            <View>
              <Text style={themeStyles.title}>영수증 장부</Text>
              <Text style={themeStyles.subtitle}>
                영수증을 찍으면 AI가 품목·금액·분류를 자동 인식해 장부에 기록합니다.
              </Text>
              <View style={themeStyles.spacer} />
              <ErrorBanner message={error} />
              <Button label="카메라로 촬영" onPress={openCamera} />
              <Button
                label="갤러리에서 선택"
                kind="secondary"
                onPress={pickFromGallery}
                style={{ marginTop: 10 }}
              />
              <View style={styles.hintBox}>
                <Text style={styles.hintText}>
                  인식 결과는 장부에 자동 저장됩니다. 틀린 부분은 수정 후 다시 저장하면
                  AI가 다음부터 더 정확하게 인식해요.
                </Text>
              </View>
            </View>
          )}
        </ScrollView>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  content: {
    padding: 20,
  },
  overlay: {
    ...ABS_FILL,
    backgroundColor: "rgba(255,255,255,0.92)",
    zIndex: 10,
    justifyContent: "center",
  },
  cameraWrap: {
    flex: 1,
    backgroundColor: "#000",
  },
  cameraControls: {
    position: "absolute",
    bottom: 40,
    left: 0,
    right: 0,
    alignItems: "center",
  },
  shutter: {
    width: 72,
    height: 72,
    borderRadius: 36,
    borderWidth: 4,
    borderColor: "#FFF",
    alignItems: "center",
    justifyContent: "center",
  },
  shutterInner: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: "#FFF",
  },
  cameraCancel: {
    marginTop: 18,
    padding: 8,
  },
  cameraCancelText: {
    color: "#FFF",
    fontSize: 16,
  },
  hintBox: {
    marginTop: 24,
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