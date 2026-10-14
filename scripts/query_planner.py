"""카카오 키워드 플래너에 키워드를 넣고 연관 키워드 표를 조사데이터/YYYY-MM-DD.json에 더한다.

    python3 query_planner.py 키워드1 키워드2 ...
    python3 query_planner.py --check     # 로그인 상태만 확인
로그인이 풀려 있으면 종료 코드 3 (사용자가 Ego 브라우저에서 직접 로그인해야 한다. 비밀번호는 다루지 않음).
열: 키워드, 모바일 광고요청수·클릭수·클릭률·평균경쟁광고수·최고입찰가, PC 같은 5개.
"""
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLANNER_URL = 'https://keywordad.kakao.com/1011514/keyword-planner'
LOGIN_EXIT = 3

JS = r'''
const args = __ARGS__;
const task = await taskSpace("지식창고 키워드 조사");
const page = task.page("p1");
const out = {};
try {
  await page.goto(args.url);
  await page.waitForLoadState();
  await page.waitForTimeout(2500);
  if ((await page.url()).includes("accounts.kakao.com")) { console.log("@@LOGIN@@"); }
  else {
    for (const kw of args.keywords) {
      await page.fill("loc=css:form input", kw);
      await page.press("loc=css:form input", "Enter");
      await page.waitForTimeout(2500);
      out[kw] = await page.evaluate(() => [...document.querySelectorAll("table")].slice(1)
        .flatMap(t => [...t.querySelectorAll("tr")]).map(r => [...r.querySelectorAll("td")].map(c => c.innerText.trim()))
        .filter(c => c.length >= 10).map(c => c.slice(1)));
    }
    console.log("@@DATA@@" + JSON.stringify(out));
  }
} finally {
  await task.finish({ keep: [] });
}
'''


def run(keywords: list[str]) -> dict | None:
    # ego-browser는 환경변수를 스크립트에 넘기지 않으므로 JSON을 코드에 직접 넣는다 (JSON은 JS 리터럴로 안전)
    script = JS.replace('__ARGS__', json.dumps({'url': PLANNER_URL, 'keywords': keywords}, ensure_ascii=False))
    proc = subprocess.run(['ego-browser', 'nodejs'], input=script, capture_output=True, text=True,
                          timeout=60 + 8 * len(keywords))
    text = proc.stdout + proc.stderr  # ego-browser는 console.log를 stderr로 내보낼 때가 있다
    if '@@LOGIN@@' in text:
        return None
    if '@@DATA@@' not in text:
        sys.exit(f'플래너 조회 실패: {text[-500:]}')
    return json.loads(text.split('@@DATA@@', 1)[1].strip().splitlines()[0])


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
