"""소재 점수 계산. 소재 정의(JSON)를 받아 조사데이터에서 관련 키워드만 묶어 점수를 매긴다.

    python3 score.py topics.json
topics.json: [{"name": "...", "roots": ["독감"], "exclude": [], "timeliness": 0-3, "action": 0-3, "penalty": 0-1,
               "format": "calculator|calendar|"}, ...]
점수 = 수요 30(로그) + 1위 입찰가 20(로그) + 롱테일 10 + 시의성 20 + 행동·꿀팁 20 − 감점 10×penalty + 형식 가점
형식 가점(2026-10-15): 계산기형·일정형 +8. Search Console에서 "실업급여 계산기 2026" 1위, "11월 마케팅 캘린더" 3.4위처럼
이 블로그에서 실제로 상위 노출된 유형이다 (일반 정보형 "퇴직금 계산 방법"은 72위).
결과는 조사데이터/YYYY-MM-DD_score.json (순위, 수요, 입찰가, 롱테일, 상위 키워드)
"""
import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FORMAT_BONUS = {'calculator': 8, 'calendar': 8}
# 2026-10-21 네이버 검색광고 API(월간 검색수)로 바꾸며 상향: 카카오 광고요청수보다 수십 배 크다.
# 수요 1천만, 1위 입찰가 10만원에서 만점, 월 1,000회 이상 연관 키워드를 롱테일로 센다. 10/15·10/20 점수(카카오)와 직접 비교 금지.
DEMAND_LOG_CAP = 7
BID_LOG_CAP = 5
LONGTAIL_MIN = 1000


def num(s: str) -> int:
    return int(s.replace(',', '')) if s not in ('-', '') else 0


def main() -> None:
    topics = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    day = datetime.now(timezone(timedelta(hours=9))).date().isoformat()
    data = json.loads((ROOT / '조사데이터' / f'{day}.json').read_text(encoding='utf-8'))
    results = []
    for t in topics:
        seen: dict[str, tuple[int, int]] = {}
        for rows in data.values():
            for r in rows:
                if len(r) >= 11 and any(x in r[0] for x in t['roots']) and not any(e in r[0] for e in t.get('exclude', [])):
                    seen[r[0]] = (num(r[1]) + num(r[6]), max(num(r[5]), num(r[10])))
        demand = sum(v[0] for v in seen.values())
        bid = max([v[1] for v in seen.values()] or [0])
        longtail = sum(1 for v in seen.values() if v[0] >= LONGTAIL_MIN)
        score = (30 * min(math.log10(max(demand, 1)) / DEMAND_LOG_CAP, 1) + 20 * min(math.log10(max(bid, 1)) / BID_LOG_CAP, 1)
                 + 10 * min(longtail / 30, 1) + 20 * t['timeliness'] / 3 + 20 * t['action'] / 3 - 10 * t.get('penalty', 0)
                 + FORMAT_BONUS.get(t.get('format', ''), 0))
        top = sorted(seen.items(), key=lambda x: -x[1][0])[:8]
        results.append({'name': t['name'], 'score': round(score, 1), 'demand': demand, 'bid': bid, 'longtail': longtail,
                        'timeliness': t['timeliness'], 'action': t['action'], 'format': t.get('format', ''),
                        'top_keywords': [{'keyword': k, 'requests': v[0], 'bid': v[1]} for k, v in top]})
    results.sort(key=lambda r: -r['score'])
    out = ROOT / '조사데이터' / f'{day}_score.json'
    out.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding='utf-8')
    for i, r in enumerate(results, 1):
        kws = ', '.join(f"{k['keyword']} {k['requests']:,}" + (f"·{k['bid']:,}원" if k['bid'] else '') for k in r['top_keywords'][:6])
        print(f"{i}. {r['score']} {r['name']} | 수요 {r['demand']:,} 입찰 {r['bid']:,}원 롱테일 {r['longtail']} | {kws}")
    print(f'[저장] {out}')


if __name__ == '__main__':
    main()
