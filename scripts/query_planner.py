"""카카오 키워드 플래너에 키워드를 넣고 연관 키워드 표를 조사데이터/YYYY-MM-DD.json에 더한다.

    python3 query_planner.py 키워드1 키워드2 ...
    python3 query_planner.py --check     # 로그인 상태만 확인
Aside 브라우저(aside repl)로 조회한다. 로그인이 풀려 있으면 종료 코드 3 (사용자가 Aside에서 직접 로그인해야 한다. 비밀번호는 다루지 않음).
열: 키워드, 모바일 광고요청수·클릭수·클릭률·평균경쟁광고수·최고입찰가, PC 같은 5개.
"""
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# 광고계정 ID가 들어간 주소라 공개 저장소에 두지 않는다 (planner_url.local은 .gitignore)
PLANNER_URL = (ROOT / 'planner_url.local').read_text(encoding='utf-8').strip()
LOGIN_EXIT = 3
CHUNK = 12  # aside repl 한 번은 120초 제한 — 키워드당 약 3초라 12개씩 나눈다

JS = r"""
const args = __ARGS__;
for (const t of [...tabs]) if (t.url().includes('keyword-planner')) await closeTab(t);
const p = await openTab(args.url);
await sleep(2500);
const out = {};
try {
  if (p.url().includes('accounts.kakao.com')) { console.log('@@LOGIN@@'); }
  else {
    const box = p.locator('form input').first();
    for (const kw of args.keywords) {
      await box.fill(kw);
      await box.press('Enter');
      await sleep(2500);
      out[kw] = await p.evaluate(() => [...document.querySelectorAll('table')].slice(1)
        .flatMap(t => [...t.querySelectorAll('tr')]).map(r => [...r.querySelectorAll('td')].map(c => c.innerText.trim()))
        .filter(c => c.length >= 10).map(c => c.slice(1)));
    }
    console.log('@@DATA@@' + JSON.stringify(out));
  }
} finally {
  await closeTab(p);
}
"""


def run_chunk(keywords: list[str]) -> dict | None:
    # JSON을 코드에 직접 넣는다 (JSON은 JS 리터럴로 안전). aside repl은 오류에도 종료 코드 0이라 표식으로 판단한다
    script = JS.replace('__ARGS__', json.dumps({'url': PLANNER_URL, 'keywords': keywords}, ensure_ascii=False))
    proc = subprocess.run(['aside', 'repl', script], capture_output=True, text=True, timeout=150)
    text = proc.stdout + proc.stderr
    if '@@LOGIN@@' in text:
        return None
    if '@@DATA@@' not in text:
        hint = ' (Aside 앱이 켜져 있어야 합니다)' if "isn't running" in text else ''
        sys.exit(f'플래너 조회 실패{hint}: {text[-500:]}')
    return json.loads(text.split('@@DATA@@', 1)[1].strip().splitlines()[0])


def run(keywords: list[str]) -> dict | None:
    merged = {}
    for i in range(0, len(keywords), CHUNK):
        data = run_chunk(keywords[i:i + CHUNK])
        if data is None:
            return None
        merged = {**merged, **data}
    return merged


def main() -> None:
    args = sys.argv[1:]
    check = args == ['--check']
    data = run(['연말정산'] if check else args)
    if data is None:
        print('카카오 로그인이 풀려 있습니다.')
        sys.exit(LOGIN_EXIT)
    if check:
        print('로그인 정상')
        return
    day = datetime.now(timezone(timedelta(hours=9))).date().isoformat()
    path = ROOT / '조사데이터' / f'{day}.json'
    saved = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    saved.update(data)
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(saved, ensure_ascii=False, indent=1), encoding='utf-8')
    n = lambda s: int(s.replace(',', '')) if s not in ('-', '') else 0  # noqa: E731
    for kw, rows in data.items():
        top = sorted(((r[0], n(r[1]) + n(r[6]), max(n(r[5]), n(r[10]))) for r in rows if len(r) >= 11), key=lambda x: -x[1])[:8]
        print(f'## {kw} ({len(rows)}줄): ' + ', '.join(f'{k} {v:,}' + (f'·{b:,}원' if b else '') for k, v, b in top))
    print(f'[저장] {path}')


if __name__ == '__main__':
    main()
