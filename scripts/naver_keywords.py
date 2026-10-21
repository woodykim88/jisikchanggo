"""네이버 검색광고 API로 키워드 검색량·연관 키워드를 조회해 조사데이터/YYYY-MM-DD.json에 더한다 (2026-10-21 카카오 플래너 대체).

    python3 naver_keywords.py 키워드1 키워드2 ...
    python3 naver_keywords.py --check     # 키·연결만 확인
카카오 키워드 플래너는 로그인이 하루 만에 풀려 자동 실행이 계속 멈췄다. API 키는 만료되지 않는다.
키는 지식창고/naver_searchad.local (JSON: customer_id, api_key, secret_key, .gitignore) — 공개 저장소에 올리지 않는다.
키가 없거나 거부되면 종료 코드 3.

행 형식은 예전 카카오 표와 같은 11칸이라 score.py를 그대로 쓴다:
  [키워드, 모바일 월간검색수·클릭수·클릭률·광고깊이·1위 입찰가, PC 같은 5개]
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEY_FILE = ROOT / 'naver_searchad.local'
BASE_URL = 'https://api.searchad.naver.com'
KEY_EXIT = 3
KEEP_RELATED = 40       # 씨앗마다 검색량 상위 연관 키워드만 남긴다 (예전 카카오 표 ~40줄과 비슷하게)
BID_TOP = 10            # 씨앗마다 검색량 상위 이만큼만 입찰가를 추정한다 (호출 수 절약)
BID_CHUNK = 50
PAUSE_SEC = 0.3         # 연속 호출 간격 (API 초당 호출 제한 대비)


class ApiKeyError(Exception):
    """키가 없거나 거부됨 → 종료 코드 3."""


def load_keys(path: Path = KEY_FILE) -> dict[str, str]:
    try:
        keys = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as e:
        raise ApiKeyError(f'{path.name}을 읽지 못했습니다: {e}') from e
    missing = [k for k in ('customer_id', 'api_key', 'secret_key') if not keys.get(k)]
    if missing:
        raise ApiKeyError(f'{path.name}에 {", ".join(missing)}가 없습니다.')
    return keys


def signature(timestamp: str, method: str, uri: str, secret: str) -> str:
    """공식 샘플(signaturehelper.py)과 같은 방식: base64(HMAC-SHA256("{ts}.{METHOD}.{uri}"))."""
    msg = f'{timestamp}.{method}.{uri}'.encode()
    return base64.b64encode(hmac.new(secret.encode(), msg, hashlib.sha256).digest()).decode()


def call(keys: dict[str, str], method: str, uri: str, query: dict | None = None, body: dict | None = None) -> dict:
    ts = str(round(time.time() * 1000))
    headers = {'Content-Type': 'application/json; charset=UTF-8', 'X-Timestamp': ts, 'X-API-KEY': keys['api_key'],
               'X-Customer': str(keys['customer_id']), 'X-Signature': signature(ts, method, uri, keys['secret_key'])}
    url = BASE_URL + uri + (f'?{urllib.parse.urlencode(query)}' if query else '')
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return json.loads(res.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors='replace')[:300]
        if e.code in (401, 403):
            raise ApiKeyError(f'API 키가 거부됐습니다 (HTTP {e.code}): {detail}') from e
        raise RuntimeError(f'{uri} 호출 실패 (HTTP {e.code}): {detail}') from e


def count(v) -> int:
    """검색수는 숫자 또는 "< 10" 문자열로 온다. "< 10"은 5로 본다."""
    if isinstance(v, (int, float)):
        return int(v)
    return 5 if str(v).strip().startswith('<') else int(float(str(v).replace(',', '') or 0))


def related(keys: dict[str, str], seed: str) -> list[dict]:
    """씨앗 하나의 연관 키워드 (씨앗 자신 포함), 검색량 상위 KEEP_RELATED개."""
    res = call(keys, 'GET', '/keywordstool', query={'hintKeywords': seed.replace(' ', ''), 'showDetail': 1})
    rows = res.get('keywordList', [])
    total = lambda r: count(r.get('monthlyPcQcCnt', 0)) + count(r.get('monthlyMobileQcCnt', 0))  # noqa: E731
    own = [r for r in rows if r.get('relKeyword') == seed.replace(' ', '')]
    rest = sorted((r for r in rows if r not in own), key=total, reverse=True)
    return own + rest[:KEEP_RELATED]


def bids(keys: dict[str, str], keywords: list[str], device: str) -> dict[str, int]:
    """1위 평균 입찰가 추정. 실패해도 조사는 계속한다 (입찰가는 점수의 일부일 뿐)."""
    out: dict[str, int] = {}
    for i in range(0, len(keywords), BID_CHUNK):
        items = [{'key': k, 'position': 1} for k in keywords[i:i + BID_CHUNK]]
        try:
            res = call(keys, 'POST', '/estimate/average-position-bid/keyword', body={'device': device, 'items': items})
        except RuntimeError as e:
            print(f'[입찰가 생략] {e}', file=sys.stderr)
            return out
        out.update({e['keyword']: int(e.get('bid', 0)) for e in res.get('estimate', []) if 'keyword' in e})
        time.sleep(PAUSE_SEC)
    return out


def to_row(r: dict, mobile_bid: int, pc_bid: int) -> list[str]:
    """API 한 줄 → 예전 카카오 표와 같은 11칸 문자열 행."""
    f = lambda v: f'{count(v):,}'  # noqa: E731
    depth = str(r.get('plAvgDepth', '-'))
    return [r['relKeyword'],
            f(r.get('monthlyMobileQcCnt', 0)), f(r.get('monthlyAveMobileClkCnt', 0)), str(r.get('monthlyAveMobileCtr', '-')),
            depth, f'{mobile_bid:,}' if mobile_bid else '-',
            f(r.get('monthlyPcQcCnt', 0)), f(r.get('monthlyAvePcClkCnt', 0)), str(r.get('monthlyAvePcCtr', '-')),
            depth, f'{pc_bid:,}' if pc_bid else '-']


def run(keys: dict[str, str], seeds: list[str]) -> dict[str, list[list[str]]]:
    rels: dict[str, list[dict]] = {}
    for seed in seeds:
        rels[seed] = related(keys, seed)
        time.sleep(PAUSE_SEC)
    wanted = sorted({r['relKeyword'] for rows in rels.values() for r in rows[:BID_TOP]})
    mobile, pc = bids(keys, wanted, 'MOBILE'), bids(keys, wanted, 'PC')
    return {seed: [to_row(r, mobile.get(r['relKeyword'], 0), pc.get(r['relKeyword'], 0)) for r in rows]
            for seed, rows in rels.items()}


def save(data: dict[str, list[list[str]]]) -> Path:
    day = datetime.now(timezone(timedelta(hours=9))).date().isoformat()
    path = ROOT / '조사데이터' / f'{day}.json'
    saved = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps({**saved, **data}, ensure_ascii=False, indent=1), encoding='utf-8')
    return path


def main() -> None:
    args = sys.argv[1:]
    try:
        keys = load_keys()
        if args == ['--check']:
            n = len(related(keys, '연말정산'))
            print(f'네이버 검색광고 API 정상 (연말정산 연관 {n}줄)')
            return
        data = run(keys, args)
    except ApiKeyError as e:
        print(f'네이버 검색광고 API 키 문제: {e}')
        sys.exit(KEY_EXIT)
    n = lambda s: int(s.replace(',', '')) if s not in ('-', '') else 0  # noqa: E731
    for kw, rows in data.items():
        top = sorted(((r[0], n(r[1]) + n(r[6]), max(n(r[5]), n(r[10]))) for r in rows), key=lambda x: -x[1])[:8]
        print(f'## {kw} ({len(rows)}줄): ' + ', '.join(f'{k} {v:,}' + (f'·{b:,}원' if b else '') for k, v, b in top))
    print(f'[저장] {save(data)}')


if __name__ == '__main__':
    main()
