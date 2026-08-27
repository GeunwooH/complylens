# GLM-5.3 Flash 가격 조사 원장

관찰 시점: 2026-08-27 KST

판정 대상: 정확한 모델 ID `glm-5.3-flash` 또는 제공자 접두사가 붙은 동일 모델

주의: 가격, 모델 목록, 프로모션은 바뀔 수 있으므로 결제 직전에 다시 확인해야 한다.

## 결론

| 비교 기준 | 현재 판정 | 근거와 한계 |
|---|---|---|
| 가장 저렴한 정액 코딩 구독 | **OpenCode Go, $10/month** | 정확한 `GLM-5.3-Flash` 포함. $12/5시간, $30/주, $60/월 한도. 모델 목록·한도 변경 가능 |
| 가장 저렴한 공식 Z.ai 코딩 구독 시작가 | **Z.ai Lite, $18 USD/month** | 공식 문서는 월 18달러부터라고 명시. 한국 결제 최종액은 미확인 |
| 가장 낮은 공개 월 플랫폼 기본료 | **Cloudflare Workers Paid, $5 USD/month** | 정액 코딩 구독이 아니라 종량제 플랫폼. GLM 호출 비용은 별도 계산 |
| 가장 낮은 공개 API 할인 단가 | **$0.075/M 입력, $0.015/M 캐시 입력, $0.25/M 출력** | Z.ai 한시 할인. 2026-09-09 24:00 UTC+8 종료 예정 |
| 한국 사용자의 확정 원화 결제액 | **UNKNOWN** | 카드 승인, 세금, 발급사 환율·해외 결제 수수료가 공개 자료에 없음 |

“구독 플랜”을 정액 코딩 도구로 정의하면 OpenCode Go가 답이다. Cloudflare의 월 5달러는 더 낮은 반복 지출이지만 사용량 기반 플랫폼이라 같은 상품군으로 보지 않았다. Z.ai API와 OpenRouter는 선불 또는 종량제이므로 구독 순위에서 분리했다.

## 주장별 근거

### S1. 모델 정체성과 공식 제공

- 주장: 정확한 모델명은 `GLM-5.3-Flash`이고 Z.ai Coding Plan에서 제공된다.
- 1차 출처: [Z.ai GLM-5.3-Flash 가이드](https://docs.z.ai/guides/vlm/glm-5.3-flash)
- 관찰: 문서 제목과 API 코드가 정확한 모델을 식별하며 Coding Plan 제공을 명시한다.
- 신뢰도: 높음.

### S2. OpenCode Go가 월 10달러 정액 코딩 구독이다

- 주장: OpenCode Go는 월 10달러이며 `GLM-5.3-Flash`를 명시적으로 포함한다.
- 주장: 사용 한도는 금액 기준 $12/5시간, $30/주, $60/월이다.
- 출처: [OpenCode Go 공식 문서](https://opencode.ai/docs/go)
- 관찰: 문서 첫 문단에 `$10/month subscription`이 적혀 있고 모델 목록과 한도 표에 GLM-5.3 Flash 및 세 구간 한도가 나온다.
- 조건: 모델 목록과 한도는 변경될 수 있다. 제한 도달 후 별도 Zen 잔액 폴백을 켜지 않으면 유료 요청이 막힌다. 한국 발급 카드 승인 여부는 문서로 확인되지 않았다.
- 신뢰도: 높음.

### S3. Z.ai Coding Plan은 월 18달러부터다

- 주장: Z.ai GLM Coding Plan의 공개 시작가는 `18 USD per month`이다.
- 출처: [Z.ai Coding Plan 개요](https://docs.z.ai/devpack/overview)
- 보조 출처: [Z.ai Quick Start](https://docs.z.ai/guides/overview/quick-start)
- 관찰: 개요에 `Starting at just 18 USD per month`가 명시돼 있다.
- 신뢰도: 높음.

### S4. Z.ai Lite 현재 크레딧 한도

- 주장: Lite는 5시간 2,000크레딧, 주간 10,000크레딧이다.
- 출처: [Z.ai Coding Plan 개요의 Usage 섹션](https://docs.z.ai/devpack/overview#usage-instructions)
- 관찰: 현재 크레딧 기반 표에 Lite 2,000/10,000, Pro 12,000/60,000, Max 28,000/140,000이 나온다.
- 주의: 과거의 “80회/400회” 수치는 현재 신규 플랜 한도가 아니라 레거시 참고치다.
- 신뢰도: 높음.

### S5. Coding Plan 크레딧은 일반 API 잔액이 아니다

- 주장: Coding Plan은 지원되는 코딩 도구용이며 일반 애플리케이션·봇·웹사이트·SaaS API 사용권이 아니다.
- 출처: [Z.ai Subscription Terms](https://docs.z.ai/legal-agreement/subscription-terms)
- 보조 출처: [Z.ai Coding Plan FAQ](https://docs.z.ai/devpack/faq)
- 관찰: 약관은 지원되는 코딩 도구 밖의 일반 API 사용을 제한하고, FAQ는 플랜 사용이 일반 API 잔액을 차감하지 않는다고 설명한다.
- 신뢰도: 높음.

### S6. Cloudflare는 월 5달러 플랫폼이지만 정액 GLM 구독은 아니다

- 주장: Workers Paid의 기본료는 월 5달러다.
- 출처: [Cloudflare Workers Pricing](https://developers.cloudflare.com/workers/platform/pricing/)
- 주장: Cloudflare에서 정확한 `@cf/zai-org/glm-5.3-flash` 모델을 제공한다.
- 출처: [Cloudflare GLM-5.3-Flash 모델 페이지](https://developers.cloudflare.com/workers-ai/models/glm-5.3-flash/)
- 주장: Workers AI는 포함량 이후 모델별 종량 가격을 적용한다.
- 출처: [Cloudflare Workers AI Pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/)
- 조건: 월 5달러는 코딩 구독료나 무제한 모델 사용료가 아니다.
- 신뢰도: 높음.

### S7. Z.ai API 한시 할인 단가와 종료 시점

- 주장: GLM-5.3-Flash 할인 단가는 100만 토큰당 입력 $0.075, 캐시 입력 $0.015, 출력 $0.25다.
- 주장: 할인 종료는 2026-09-09 24:00 UTC+8이다.
- 출처: [Z.ai API Pricing](https://docs.z.ai/guides/overview/pricing)
- 관찰: 정가 $0.15/$0.03/$0.50에 취소선을 긋고 할인 단가와 종료 시각을 표시한다.
- 계산: 100만 입력 + 100만 출력 = `$0.075 + $0.25 = $0.325`.
- 조건: 한시 가격이며 공개 페이지에 최소 충전액은 없다.
- 신뢰도: 높음.

### S8. OpenRouter는 월 구독이 아니라 선불 종량제다

- 주장: 정확한 모델 ID `z-ai/glm-5.3-flash`의 제공자별 단가가 존재한다.
- 출처: [OpenRouter endpoint API](https://openrouter.ai/api/v1/models/z-ai/glm-5.3-flash/endpoints)
- 주장: 최소 크레딧 구매액은 $5이고 결제 수수료가 붙을 수 있다.
- 출처: [OpenRouter Terms §4.1](https://openrouter.ai/terms#4_1-pre-paid-credits-refunds), [OpenRouter FAQ](https://openrouter.ai/docs/faq)
- 조건: $5는 추론 비용이 아니라 잔액 구매액이다. Stripe는 5.5% 또는 최소 $0.80 수수료가 명시돼 있다.
- 신뢰도: 높음.

### S9. 공개 가중치는 무료 구독이 아니다

- 주장: 공식 가중치는 MIT 메타데이터와 함께 공개됐지만, 무료 호스팅·전기·하드웨어를 뜻하지 않는다.
- 출처: [Hugging Face zai-org/GLM-5.3-Flash](https://huggingface.co/zai-org/GLM-5.3-Flash), [모델 API 메타데이터](https://huggingface.co/api/models/zai-org/GLM-5.3-Flash)
- 신뢰도: 높음.

## 장점 판정 근거

- OpenCode Go: 공개 월 가격과 세 구간 사용 한도가 있어 예산을 이해하기 쉽다.
- Z.ai Coding Plan: 공식 경로이며 문서에 Claude Code, Cline, OpenCode 등의 지원 도구가 나온다.
- API: 호출량이 적으면 월 정액료보다 총액이 낮아질 수 있다. 이는 워크로드에 따라 달라지는 조건부 장점이다.

## 단점 및 미확인 사항

- OpenCode Go는 모델 목록과 한도를 변경할 수 있다고 명시한다.
- Z.ai 구독 크레딧은 일반 API 잔액으로 쓸 수 없다.
- Cloudflare·Z.ai API·OpenRouter는 사용량 기반이므로 월 총액이 고정되지 않는다.
- 어느 승자 후보도 한국 발급 카드 승인, 한국 세금 포함 여부, 발급사 환율·해외 결제 수수료를 보장하지 않는다.
- Z.ai 개인 정보 처리방침만으로 Coding Plan 입력의 zero retention 또는 no-training을 단정할 수 없다.

## 제외한 표현

- “Z.ai 월 18달러가 전체 최저가다.”: OpenCode Go 월 10달러가 반례다.
- “Cloudflare 월 5달러가 가장 싼 정액 코딩 구독이다.”: 종량제 플랫폼이다.
- “OpenRouter는 5달러에 쓸 수 있다.”: 5달러는 최소 잔액 구매이고 수수료가 별도다.
- “무료로 무제한 사용한다.”: 공개 채팅·플레이그라운드·가중치에는 지속 가능한 무료 호스팅 한도가 없다.
- “한국 사용자는 정확히 10달러만 낸다.”: 세금·환율·카드 수수료를 확인하지 못했다.
