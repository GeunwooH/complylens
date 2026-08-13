# 내PC제어 프로젝트 규칙 (ComplyLens 사업 운영)

## 메모리 (세션 간 지속)

**이 프로젝트의 세션 시작 시 반드시 아래를 읽고, 새 세션이라도 동일한 에이전트로서 행동한다:**

1. `~/.senpi/memory/identity.md` — 에이전트 정체성 (말투·성격·전문성·금기·작업 스타일)
2. `~/.senpi/memory/long-term.md` — 사용자 선호·프로젝트 컨텍스트·결정 사항
3. `~/.senpi/memory/daily/$(date +%Y-%m-%d).md` — 오늘 일일 로그 (없으면 생성)
4. `~/.senpi/memory/index.md` — 최근 7일 요약 (빠른 복귀용)

**규칙:**
- 기억이 비어 보여도 이전 세션의 로그를 먼저 찾아보고, "아는 척"이 아니라 "로그 기반"으로 행동한다.
- 세션 간 충돌(다른 세션이 상태 변경) 발견 시 사용자에게 보고하고 조정한다.
- 사용자 승인 없는 외부 게시·배포·결제·커밋은 금지.

## 회고 일기 (활동한 날만)

**작업을 한 날의 세션 종료 시 `~/.senpi/memory/memory-diary.sh` 로 오늘의 회고를 남긴다.**
- **1주일 이상 아무 작업도 안 했다면 일기 생략 가능** (스크립트가 자동 감지해 안내한다)
- 작업이 있었으면 세션 종료 전 반드시 기록

회고 일기에는 반드시 6가지:
- 오늘 한 일 (무엇을 했나)
- 잘한 것 / 성과
- 잘못한 것 / 실수 (솔직하게 — 숨기지 않는다)
- 원인 분석 (왜 그랬나)
- 내일은 이렇게 (개선 액션 — 구체적으로)
- 오늘의 교훈 / 메모

빠른 기록: `memory-diary.sh "요약"` (오늘 한 일에 추가), 상세 기록: `memory-diary.sh` (파일 직접 편집)

## 모델 폴백 (유동적 대응)

- 모델 실패 시 `~/.omo/omo.jsonc`의 `[senpi].categories.*.fallback_models` 체인이 자동으로 다음 모델로 폴백한다.
- 현재 체인: commandcode/deepseek-v4-flash → opencode/deepseek-v4-flash-free → alibaba-token-plan/deepseek-v4-flash-0731 → openai-codex/gpt-5.6-luna → kimi-coding/kimi-for-coding-highspeed
- **새 모델이 등록되면 `senpi --list-models`로 카탈로그를 갱신하면 폴백 체인에 자동 반영된다** (수동 추가 불필요 — provider 연결 상태 기반).
- 특정 실행에서 폴백을 끄려면 `--no-model-fallback` 플래그 사용.
- 모델 실패가 잦으면: (1) 인증 상태 확인 (`senpi auth`), (2) 카탈로그 갱신 (`senpi update`), (3) 체인 재정렬 순으로 대응한다.
