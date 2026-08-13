# Campaign scheduling and launch readiness

이 문서는 실행 가능한 준비물만 정의한다. 외부 계정·크론·이메일·폼을
자동으로 변경하지 않는다.

## Readiness checks

```bash
cd /path/to/complylens
uv run python scripts/stripe-staging-preflight.py --json
uv run python scripts/llm-routing-audit.py --json
test -x scripts/daily-report.sh
test -x scripts/followup-builder.py
```

- Stripe preflight가 `ready`가 아니면 결제 테스트를 시작하지 않는다.
- sensitive LLM audit가 `ready`가 아니면 PII가 포함된 데이터를 provider에
  보내지 않는다.
- campaign observation log를 먼저 만들고 source/product/window/pivot rule을
  고정한다.

## Read-only report schedule

호스트 소유자가 승인한 뒤에만 다음 예시를 사용자 환경의 crontab에 등록한다.

```cron
0 * * * * cd /path/to/complylens && COMPLYLENS_DATA_DIR=/path/to/data ./scripts/daily-report.sh >> /path/to/logs/complylens-daily.log 2>&1
```

등록 전 확인:

```bash
crontab -l
crontab -e
```

이 작업은 주문·리드·페이지뷰를 읽기만 하며, 에이전트는 현재 crontab을
수정하지 않는다.

## Campaign launch gate

1. 사용자가 채널과 대상 목록을 승인한다.
2. SMTP/계정 권한과 외부 write 범위를 확인한다.
3. `evidence/deeplink-experiment/campaign-observation-log.md`의 기간과
   판정 규칙을 복사하지 않고 그대로 사용한다.
4. 브라우저에서 CTA의 source/product query를 확인한다.
5. 외부 발송 전 dry-run receipt를 저장한다.
6. 14일 또는 30 pageview 중 먼저 도달한 시점에만 판정한다.

승인 전에는 준비 문안과 로컬 QA만 수행하고, 이메일·폼·커뮤니티·유료
광고를 전송하지 않는다.
