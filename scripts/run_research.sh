#!/bin/bash
# 지식창고 글감 조사 자동 실행 (launchd: 월·수·금 14:00, 13:55 pmset 깨우기에 맞춤). 2026-10-15 사용자 지시: 명령 기다리지 말고 규칙대로.
set -u
cd "$HOME/Projects/지식창고" || exit 1
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:/usr/bin:/bin"
LOG="logs/research-$(date +%Y-%m-%d).log"
ENV_FILE="$HOME/Projects/도구/자동화-워치독/.env"

notify() {
  local token chat
  token=$(grep -E '^TELEGRAM_BOT_TOKEN=' "$ENV_FILE" | cut -d= -f2-)
  chat=$(grep -E '^TELEGRAM_CHAT_ID=' "$ENV_FILE" | cut -d= -f2-)
  [ -n "$token" ] && [ -n "$chat" ] || return 0
  curl -s -o /dev/null --data-urlencode "chat_id=$chat" --data-urlencode "text=[지식창고 조사] $1" \
    "https://api.telegram.org/bot$token/sendMessage"
}

{
  echo "=== $(date '+%F %T') 시작"
  # 잠자기에서 막 깨면 네트워크가 늦게 붙는다(10/16 ERR_INTERNET_DISCONNECTED). 최대 10분 기다림.
  for _ in $(seq 1 30); do
    curl -s -m 5 -o /dev/null https://keywordad.kakao.com && break
    sleep 20
  done
  # 키워드 플래너는 Aside 브라우저로 조회한다(10/20 ego→Aside). 앱이 꺼져 있으면 켠다.
  if ! aside repl "console.log('ok')" 2>&1 | grep -q '^ok'; then
    open -ga Aside
    sleep 20
  fi
  python3 scripts/query_planner.py --check
  code=$?
  if [ $code -eq 3 ]; then
    notify "⚠️ 카카오 로그인이 풀려 조사를 건너뜁니다. Aside 브라우저에서 keywordad.kakao.com 로그인 후 Claude Code에 '조사해'라고 해 주세요."
    exit 0
  elif [ $code -ne 0 ]; then
    notify "⚠️ 키워드 플래너 확인 실패(코드 $code). 로그: $LOG"
    exit 0
  fi
  out=$(claude -p "$(cat scripts/research_prompt.md)" --model opus --max-budget-usd 8 --no-session-persistence \
    --allowedTools "Read" "Glob" "Grep" "Write(./**)" "Edit(./**)" \
      "Bash(python3 scripts/*)" "Bash(python3 ./scripts/*)" \
      "Bash($HOME/Projects/블로그/구글블로그-AI뉴스/.venv/bin/python scripts/collect_seeds.py)" \
      "Bash(ls *)" "Bash(cat *)" "Bash(date*)" 2>&1)
  status=$?
  echo "$out"
  if [ $status -eq 0 ]; then
    notify "✅ $(echo "$out" | tail -8)"
  else
    notify "❌ 조사 실패(코드 $status). $(echo "$out" | tail -3)"
  fi
  echo "=== $(date '+%F %T') 끝 (코드 $status)"
} >> "$LOG" 2>&1
