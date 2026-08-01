# A/B 실험 설계 — 전환 최적화 (2026-08-01)

> 목적: 트래픽이 발생하기 시작하면 즉시 실행할 실험 설계. skeptic A3(툴킷 포지셔닝)
> 와 dev #4(가치 사다리)의 검증.
> 실행 조건: 주간 방문자 100+ 또는 아웃리치 응답으로 첫 리드 발생 시.

## 실험 1: 가격 앵커 (pricing.html)

| 항목 | A (현재) | B (실험) |
|---|---|---|
| 상단 제품 | Readiness $299 | **$299 + "was $499" 앵커** |
| 제품 순서 | Vendor $29 → Readiness $299 | Readiness $299 → Vendor $29 (앵커링) |
| CTA 문구 | "Start with the Readiness Toolkit" | "Get compliant in 72 hours" |

측정: /api/pv (pricing.html) 대비 주문 생성률 — 주문/방문 비율.
판정: 30일간 주문률 +0.5pp 이상이면 B 채택.

## 실험 2: 랜딩 가치 제안 (index.html)

| 항목 | A (현재) | B (실험) |
|---|---|---|
| H1 | "NYC Local Law 144 Compliance Analysis, delivered in 72 hours" | "Avoid $270,000 in LL144 penalties — compliant in 72 hours" |
| 상단 CTA | email us | "Start free quiz" (퀴즈로 유도) |

측정: 퀴즈 시작률 + 리드 캡처율 (리드/방문).
판정: 리드율 2x 이상이면 B 채택.

## 실험 3: 리드 마그넷 위치 (preview/quiz)

| 항목 | A (현재) | B (실험) |
|---|---|---|
| 프리뷰 리드 폼 위치 | 하단 | **상단 (2섹션 직후)** |
| 퀴즈 결과 CTA | 제품 링크 | **체크리스트 다운로드 + 제품 링크** |

측정: 리드/방문 비율.

## 측정 인프라 (이미 가동)

- /api/pv: 페이지뷰 (경로별 집계)
- /api/leads: 리드 (메시지로 실험 태그 — "QUIZ:" 등)
- 주문: 상태별 추적
- daily-report.sh: 일일 요약

## 실행 조건 및 절차

1. 조건 충족 (주간 100+ 방문 또는 첫 유료 리드) 확인
2. 정적 HTML 변경 (A/B는 페이지 복제가 아닌 순차 적용 — v1은 단순함 우선)
3. 7일 측정 후 판정 (애널리틱스 by_path)
4. 채택 시 기본 페이지 갱신 + 체크포인트 기록
