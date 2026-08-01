# Autonomous Ops — 자율 운영 상태 (2026-08-01)

> 원칙: 사용자 명령 없이 에이전트가 스스로 상태를 감시하고 개선한다.

## 활성 감시 (monitor)
| 채널 | 주기 | 감시 대상 | 장애 시 |
|---|---|---|---|
| html.npopo.com health | 5분 | HTTP 200 | ALERT 이벤트 → 진단/복구 |
| Cloudflare 터널 | 지속 | cloudflared 프로세스 | 재시작 (nohup) |
| uvicorn 서버 | 지속 | :8000 | 재시작 |

## 서브에이전트 워크로드 (상태)
| 워커 | 역할 | 상태 | 다음 행동 |
|---|---|---|---|
| SEO 콘텐츠 | 블로그 주 2편 | 5편 완료 | 방법론/다중관할/감사관/IL/기본 |
| 디렉토리 아웃리치 | 벤더 5곳 등록 문의 | 초안 완료 | 발송 대기 (Gmail SMTP 설정 시 자동화) |
| 결제 감시 | 주문 API + txid 검증 | 가동 중 | 주문 발생 시 자동 납품 |
| 소비자 전환 | preview/신뢰 페이지 | 완료 | 전환율 측정 (주문 로그) |

## 소비자 관점 회귀 체크 (완료)
- preview.html: 무료 미리보기 + CTA → 지갑 열기 유도
- about/privacy: 신뢰 신호 → "익명 사이트" 해소
- invoice 옵션: 크립토 없는 소비자도 결제 가능

## 다음 자율 주기 (세션 재개 시 자동)
1. 모니터 ALERT 확인 → 장애 복구
2. 주문/결제 로그 점검 → 미확인 결제 처리
3. 디렉토리 응답 확인 (수신 메일 없음 — SMTP 설정 후 발송)
4. SEO 키워드 실측 ("LL144 bias audit" SERP)

## 이메일 인프라 발견 (2026-08-01)
- npopo.com에 Cloudflare Email Routing MX (route1~3.mx.cloudflare.net) + SPF(google 포함) 활성
- audit@npopo.com 수신 가능 인프라 존재 → G2/Capterra/Product Hunt 회사 이메일 인증 + 고객 문의 수신에 활용 가능
- 확인 필요: 포워딩 대상 주소 (아마 npopo86@gmail.com — Cloudflare 대시보드 확인)
