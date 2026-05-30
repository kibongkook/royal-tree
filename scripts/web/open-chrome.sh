#!/usr/bin/env bash
# Open isolated Chrome (RoyalTreeWeb profile, CDP 9224) to Cloudflare API Tokens page.
# Singleton + port guard. Used as a fresh tab for OAuth/REST-API token operations.
set -euo pipefail

PROFILE_DIR="$HOME/Library/Application Support/Google/Chrome/RoyalTreeWeb"
CDP_PORT=9224
START_URL="${1:-https://dash.cloudflare.com/profile/api-tokens}"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# Singleton guard — if instance already running, just add tab via CDP
if pgrep -f "user-data-dir=$PROFILE_DIR" >/dev/null 2>&1; then
  echo "RoyalTreeWeb already running — opening tab via CDP"
  curl -s -X PUT "http://localhost:$CDP_PORT/json/new?$START_URL" >/dev/null
  exit 0
fi

# Port conflict check
if lsof -nP -iTCP:"$CDP_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  OWNER_DIR=$(ps -ww -o command= -p "$(lsof -nP -iTCP:"$CDP_PORT" -sTCP:LISTEN -F p | awk '/^p/{sub(/^p/,""); print; exit}')" \
              | grep -oE 'user-data-dir=[^ ]+' || true)
  if [[ "$OWNER_DIR" != "user-data-dir=$PROFILE_DIR" ]]; then
    echo "[err] port $CDP_PORT already taken by: $OWNER_DIR" >&2
    exit 1
  fi
fi

mkdir -p "$PROFILE_DIR"
"$CHROME" \
  --user-data-dir="$PROFILE_DIR" \
  --remote-debugging-port="$CDP_PORT" \
  '--remote-allow-origins=*' \
  --restore-last-session \
  --no-first-run --no-default-browser-check \
  --disable-features=LockProfileCookieDatabase \
  "$START_URL" >/dev/null 2>&1 &

echo "RoyalTreeWeb started (PID $!, CDP $CDP_PORT)"
