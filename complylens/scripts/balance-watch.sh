#!/usr/bin/env bash
set -euo pipefail
ADDR="1C1mjuJ1ox3YgxT6Jq7FA6YjrjXb319nr7"
LOG="docs/ops/balance.log"
DATA=$(curl -s --max-time 10 "https://blockstream.info/api/address/${ADDR}" 2>/dev/null || echo "{}")
BAL=$(echo "$DATA" | python3 -c "import json,sys; d=json.load(sys.stdin); print((d['chain_stats']['funded_txo_sum']-d['chain_stats']['spent_txo_sum'])/1e8)" 2>/dev/null || echo "ERR")
TX=$(echo "$DATA" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['chain_stats']['tx_count'])" 2>/dev/null || echo "?")
if [ ! -f "$LOG" ]; then
  echo "$(date '+%Y-%m-%d %H:%M') 잔액: ${BAL} BTC (${TX}건)" > "$LOG"
  echo "로그 초기화: ${BAL} BTC"
elif [ "$BAL" != "ERR" ]; then
  LAST=$(tail -1 "$LOG")
  if ! echo "$LAST" | grep -q " ${BAL} BTC (${TX}건)"; then
    echo "$(date '+%Y-%m-%d %H:%M') 잔액: ${BAL} BTC (${TX}건) ← 변화!" >> "$LOG"
    echo "지갑 변화 감지: ${BAL} BTC (${TX}건)"
  fi
fi
