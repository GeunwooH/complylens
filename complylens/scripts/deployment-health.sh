#!/usr/bin/env bash
# Read-only Cloudflare/origin health classification.
set -u

if [[ "${1:-}" == "--help" ]]; then
  cat <<'EOF'
Read-only ComplyLens deployment health check.
Probes public homepage/pricing/CSV offer, local port 8000, and cloudflared presence.
It never restarts services, reads secrets, or changes deployment state.
EOF
  exit 0
fi

probe() {
  local url="$1"
  local status
  if status="$(
    curl --silent --show-error --max-time 10 \
      --output /dev/null --write-out '%{http_code}' "$url" 2>/dev/null
  )"; then
    printf '%s' "$status"
  else
    printf 'ERR'
  fi
}

is_2xx() {
  [[ "$1" =~ ^2[0-9][0-9]$ ]]
}

public_home="$(probe 'https://html.npopo.com/')"
public_pricing="$(probe 'https://html.npopo.com/pricing.html')"
public_offer="$(probe 'https://html.npopo.com/kmong-csv-profile.html')"
local_origin="$(probe 'http://127.0.0.1:8000/')"
if pgrep -x cloudflared >/dev/null 2>&1; then
  cloudflared="present"
else
  cloudflared="absent"
fi

if ! is_2xx "$local_origin"; then
  classification="ORIGIN_DOWN"
elif ! is_2xx "$public_home" || ! is_2xx "$public_pricing" || ! is_2xx "$public_offer"; then
  classification="TUNNEL_OR_EDGE_DOWN"
elif [[ "$cloudflared" != "present" ]]; then
  classification="CLOUDFLARED_NOT_RUNNING"
else
  classification="HEALTHY"
fi

printf 'deployment_health=%s\n' "$classification"
printf 'public_home=%s\n' "$public_home"
printf 'public_pricing=%s\n' "$public_pricing"
printf 'public_offer=%s\n' "$public_offer"
printf 'local_origin=%s\n' "$local_origin"
printf 'cloudflared=%s\n' "$cloudflared"

if [[ "$classification" == "HEALTHY" ]]; then
  exit 0
fi
exit 1
