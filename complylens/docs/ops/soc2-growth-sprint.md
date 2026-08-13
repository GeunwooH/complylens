# SOC2 7-Day Growth Sprint

## 목적

`p6-soc2`를 더 만드는 것이 아니라, 어떤 채널이 evidence coordination
구매로 이어지는지 측정한다. 결제 확인은 크론과 `daily-report.sh`로 자동화하고,
사람의 시간은 아웃리치·콘텐츠·제품 개선에 쓴다.

## 채널 우선순위

1. startup-focused CPA/SOC2 auditor partner
2. SaaS founder/security leader direct outreach
3. owned SEO/checklist funnel
4. 질문에 답하는 비스팸 커뮤니티 참여

대량 스팸, 자동 댓글, “SOC2 pass 보장” 주장은 금지한다. 실제 이메일·폼
제출은 Gmail SMTP 또는 해당 계정 권한이 필요하므로, 이 문서는 발송 목록과
문안까지만 자동 준비한다.

## 감사 파트너 10개

| 우선 | 대상 | 적합성 | 근거 | 공개 연락 경로 |
|---:|---|---|---|---|
| 1 | Schellman | SOC2 페이지에 초기기업용 `SOC Essentials` 명시 | https://www.schellman.com/services/soc-compliance-and-attestations/soc-2 | https://www.schellman.com/contact-us |
| 2 | Kruze Consulting | VC-funded startup 전문 CPA; 감사 준비·소개 파트너 | https://kruzeconsulting.com/ | https://kruzeconsulting.com/free-consultation/ |
| 3 | Linford & Company | SOC1/SOC2 전문 부티크 CPA | https://linfordco.com/services/soc-2-audits/ | https://linfordco.com/contact/ |
| 4 | A-LIGN | SOC2와 사이버 컴플라이언스 전문 | https://www.a-lign.com/service/soc-2 | https://www.a-lign.com/contact |
| 5 | RSM | early-stage startup부터 SaaS·emerging tech까지 지원 | https://rsmus.com/industries/technology.html | https://rsmus.com/contact.html |
| 6 | Coalfire | SaaS 고객과 SOC assessment 서비스 | https://coalfire.com/services/assessment | https://coalfire.com/about/contact-us |
| 7 | Baker Tilly | System & Organization Controls reporting 서비스 | https://www.bakertilly.com/services/system-and-organization-controls-soc-reporting | https://www.bakertilly.com/contact |
| 8 | Plante Moran | technology companies 산업·assurance 채널 | https://www.plantemoran.com/industries/technology-companies | https://www.plantemoran.com/contact-us |
| 9 | Wipfli | technology 산업·assurance/risk advisory | https://www.wipfli.com/industries/tech | https://www.wipfli.com/contact |
| 10 | Richey May | technology/media와 risk/compliance assurance | https://richeymay.com/compliance-risk/assurance/ | https://richeymay.com/contact-us/ |

Schellman·Kruze·RSM은 startup/SOC2 문구가 직접 확인된 고신뢰 대상이다.
나머지는 회사 사이트의 내비게이션/서비스 페이지로 적합성을 확인했으며,
폼 제출 전에 링크가 현재 유효한지 다시 클릭한다. 개인 이메일은 추측하지
않는다.

## UTM 규칙

허용 키: `source`, `utm_source`, `utm_medium`, `utm_campaign`, `utm_content`.
모든 값은 주문 JSON에 trim 후 최대 80자로 저장한다.

예시:

```text
https://html.npopo.com/blog/soc2-evidence-gap-check.html?utm_source=auditor&utm_medium=partner&utm_campaign=soc2-v1
https://html.npopo.com/blog/soc2-evidence-gap-check.html?utm_source=founder&utm_medium=direct&utm_campaign=soc2-v1
https://html.npopo.com/blog/soc2-evidence-gap-check.html?utm_source=community&utm_medium=answer&utm_campaign=soc2-v1
```

## 7일 순서

### Day 1 — 계측

- source/UTM을 blog → checklist → pricing → order JSON까지 보존한다.
- 페이지뷰는 `/api/pv`, 주문 attribution은 `orders/*.json`에서 집계한다.
  `daily-report.sh`는 사이트·지갑·주문·리드의 기본 상태를 자동 출력한다.

### Day 2 — 감사 파트너 10곳

공개 contact 경로에서 다음 문안을 회사별로 한 문장 개인화한다.

> Subject: Free SOC2 evidence-gap checklist for startup clients  
>
> We made a short checklist for small SaaS teams preparing for a SOC 2 Type I
> conversation. It focuses on named owners and reproducible evidence rather
> than selling a GRC platform. If it is useful for your startup clients, may we
> share a partner-ready link? We do not claim certification or audit outcomes.

### Day 3 — 창업자/security 담당자 20명

> Before buying a SOC2 platform, this free ten-minute checklist helps a small
> SaaS team find missing evidence owners and links:
> https://html.npopo.com/blog/soc2-evidence-gap-check.html?utm_source=founder&utm_medium=direct&utm_campaign=soc2-v1
>
> It is a readiness screen, not an audit or certification.

대상 기준: 최근 SOC2 요구를 공개적으로 언급한 B2B SaaS, 보안 담당자가
확인되는 2~30인 회사, 또는 vendor-security questionnaire를 운영하는 팀.

### Day 4 — CTA 실험

- A: `Use the free evidence-gap checklist`
- B: `Find your five auditor blockers in ten minutes`
- 한 번에 한 문구만 바꾸고 source별 pricing 진입·주문을 비교한다.

### Day 5 — 제품 사용성

- 첫 화면에서 scope owner와 evidence link를 먼저 안내한다.
- “포함하지 않는 것” FAQ를 추가해 audit/certification 오해를 줄인다.

### Day 6 — 커뮤니티

SOC2 비용·범위 질문에 먼저 실질적인 답변을 쓰고, 질문과 직접 관련될 때만
체크리스트 링크를 한 번 첨부한다. 자동 게시하지 않는다.

### Day 7 — 판정

- `pageview → pricing → order create → confirmed`를 source별로 비교한다.
- 20건 이상이면 update pass·auditor affiliate·ISO upsell 순서로 확장한다.
- 20건 미만이어도 개발·광고를 멈추지 않고 ICP·메시지·채널 중 하나를 바꾼다.

## 운영 명령

```sh
COMPLYLENS_API_KEY=dev bash scripts/daily-report.sh
```

결제 모니터는 자동 보고용이다. 사람이 상시 지갑을 감시하지 않는다.
