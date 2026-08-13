/**
 * 영수증 장부 — 소상공인용 영수증 촬영 → OCR → 장부 자동화 (Wave 2).
 * Root 스택: Onboarding(조건부) → Main 탭(촬영/장부/내보내기) + Payment(푸시).
 */
import React, { useEffect, useState } from "react";
import { Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { StatusBar } from "expo-status-bar";
import { loadSettings, saveSettings } from "./src/settings";
import { setStoreCode, setStorePin, flushUploadQueue, setupStorePin, trackEvent } from "./src/api";
import { OnboardSettings } from "./src/types";
import { RootStackParamList, TabParamList } from "./src/navigation";
import { COLORS } from "./src/theme";
import { OnboardingScreen } from "./src/screens/OnboardingScreen";
import { CaptureScreen } from "./src/screens/CaptureScreen";
import { LedgerScreen } from "./src/screens/LedgerScreen";
import { ExportScreen } from "./src/screens/ExportScreen";
import { PaymentScreen } from "./src/screens/PaymentScreen";

const Stack = createNativeStackNavigator<RootStackParamList>();
const Tab = createBottomTabNavigator<TabParamList>();

function TabLabel({ name, active }: { name: string; active: boolean }) {
  return <Text style={{ fontSize: 11, color: active ? COLORS.primary : "#9AA5B1" }}>{name}</Text>;
}

function MainTabs({ activeCategories }: { activeCategories: string[] }) {
  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: true,
        tabBarActiveTintColor: COLORS.primary,
        tabBarInactiveTintColor: "#9AA5B1",
        headerTitleAlign: "center",
        headerStyle: { backgroundColor: COLORS.bg },
        headerShadowVisible: false,
      }}
    >
      <Tab.Screen
        name="Capture"
        options={{
          title: "촬영",
          tabBarLabel: "촬영",
          headerTitle: "영수증 촬영",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="camera" size={size} color={color} />
          ),
        }}
      >
        {() => <CaptureScreen activeCategories={activeCategories} />}
      </Tab.Screen>
      <Tab.Screen
        name="Ledger"
        options={{
          title: "장부",
          tabBarLabel: "장부",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="book" size={size} color={color} />
          ),
        }}
        component={LedgerScreen}
      />
      <Tab.Screen
        name="Export"
        options={{
          title: "내보내기",
          tabBarLabel: "내보내기",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="download" size={size} color={color} />
          ),
        }}
        component={ExportScreen}
      />
    </Tab.Navigator>
  );
}

export default function App() {
  const [settings, setSettings] = useState<OnboardSettings | null>(null);

  useEffect(() => {
    loadSettings().then((loaded) => {
      setStoreCode(loaded.storeCode);
      setStorePin(loaded.storePin);
      setSettings(loaded);
      // 기존 설치자 마이그레이션: 저장된 PIN을 백엔드에 자동 등록 (실패해도 무해 — 다음 기회)
      if (loaded.storeCode && loaded.storePin) {
        setupStorePin(loaded.storeCode, loaded.storePin).catch(() => {});
      }
    });
    // D1: 앱 시작 시 오프라인 대기열 자동 재시도
    flushUploadQueue().catch(() => {});
    // G7: 앱 시작(재방문) 이벤트 — 같은 코호트의 D7/D30 측정 기준
    trackEvent("app_open").catch(() => {});
  }, []);

  // 로딩 중 — 스플래시 역할
  if (!settings) {
    return (
      <View style={{ flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: COLORS.bg }}>
        <Text style={{ fontSize: 18, fontWeight: "700", color: COLORS.primary }}>영수증 장부</Text>
        <Text style={{ marginTop: 8, fontSize: 13, color: "#718A95" }}>불러오는 중…</Text>
      </View>
    );
  }

  if (!settings.onboarded || !settings.storeCode || !settings.storePin) {
    return (
      <SafeAreaProvider>
        <StatusBar style="dark" />
        <OnboardingScreen
          existing={settings}
          onComplete={async (next) => {
            try {
              await setupStorePin(next.storeCode, next.storePin);
            } catch {
              // 등록 실패해도 저장 진행 — 다음 API 호출에서 apiFetch가 428 자동 복구
            }
            await saveSettings(next);
            setStoreCode(next.storeCode);
            setStorePin(next.storePin);
            setSettings(next);
          }}
        />
      </SafeAreaProvider>
    );
  }

  return (
    <SafeAreaProvider>
      <NavigationContainer>
        <Stack.Navigator
          initialRouteName="Main"
          screenOptions={{
            headerTitleAlign: "center",
            headerStyle: { backgroundColor: COLORS.bg },
            headerShadowVisible: false,
            headerTintColor: COLORS.primaryDark,
            contentStyle: { backgroundColor: COLORS.bg },
          }}
        >
          <Stack.Screen name="Main" options={{ headerShown: false }}>
            {() => <MainTabs activeCategories={settings.categories} />}
          </Stack.Screen>
          <Stack.Screen
            name="Payment"
            component={PaymentScreen}
            options={{ title: "무통장 결제" }}
          />
        </Stack.Navigator>
      </NavigationContainer>
    </SafeAreaProvider>
  );
}