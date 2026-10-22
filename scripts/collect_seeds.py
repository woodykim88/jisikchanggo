"""씨앗 수집: 블로그봇 수집기로 최근 48시간 후보·트렌드·달력·최근 발행 글을 출력한다.
블로그봇 가상환경으로 실행: ~/Projects/블로그/구글블로그-정보마스터/.venv/bin/python collect_seeds.py
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

BLOG = Path(__file__).resolve().parents[2] / '블로그' / '구글블로그-정보마스터'
os.chdir(BLOG)
sys.path.insert(0, str(BLOG))

from src import collector, history, kr_calendar, selector, topics, trends  # noqa: E402
from src.http_client import http_get  # noqa: E402

now = datetime.now(timezone.utc)
print(kr_calendar.calendar_facts(now.astimezone(timezone(timedelta(hours=9))).date()))
past = history.load_history()
print('\n== 블로그 최근 30편 (중복 피하기)')
for e in past[-30:]:
    print('-', e.publish_date, e.title)
print('\n== 지금 검색 급상승 키워드')
print(', '.join(trends.fetch_trending(http_get)))
for cat in (topics.TECH, topics.MONEY):
    spec = topics.SPECS[cat]
    found = [c for c in collector.fetch_candidates(http_get, now, spec.sources) if not selector.is_duplicate(c, past)]
    print(f'\n== {spec.name} 기사 {len(found)}건')
    for c in found:
        print(f'- ({c.source}) {c.title}')
