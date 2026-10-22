"""지식창고의 최신 채널 배분(hints/YYYY-MM-DD.json)을 각 봇 저장소의 data/topic_hints.json으로 보내 푸시한다.

봇들은 GitHub Actions에서 돌아 이 폴더를 못 읽는다. 조사를 마친 뒤 한 번 실행:
    python3 ~/Projects/지식창고/scripts/sync_hints.py          # 최신 파일
    python3 ~/Projects/지식창고/scripts/sync_hints.py --dry-run # 복사만, 커밋·푸시 안 함
각 저장소에서는 data/topic_hints.json 한 파일만 커밋한다 (다른 작업 중인 파일은 건드리지 않음).
먼저 지식창고 자체(공개 저장소 woodykim88/jisikchanggo)의 변경을 커밋·푸시한다. 접속정보.md는 .gitignore로 제외.
로컬에서 도는 채널(Aside 네이버 블로그·건강노트 3D릴스, 베리굿)은 지식창고를 직접 읽는다.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECTS = ROOT.parent
REPOS = {
    'blog': PROJECTS / '블로그' / '구글블로그-정보마스터',
    'honjasseobom': PROJECTS / '스레드' / '혼자써봄 생활필수품 뉴스',
    'healthnote': PROJECTS / '스레드' / '건강노트 건강소식 뉴스',
    'haru': PROJECTS / '스레드' / '하루뉴스',
}
TARGET = Path('data') / 'topic_hints.json'
COMMIT_MESSAGE = 'chore: 지식창고 키워드 조사 소재 갱신 [skip ci]'


def latest_hints() -> Path:
    files = sorted((ROOT / 'hints').glob('????-??-??.json'))
    if not files:
        sys.exit('hints/ 폴더에 YYYY-MM-DD.json이 없습니다.')
    return files[-1]


def git(repo: Path, *args: str) -> str:
    return subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


def sync(repo: Path, data: dict, dry_run: bool) -> str:
    target = repo / TARGET
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    if dry_run:
        return '복사만 함'
    git(repo, 'add', '--', str(TARGET))
    if not git(repo, 'diff', '--cached', '--name-only', '--', str(TARGET)):
        return '변경 없음'
    git(repo, 'commit', '-m', COMMIT_MESSAGE, '--', str(TARGET))
    git(repo, 'pull', '--rebase', '--autostash', '-q')
    git(repo, 'push', '-q')
    return '푸시함'


def publish_self() -> str:
    git(ROOT, 'add', '-A')
    if not git(ROOT, 'diff', '--cached', '--name-only'):
        return '변경 없음'
    git(ROOT, 'commit', '-m', 'docs: 키워드 조사 기록 갱신')
    git(ROOT, 'pull', '--rebase', '--autostash', '-q')
    git(ROOT, 'push', '-q')
    return '푸시함'


def main() -> None:
    dry_run = '--dry-run' in sys.argv
    if not dry_run:
        try:
            print(f'[지식창고] {publish_self()}')
        except subprocess.CalledProcessError as e:
            print(f'[지식창고] 실패: {e.stderr.strip()[:200]}')
    source = latest_hints()
    data = json.loads(source.read_text(encoding='utf-8'))
    print(f'[소스] {source.name} (조사일 {data["date"]})')
    for channel, repo in REPOS.items():
        count = len(data.get('channels', {}).get(channel, []))
        try:
            result = sync(repo, data, dry_run)
        except subprocess.CalledProcessError as e:
            result = f'실패: {e.stderr.strip()[:200]}'
        print(f'[{channel}] 소재 {count}개 → {repo.name}: {result}')


if __name__ == '__main__':
    main()
