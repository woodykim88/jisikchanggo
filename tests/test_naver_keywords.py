"""python3 -m unittest discover -s tests (지식창고는 시스템 python3로 돌아 pytest 없이 unittest)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))
import naver_keywords as nk  # noqa: E402

KEYS = {'customer_id': '1', 'api_key': 'k', 'secret_key': 's'}


def fake_api(rows, estimate=None, fail_bid=False):
    def call(keys, method, uri, query=None, body=None):
        if uri == '/keywordstool':
            return {'keywordList': rows}
        if fail_bid:
            raise RuntimeError('입찰가 실패')
        return {'estimate': [{'keyword': i['key'], 'bid': (estimate or {}).get(i['key'], 0)} for i in body['items']]}
    return call


def kw(name, pc, mo):
    return {'relKeyword': name, 'monthlyPcQcCnt': pc, 'monthlyMobileQcCnt': mo, 'monthlyAvePcClkCnt': 1.5,
            'monthlyAveMobileClkCnt': 3, 'monthlyAvePcCtr': 0.1, 'monthlyAveMobileCtr': 0.2, 'plAvgDepth': 15, 'compIdx': '높음'}


class NaverKeywordsTest(unittest.TestCase):
    def setUp(self):
        self.orig_call, self.orig_pause = nk.call, nk.PAUSE_SEC
        nk.PAUSE_SEC = 0

    def tearDown(self):
        nk.call, nk.PAUSE_SEC = self.orig_call, self.orig_pause

    def test_count_handles_under_ten_string(self):
        self.assertEqual(nk.count('< 10'), 5)
        self.assertEqual(nk.count(1230), 1230)
        self.assertEqual(nk.count('2,400'), 2400)

    def test_signature_matches_official_format(self):
        import base64, hashlib, hmac
        want = base64.b64encode(hmac.new(b's', b'123.GET./keywordstool', hashlib.sha256).digest()).decode()
        self.assertEqual(nk.signature('123', 'GET', '/keywordstool', 's'), want)

    def test_rows_keep_kakao_layout_for_score_py(self):
        nk.call = fake_api([kw('수능', 1000, '< 10')], estimate={'수능': 1200})
        rows = nk.run(KEYS, ['수능'])['수능']
        self.assertEqual(len(rows[0]), 11)
        self.assertEqual(rows[0][0], '수능')
        self.assertEqual(rows[0][1], '5')        # 모바일 검색수 "< 10"
        self.assertEqual(rows[0][5], '1,200')    # 모바일 1위 입찰가
        self.assertEqual(rows[0][6], '1,000')    # PC 검색수

    def test_seed_first_then_top_related_capped(self):
        many = [kw(f'수능{i}', i, i) for i in range(100)] + [kw('수능일정', 1, 1)]
        nk.call = fake_api(many)
        rows = nk.related(KEYS, '수능 일정')
        self.assertEqual(rows[0]['relKeyword'], '수능일정')
        self.assertEqual(len(rows), 1 + nk.KEEP_RELATED)
        self.assertEqual(rows[1]['relKeyword'], '수능99')

    def test_bid_failure_does_not_stop_research(self):
        nk.call = fake_api([kw('독감', 10, 10)], fail_bid=True)
        rows = nk.run(KEYS, ['독감'])['독감']
        self.assertEqual(rows[0][5], '-')

    def test_missing_keys_raise_api_key_error(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'k.local'
            p.write_text(json.dumps({'customer_id': '1'}), encoding='utf-8')
            with self.assertRaises(nk.ApiKeyError):
                nk.load_keys(p)
            with self.assertRaises(nk.ApiKeyError):
                nk.load_keys(Path(d) / 'none.local')


if __name__ == '__main__':
    unittest.main()
