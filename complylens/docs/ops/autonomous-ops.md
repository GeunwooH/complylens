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

## 아웃리치 발송 상태 (2026-08-01)
- Gmail 웹 UI 발송 시도: 컴퓨터-유즈 좌표 클릭이 Safari/Aside 웹 콘텐츠에 전달되지 않아 실패 (2회)
- Email Routing 확인: me@npopo.com 존재 + 사용자 테스트 완료 — npopo.com 메일 수신 인프라 작동
- 대안 경로: (1) Gmail SMTP 앱 비밀번호 (사용자 1분 설정) → curl/python으로 5건 자동 발송,
  (2) mailto 초안 (docs/ops/outreach-emails.md) — 사용자가 1클릭으로 발송
- 결정: SMTP 설정 전까지 SEO/사이트가 주 유치 채널 (에이전트 완전 자율)

## 구매자 여정 QA (agent-browser, 2026-08-01)
- 실제 Chromium 렌더: 랜딩(타이틀/CTA/벌금 계산기), pricing(제품 4종/환불 보장) 확인
- 주문 API 실측: fetch POST /api/orders → 200 (2d4c90f13896, 0.00075 BTC, 지갑 주소)
- 폼 JS 화면 갱신은 eval 타이밍 문제 — API/데이터 흐름 정상
- 도구: agent-browser 0.33.1 (npx) — 외부 플랫폼(Product Hunt/G2) 등록은 새 프로필에 로그인 세션 없어 Gmail OAuth 필요 → 사용자 세션 필요 항목으로 유지

## GitHub 유치 채널 (2026-08-01)
- 공개 repo: https://github.com/GeunwooH/complylens — README에 제품 5종 + html.npopo.com 링크 5개 (백링크)
- 효과: Google 크롤러가 GitHub 링크로 색인 발견 + 개발자/스타트업 커뮤니티 노출
- 다음: ACLU LL144 트래커 기여 (github.com/aclu-national/tracking-ll144-bias-audits) — 포크 + 최신 감사 데이터 추가 시도

## GitHub 채널 완성 (2026-08-01)
- complylens repo: README(제품5+링크5) + LICENSE(MIT) + topics 5개
- 프로필 README (github.com/GeunwooH): ComplyLens 소개 + 링크 3개
- 백링크 총 8개 — Google 색인 발견 트리거 + 커뮤니티 노출

## 아웃리치 발송 성공 (2026-08-01) 🎯
- **방법**: Gmail compose URL(미리 채운 작성 창) + Cmd+Enter — SMTP 없이 발송 성공
- **발송 3건**: aedtaudits(등재 문의) · ll144audit(비교 페이지 등재) · lexaraadvisory(교차 리퍼럴)
- runaiaudit/verifywise: 이메일 미공개(연락 폼만) — 폼 제출은 별도 경로
- 다음: 응답 모니터링 (Gmail 수신 — 주기 확인)

## 아웃리치 4건 완료 (2026-08-01)
- runaiaudit.com: agent-browser DOM 조작으로 Formspree 폼 제출 성공 (필드 리셋 = 전송 확인)
- verifywise.ai: 연락처 미공개 (JS 렌더) — 보류
- 발송 4건: aedtaudits / ll144audit / lexaraadvisory (이메일) + runaiaudit (폼)
- 도구: agent-browser (DOM 기반 — 좌표 클릭 문제 우회)

## 아웃리치 5건 완료 (2026-08-01)
- phenom.com (ATS 벤더) 파트너십 제안 — support@phenompeople.com
- 발송 5건: aedtaudits / ll144audit / lexaraadvisory / runaiaudit(폼) / phenom
- eightfold/beamery: 이메일 미공개, paradox: media@만 공개(부적합) — 보류

## 1시간 경과 실측 (2026-08-01 15:4x)
- sitemap ping: Google 404 / Bing 410 — 공식 폐지 확인, 색인은 GSC/크롤러 시간 의존
- 애널리틱스: 방문자 0 (테스트 1건) — 색인 전 상태
- 아웃리치 응답: 5건 모두 미회신 (정상 — 수시간~수일 소요)
- 지갑: 0 BTC · 주문 7건(전부 테스트) · 리드 1건(테스트)

## CSP 수정 후 전환 퍼널 회귀 (2026-08-01 15:5x)
- Playwright 실검증: 퀴즈(결과 표시) / 계산기($67,500) / 주문 폼(지갑 표시) / 문의 폼(리드 저장) / 리드 마그넷(리드 저장) — 전부 ✅
- 리드 2건 실저장: qaform@test.com, qalead@test.com (테스트)
- 전환 퍼널 5개 요소 전부 동작 — 구매 가능 상태 확정

## GitHub Discussions 채널 활성화 (2026-08-01)
- has_discussions=true (API) + 첫 게시물: github.com/GeunwooH/complylens/discussions/1
- "ComplyLens launched" — 제품 소개 + 질문 유도 (LL144/방법론/다중관할 AMA)
- 효과: GitHub 커뮤니티 노출 + Discussion 페이지도 검색 색인 (고권위 백링크)

## 카드 결제(Lemon Squeezy) 시도 결과 (2026-08-01)
- 가입 흐름: 비즈니스 정보 → Managed Payments(Stripe merchant of record) 온보딩 개입
- 여러 단계 시도 후 정체 — Stripe KYC(사업자 정보)는 에이전트 불가
- 결론: 카드 결제 수신은 **사용자 KYC 필요 항목 확정** (skeptic A2 권고 — BTC 전용은 전환율 자해,
  카드가 필요하나 수신 활성화는 사용자 몫). 크립토+invoice는 자율 가동 중.

## 모바일 반응형 검증 (2026-08-01 16:2x)
- Playwright 375x812 뷰포트: / /pricing.html /ll144-guide.html 전부 가로 오버플로 없음
- 헤더 스택/CTA 전체 폭 정상 — dev #6 (@media) 실검증 완료

## 보낸 편지함 검증 (2026-08-01 16:4x)
- Gmail 보낸 편지함 실측: 아웃리치 5건(이메일) 전부 기록 확인
  lets.talk(idiro) / support(phenom) / advisory(lexaraadvisory) / support(ll144audit) / vedvyas(aedtaudits)
- 발송 확정 (토스트 외 2차 검증) — 폼 제출 2건(runaiaudit/HireVue)은 "Thank you" 확인
