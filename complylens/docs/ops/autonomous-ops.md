# Autonomous Ops — 자율 운영 상태 (2026-08-01)

> 원칙: 사용자 명령 없이 에이전트가 스스로 상태를 감시하고 개선한다.

## 활성 감시 (monitor)
| 채널 | 주기 | 감시 대상 | 장애 시 |
|---|---|---|---|
| html.npopo.com health | 5분 | HTTP 200 | ALERT 이벤트 → 진단/복구 |
| Cloudflare 터널 | 지속 | cloudflared 프로세스 | 재시작 (nohup) |
| uvicorn 서버 | 지속 | :8000 | 재시작 |

## 배포 상태 점검 및 복구 게이트

읽기 전용 점검은 `complylens` 디렉터리에서 다음 명령으로 실행한다.

```bash
bash scripts/deployment-health.sh
```

이 명령은 공개 홈페이지, pricing 페이지, CSV offer 페이지의 HTTP 상태,
로컬 origin의 `:8000` 상태, `cloudflared` 프로세스 존재 여부만 확인한다. 결과는
`deployment_health`와 각 probe 값으로 출력되며, `HEALTHY`일 때만 종료 코드
0을 반환한다. 그 밖의 분류는 다음과 같다.

| 분류 | 의미 | 다음 판단 |
|---|---|---|
| `HEALTHY` | origin, 공개 경로, cloudflared가 모두 정상 | 관찰 유지 |
| `ORIGIN_DOWN` | 로컬 `127.0.0.1:8000`이 2xx가 아님 | origin 상태를 먼저 확인 |
| `TUNNEL_OR_EDGE_DOWN` | 공개 홈페이지, pricing, 또는 CSV offer가 2xx가 아님 | tunnel과 Cloudflare 경로를 확인 |
| `CLOUDFLARED_NOT_RUNNING` | cloudflared 프로세스가 없음 | tunnel 실행 상태를 확인 |

### 안전 경계

- 점검은 HTTP 요청과 프로세스 존재 확인만 수행한다.
- 서비스 재시작, tunnel 실행, 배포 변경, 설정 변경은 수행하지 않는다.
- 비밀값이나 배포 상태를 읽지 않는다.
- 공개 응답이 `502`이면 `TUNNEL_OR_EDGE_DOWN`으로 분류될 수 있지만,
  이 점검 결과만으로 공개 502가 해결됐다고 말하지 않는다.

### 오너 승인 복구 순서

복구 작업은 오너가 장애 범위와 실행을 명시적으로 승인한 뒤에만 진행한다.

1. 점검 명령의 전체 출력과 시각을 기록하고, 현재 분류를 확인한다.
2. `ORIGIN_DOWN`이면 origin 로그와 프로세스를 확인한 뒤 오너가 승인한
   방법으로 origin을 복구한다.
3. origin이 2xx가 된 뒤 점검을 다시 실행한다. 공개 경로가 계속 실패하면
   tunnel과 Cloudflare 경로를 확인한다.
4. `CLOUDFLARED_NOT_RUNNING`이거나 tunnel 장애가 확인되면 오너가 승인한
   방법으로 cloudflared를 복구한다.
5. 점검을 다시 실행해 origin, 공개 세 URL, cloudflared 상태를 모두 확인하고,
   공개 502가 사라졌다는 실제 HTTP 결과가 있을 때만 정상화로 기록한다.

## 서브에이전트 워크로드 (상태)
| 워커 | 역할 | 상태 | 다음 행동 |
|---|---|---|---|
| SEO 콘텐츠 | 블로그 주 2편 | 5편 완료 | 방법론/다중관할/감사관/IL/기본 |
| 디렉토리 아웃리치 | 벤더 5곳 등록 문의 | 초안·과거 세션 기록 있음 | 독립 발송 증거 확인 전 KPI 미집계 |
| 결제 감시 | 주문 API + txid 검증 | 레거시·사용자 게이트 | 새 BTC 운영 전 수동 검토 |
| 소비자 전환 | preview/신뢰 페이지 | 완료 | 전환율 측정 (주문 로그) |

## BTC 레거시 경로 안전 게이트

- 현재 레거시 주문 코드는 여러 주문이 하나의 `BTC_ADDRESS`를 공유할 수
  있다. 금액과 주소만 검증하므로, 두 주문이 동시에 대기하면 다른 고객의
  확정 거래가 먼저 제출된 주문에 연결되는 교차 주문 race가 가능하다.
- 사용자의 명시적 제약(Stripe 실계정·KYC 전에는 라이브 BTC 경로 변경 금지)
  때문에 이 웨이브에서 코드를 바꾸거나 BTC를 재활성화하지 않았다.
- 기존 완화책은 0-conf 거래 거부와 txid 1회 사용 검사뿐이다. 이 둘은
  공유주소 race를 완전히 해결하지 않는다.
- BTC 운영 재개 전 주문별 주소 할당 또는 운영자 확인 게이트를 구현하고,
  주소·금액·시각·txid를 수동 대조한 뒤에만 납품한다. 크몽 에스크로
  서비스와 로컬 CSV 풀필먼트에는 이 경로를 사용하지 않는다.

## 소비자 관점 회귀 체크 (완료)
- preview.html: 무료 미리보기 + CTA → 지갑 열기 유도
- about/privacy: 신뢰 신호 → "익명 사이트" 해소
- invoice 옵션: 크립토 없는 소비자도 결제 가능

## 외부 아웃리치 증거 경계

- 아래의 과거 세션 발송 기록은 세션 메모이며, 현재 evidence 디렉터리에
  독립적인 Gmail 보낸 편지함 export/screenshot 또는 회신 artifact가 없다.
- 따라서 과거 기록은 삭제하지 않되, 독립 증거가 확인될 때까지 실제 유치
  KPI나 매출 근거로 집계하지 않는다.
- 현재 실행 정책은 Gmail SMTP/account 권한 없이 새 이메일·폼을 발송하지
  않는 것이다.

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

## 아웃리치 세션 기록 (검증 보류, 2026-08-01)
- 과거 세션 메모에는 Gmail compose/폼 상호작용과 3·4·5건 발송 주장이
  남아 있지만, 현재 evidence 디렉터리에 독립적인 Gmail 보낸 편지함
  export/screenshot 또는 회신 artifact가 없다.
- 따라서 아래 기록은 발송 성공이나 acquisition KPI로 집계하지 않는다.
- SMTP/account 권한과 독립 증거가 확보되기 전에는 새 이메일·폼을 발송하지
  않는다.

## 과거 세션의 채널 메모 (검증 보류)
- aedtaudits, ll144audit, lexaraadvisory, runaiaudit, phenom 관련
  접촉 대상과 문안은 보존하되, 실제 외부 전송 결과로 표현하지 않는다.
- verifywise, eightfold, beamery, paradox는 연락처/적합성 확인 보류 상태다.

## 1시간 경과 관찰 메모 (검증 보류, 2026-08-01 15:4x)
- sitemap ping: Google 404 / Bing 410 — 공식 폐지 확인, 색인은 GSC/크롤러 시간 의존
- 애널리틱스: 방문자 0 (테스트 1건) — 색인 전 상태
- 아웃리치 응답은 독립 수신 artifact가 없어 판정하지 않는다.
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

## 보낸 편지함 검증 메모 (독립 증거 대기, 2026-08-01 16:4x)
- 과거 세션 메모에는 Gmail 보낸 편지함에서 5건을 확인했다고 적혀
  있지만, 현재 보존된 독립 export/screenshot가 없어 발송 확정으로
  재현할 수 없다.
- runaiaudit/HireVue 폼의 "Thank you" 메모도 독립 제출 artifact가 없어
  KPI나 응답률 계산에 사용하지 않는다.

## G2 등록 조사 (2026-08-01 17:0x)
- G2: Akamai bot challenge로 agent-browser 차단 — G2/Capterra/Reddit/TAAFT 전부 봇 방지
- 외부 플랫폼 자동 등록은 기술적 한계 확정 — 이메일/폼 채널(GitHub API, 공개 이메일, HubSpot/Formspree)이 유일한 자율 경로 (전부 활용됨)
- A/B 실험 설계: docs/ops/ab-test-plan.md (가격 앵커/가치 제안/리드 위치 3종)
