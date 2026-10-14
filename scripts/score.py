"""소재 점수 계산. 소재 정의(JSON)를 받아 조사데이터에서 관련 키워드만 묶어 점수를 매긴다.

    python3 score.py topics.json
topics.json: [{"name": "...", "roots": ["독감"], "exclude": [], "timeliness": 0-3, "action": 0-3, "penalty": 0-1}, ...]
점수 = 수요 30(로그) + 최고입찰가 20(로그) + 롱테일 10 + 시의성 20 + 행동·꿀팁 20 − 감점 10×penalty
결과는 조사데이터/YYYY-MM-DD_score.json (순위, 수요, 입찰가, 롱테일, 상위 키워드)
"""
import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


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
        longtail = sum(1 for v in seen.values() if v[0] >= 100)
        score = (30 * min(math.log10(max(demand, 1)) / 6, 1) + 20 * min(math.log10(max(bid, 1)) / 4, 1)
                 + 10 * min(longtail / 30, 1) + 20 * t['timeliness'] / 3 + 20 * t['action'] / 3 - 10 * t.get('penalty', 0))
        top = sorted(seen.items(), key=lambda x: -x[1][0])[:8]
        results.append({'name': t['name'], 'score': round(score, 1), 'demand': demand, 'bid': bid, 'longtail': longtail,
                        'timeliness': t['timeliness'], 'action': t['action'],
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
