# SOC2 Founding Pre-sale Experiment

## 가설

가격에 밀린 소규모 SaaS 팀이 SOC2 Type I 준비의 scope/evidence coordination
문제를 해결하기 위해 $49 고정가 evidence binder를 구매한다.

## 실험 설계

- 제품: `p6-soc2` — SOC2 Under $5k Startup Playbook v1
- 기간: 14일 from first public launch
- 기준: `orders/`에서 유료 주문 20건 이상
- 측정: 주문 생성 수, confirmed 수, 리드 수, 유입 경로, 환불 요청
- 현재 기준선: 2026-08-01, confirmed 유료 주문 0건

## 운영 규칙

20건은 **확장 규모를 결정하는 기준**이지 개발·광고를 멈추는 조건이 아니다.
선판매 기간에도 제품 사용성, 카피, 유입 채널, 증거 조정 기능을 계속 개선한다.
결제 확인은 `daily-report.sh`와 크론으로 자동 집계하며, 사람이 결제 화면을
계속 감시하는 작업은 하지 않는다.

### 성공

- 20건 이상 confirmed 주문: 현재 채널을 확대하고 update pass($99/year),
  auditor-affiliate 유통, ISO 42001 upsell을 순서대로 개발한다.
- 10~19건: 카피·채널·온보딩 중 하나를 조정하고 7일 재검증한다.

### 가설 전환

- 14일 후 confirmed 주문 10건 미만: SOC2 **현재 가설**(ICP, 메시지, 채널)을
  실패로 기록한다.
- 개발·광고를 중단하지 않고, evidence coordination 메시지·기존 ComplyLens
  pipeline용 vendor-risk 메시지·Article 50 메시지를 병렬 실험한다.
- 3일마다 최소 한 가지 유입 자산 또는 제품 개선을 배포한다.

## 주장 경계

- “SOC2 compliant”, “certified”, “audit pass guaranteed”를 사용하지 않는다.
- 독립 CPA의 SOC 2 attestation을 대체하지 않는다.
- 가격은 준비용 정보상품의 가격이며 감사인·도구·수정 비용을 포함하지 않는다.

## 운영 명령

```sh
COMPLYLENS_API_KEY=dev bash scripts/daily-report.sh
```

일일 보고는 주문/리드 수를 자동 기록하는 용도다. 테스트 주문은 실험 지표에서
제외하고, 운영 시간은 개선 작업에 사용한다.
