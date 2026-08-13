/** 내비게이션 타입 — Root 스택 + 메인 탭 */
import { NavigatorScreenParams } from "@react-navigation/native";
import { BankOrder } from "./types";

export type TabParamList = {
  Capture: undefined;
  Ledger: undefined;
  Export: undefined;
};

export type RootStackParamList = {
  Onboarding: undefined;
  Main: NavigatorScreenParams<TabParamList>;
  Payment: { order: BankOrder };
};