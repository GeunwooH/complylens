/**
 * 온보딩 설정 저장소 — AsyncStorage 단일 사용자 플래그 (v1, 인증 없음).
 */
import AsyncStorage from "@react-native-async-storage/async-storage";
import { OnboardSettings, CATEGORY_VALUES } from "./types";

const KEY = "receipt-app:onboard:v1";

export async function loadSettings(): Promise<OnboardSettings> {
  try {
    const raw = await AsyncStorage.getItem(KEY);
    if (!raw) return defaultSettings();
    const parsed = JSON.parse(raw) as Partial<OnboardSettings>;
    return {
      businessName: typeof parsed.businessName === "string" ? parsed.businessName : "",
      categories: Array.isArray(parsed.categories) ? parsed.categories : [...CATEGORY_VALUES],
      storeCode: typeof parsed.storeCode === "string" ? parsed.storeCode : "",
      storePin: typeof parsed.storePin === "string" ? parsed.storePin : "",
      onboarded: Boolean(parsed.onboarded),
    };
  } catch {
    return defaultSettings();
  }
}

export async function saveSettings(settings: OnboardSettings): Promise<void> {
  await AsyncStorage.setItem(KEY, JSON.stringify(settings));
}

export function defaultSettings(): OnboardSettings {
  return {
    businessName: "",
    categories: [...CATEGORY_VALUES],
    storeCode: "",
    storePin: "",
    onboarded: false,
  };
}