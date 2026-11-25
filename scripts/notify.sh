# 텔레그램 알림함에 남긴다 (run_research.sh가 source). 11/25: 직접 전송 대신 알림함 notify CLI.
# fail 은 바로 가고, ok·warn 은 08:30·21:35 표에 묶인다.
NOTIFY="$HOME/Projects/도구/텔레그램-알림함/notify"

notify() {  # notify <fail|warn|ok> <본문>
  perl -e 'alarm 60; exec @ARGV or exit 127' "$NOTIFY" --status "$1" --project "지식창고 조사" --text "$2" \
    || echo "[알림함] notify 실패(종료코드 $?)" >&2
}
