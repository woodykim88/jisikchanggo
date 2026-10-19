"""조사 소재를 쓴 글과 아닌 글의 성과 비교 (10/20 건의 2번: 봇이 사용 여부를 따로 기록하지 않아 발행 기록으로 소급 판정).

    python3 scripts/hint_usage.py              # 10/15 이후 전체
    python3 scripts/hint_usage.py 2026-10-20   # 이 날짜 이후 글만

판정: 글 날짜 기준 0~3일 전 hints/YYYY-MM-DD.json에서 그 채널에 배분된 소재의 키워드가
제목·본문에 하나라도 그대로 나오면 '조사 소재' (봇의 topic_hints.matches와 같은 규칙).
성과: 스레드는 data/performance.json 조회수, 블로그는 data/search_console.json 노출·클릭(28일, 상위 페이지만).
결과는 화면에만 낸다 — 공개 저장소라 성과 숫자는 파일로 남기지 않는다.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

from sync_hints import REPOS

ROOT = Path(__file__).resolve().parent.parent
MAX_AGE_DAYS = 3  # 봇 topic_hints.MAX_AGE_DAYS와 같게
MIN_KEYWORD_CHARS = 2
DONE = {'PUBLISHED', 'SCHEDULED'}


def squash(text: str) -> str:
    return re.sub(r'\s+', '', text).lower()


def load_hints() -> dict[date, dict]:
    return {date.fromisoformat(p.stem): json.loads(p.read_text(encoding='utf-8'))
            for p in sorted((ROOT / 'hints').glob('????-??-??.json'))}


def hint_topics(post_day: date, channel: str, hints: dict[date, dict]) -> list[str]:
    """그날 봇이 볼 수 있었던 소재 중, 글에 키워드가 나온 것 (matches는 호출하는 쪽에서)."""
    return [i for d, h in hints.items() if 0 <= (post_day - d).days <= MAX_AGE_DAYS
            for i in h.get('channels', {}).get(channel, []) if isinstance(i, dict)]


def matched(text: str, items: list[dict]) -> list[str]:
    s = squash(text)
    return sorted({i['topic'] for i in items
                   if any(len(squash(k)) >= MIN_KEYWORD_CHARS and squash(k) in s for k in i.get('keywords', []))})


def post_day(p: dict) -> date | None:
    raw = p.get('publish_date') or str(p.get('slot', ''))[:10]
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def metrics(repo: Path) -> dict[str, str]:
    """글 주소·media id → 성과 문자열."""
    perf = repo / 'data' / 'performance.json'
    if perf.exists():
        posts = json.loads(perf.read_text(encoding='utf-8')).get('posts', [])
        return {str(p['id']): f"조회 {p.get('views', 0)}" for p in posts if 'id' in p}
    sc = repo / 'data' / 'search_console.json'
    if sc.exists():
        pages = json.loads(sc.read_text(encoding='utf-8')).get('top_pages', [])
        return {p['page']: f"노출 {p['impressions']}·클릭 {p['clicks']}" for p in pages}
    return {}


def views(m: str) -> int | None:
    found = re.match(r'조회 (\d+)', m or '')
    return int(found.group(1)) if found else None


def report(channel: str, repo: Path, hints: dict[date, dict], since: date) -> None:
    history = json.loads((repo / 'data' / 'history.json').read_text(encoding='utf-8'))
    perf = metrics(repo)
    rows = []
    for p in history:
        day = post_day(p)
        if day is None or day < since or p.get('status') not in DONE:
            continue
        text = ' '.join(str(p.get(k, '')) for k in ('title', 'caption'))
        topics = matched(text, hint_topics(day, channel, hints))
        m = perf.get(str(p.get('media_id', ''))) or perf.get(str(p.get('url', ''))) or ''
        rows.append((day, bool(topics), p.get('title', '')[:40], ', '.join(topics), m))
    print(f'\n## {channel} ({len(rows)}편, 조사 소재 {sum(r[1] for r in rows)}편)')
    for used in (True, False):
        vs = [v for r in rows if r[1] == used for v in [views(r[4])] if v is not None]
        if vs:
            print(f"- {'조사 소재' if used else '그 외'} 평균 조회 {sum(vs) / len(vs):.0f} ({len(vs)}편)")
    for day, used, title, topics, m in rows:
        if used:
            print(f'  {day} [{topics}] {title} {m}')


def main() -> None:
    since = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date(2026, 10, 15)
    hints = load_hints()
    for channel, repo in REPOS.items():
        if (repo / 'data' / 'history.json').exists():
            report(channel, repo, hints, since)


if __name__ == '__main__':
    main()
