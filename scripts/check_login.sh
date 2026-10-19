#!/bin/bash
# 조사 전날 저녁(일·화·목 21:00) 카카오 로그인만 확인. 풀려 있으면 미리 알려 다음 날 14:00 조사를 놓치지 않게 한다 (10/20 건의).
set -u
cd "$HOME/Projects/지식창고" || exit 1
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:/usr/bin:/bin"
source scripts/notify.sh
LOG="logs/login-check.log"
{
  echo "=== $(date '+%F %T')"
  ensure_aside
  python3 scripts/query_planner.py --check
  code=$?
  if [ $code -eq 3 ]; then
    notify "🔑 내일 14:00 조사 전에 로그인이 필요합니다. Aside 브라우저에서 keywordad.kakao.com에 로그인해 주세요."
  elif [ $code -ne 0 ]; then
    notify "⚠️ 내일 조사 전 점검 실패(코드 $code). Aside가 켜져 있는지 확인해 주세요. 로그: $LOG"
  fi
} >> "$LOG" 2>&1
