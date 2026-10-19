# 텔레그램 알림 (run_research.sh·check_login.sh가 source). 토큰은 자동화-워치독 .env에서 읽는다.
ENV_FILE="$HOME/Projects/도구/자동화-워치독/.env"

notify() {
  local token chat
  token=$(grep -E '^TELEGRAM_BOT_TOKEN=' "$ENV_FILE" | cut -d= -f2-)
  chat=$(grep -E '^TELEGRAM_CHAT_ID=' "$ENV_FILE" | cut -d= -f2-)
  [ -n "$token" ] && [ -n "$chat" ] || return 0
  curl -s -o /dev/null --data-urlencode "chat_id=$chat" --data-urlencode "text=[지식창고 조사] $1" \
    "https://api.telegram.org/bot$token/sendMessage"
}

# Aside 앱이 꺼져 있으면 켠다 (키워드 플래너는 Aside 브라우저로 조회)
ensure_aside() {
  if ! aside repl "console.log('ok')" 2>&1 | grep -q '^ok'; then
    open -ga Aside
    sleep 20
  fi
}
