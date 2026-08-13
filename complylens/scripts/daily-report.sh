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

ORDERS=0
for file in "${DATA_DIR}/orders/"*.json; do
  [ -e "$file" ] || continue
  ORDERS=$((ORDERS + 1))
done
LEADS=0
for file in "${DATA_DIR}/leads/"*.json; do
  [ -e "$file" ] || continue
  LEADS=$((LEADS + 1))
done
echo "주문: ${ORDERS}건 | 리드: ${LEADS}건"

echo "--- 최근 주문 ---"
python3 - "${DATA_DIR}/orders" <<'PY'
import json
import sys
from pathlib import Path

directory = Path(sys.argv[1])
paths = sorted(
    (path for path in directory.glob("*.json") if path.is_file()),
    key=lambda path: path.stat().st_mtime,
    reverse=True,
)[:3]
for path in paths:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        print(
            f"{data['order_id']} | {data['email']} | "
            f"{data['product_name'][:30]} | {data['status']} | "
            f"{data['created_at'][:16]}"
        )
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"unreadable order {path.name}: {exc}", file=sys.stderr)
PY

if [ -n "${COMPLYLENS_API_KEY:-}" ]; then
  PV=$(curl -s -H "X-API-Key: ${COMPLYLENS_API_KEY}" --max-time 10 https://html.npopo.com/api/stats 2>/dev/null \
    | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['total'])" 2>/dev/null || echo "확인 불가")
  echo "페이지뷰: ${PV}"
else
  echo "페이지뷰: (COMPLYLENS_API_KEY 미설정 — 생략)"
fi

echo "--- 최근 리드 ---"
python3 - "${DATA_DIR}/leads" <<'PY'
import json
import sys
from pathlib import Path

directory = Path(sys.argv[1])
paths = sorted(
    (path for path in directory.glob("*.json") if path.is_file()),
    key=lambda path: path.stat().st_mtime,
    reverse=True,
)[:3]
for path in paths:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        print(
            f"{data['lead_id']} | {data['email']} | "
            f"{data['message'][:40]} | {data['created_at'][:16]}"
        )
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"unreadable lead {path.name}: {exc}", file=sys.stderr)
PY

echo "=== 끝 ==="
