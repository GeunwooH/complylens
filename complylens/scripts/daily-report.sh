#!/usr/bin/env bash
# ComplyLens 일일 상태 요약 — 사용법: bash scripts/daily-report.sh
set -euo pipefail

DATA_DIR="${COMPLYLENS_DATA_DIR:-/tmp/complylens-html}"
BTC_ADDR="${BTC_ADDRESS:-1C1mjuJ1ox3YgxT6Jq7FA6YjrjXb319nr7}"

echo "=== ComplyLens 상태 요약 $(date '+%Y-%m-%d %H:%M') ==="

SITE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 https://html.npopo.com/ 2>/dev/null || echo "ERR")
echo "사이트: ${SITE}"

WALLET=$(curl -s --max-time 10 "https://blockstream.info/api/address/${BTC_ADDR}" 2>/dev/null \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"{d['chain_stats']['funded_txo_sum']/1e8:.8f} BTC ({d['chain_stats']['tx_count']}건)\")" 2>/dev/null || echo "확인 불가")
echo "지갑: ${WALLET}"

ORDERS=$(ls "${DATA_DIR}/orders/"*.json 2>/dev/null | wc -l | tr -d ' ')
LEADS=$(ls "${DATA_DIR}/leads/"*.json 2>/dev/null | wc -l | tr -d ' ')
echo "주문: ${ORDERS}건 | 리드: ${LEADS}건"

echo "--- 최근 주문 ---"
for f in $(ls -t "${DATA_DIR}/orders/"*.json 2>/dev/null | head -3); do
  python3 -c "
import json
d = json.load(open('$f'))
print(f\"{d['order_id']} | {d['email']} | {d['product_name'][:30]} | {d['status']} | {d['created_at'][:16]}\")
" 2>/dev/null || true
done

if [ -n "${COMPLYLENS_API_KEY:-}" ]; then
  PV=$(curl -s -H "X-API-Key: ${COMPLYLENS_API_KEY}" --max-time 10 https://html.npopo.com/api/stats 2>/dev/null \
    | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['total'])" 2>/dev/null || echo "확인 불가")
  echo "페이지뷰: ${PV}"
else
  echo "페이지뷰: (COMPLYLENS_API_KEY 미설정 — 생략)"
fi

echo "--- 최근 리드 ---"
for f in $(ls -t "${DATA_DIR}/leads/"*.json 2>/dev/null | head -3); do
  python3 -c "
import json
d = json.load(open('$f'))
print(f\"{d['lead_id']} | {d['email']} | {d['message'][:40]} | {d['created_at'][:16]}\")
" 2>/dev/null || true
done

echo "=== 끝 ==="
