# 텔레그램 알림 (run_research.sh가 source). 토큰은 자동화-워치독 .env에서 읽는다.
ENV_FILE="$HOME/Projects/도구/자동화-워치독/.env"

notify() {
  local token chat
  token=$(grep -E '^TELEGRAM_BOT_TOKEN=' "$ENV_FILE" | cut -d= -f2-)
  chat=$(grep -E '^TELEGRAM_CHAT_ID=' "$ENV_FILE" | cut -d= -f2-)
  [ -n "$token" ] && [ -n "$chat" ] || return 0
  curl -s -o /dev/null --data-urlencode "chat_id=$chat" --data-urlencode "text=[지식창고 조사] $1" \
    "https://api.telegram.org/bot$token/sendMessage"
}

