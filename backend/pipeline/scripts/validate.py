"""
생성된 stories/colorInfo/scentInfo/flowerInfo 검증

사용법:
    python backend/pipeline/scripts/validate.py [경로] [--all]
    경로 생략 시 기본값: <repo>/backend/data/floripedia_v2.json
    --all : v1 1부(_id <= 1500)까지 포함해 전체 검증 (기본은 v2 신규 _id > 1500만)

이슈는 두 단계로 구분한다.
  - ERROR(유효성): enum 값 오류, 필수 필드 누락, hex/label 개수 불일치 등 데이터 오류
  - WARN(권장): 길이·개수·장르중복 등 v2 생성 가이드 기준 (v1 1부는 더 느슨해 다수 발생)
"""

import json
import sys
from pathlib import Path

# 이 스크립트(backend/pipeline/scripts/) 기준 경로
_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[3]
DEFAULT_DATA = _REPO_ROOT / 'backend' / 'data' / 'floripedia_v2.json'
REPORT_PATH = _HERE.parent / 'validation_report.json'


VALID_GENRES = {'SCIENCE', 'HISTORY', 'EPISODE', 'ART', 'MYTH'}
VALID_COLOR_GROUPS = {'빨강/분홍', '푸른색', '백색/미색', '노랑/주황', '갈색/검정', '초록/연두'}
VALID_SCENT_GROUPS = {'은은·차분', '싱그러운·시원', '달콤·화사', '무향'}
VALID_FLOWER_GROUPS = {'사랑/고백', '감사/존경', '행복/즐거움', '위로/슬픔', '이별/그리움'}


def check_item(p):
    """단일 항목 검증, 이슈 리스트 반환. 각 이슈는 sev='error'|'warn'."""
    issues = []

    def err(field, msg):
        issues.append({'field': field, 'msg': msg, 'sev': 'error'})

    def warn(field, msg):
        issues.append({'field': field, 'msg': msg, 'sev': 'warn'})

    # === stories ===
    stories = p.get('stories', [])
    if not stories:
        return [{'field': 'stories', 'msg': '비어있음 (생성 안 됨)', 'sev': 'error'}]

    if not (3 <= len(stories) <= 4):
        warn('stories', f'개수 권장 3~4개 ({len(stories)}개)')

    seen_genres = []
    for i, s in enumerate(stories):
        g = s.get('genre', '')
        c = s.get('content', '')
        if g not in VALID_GENRES:
            err(f'stories[{i}].genre', f'유효하지 않음: {g!r}')
        seen_genres.append(g)
        if not (80 <= len(c) <= 200):
            warn(f'stories[{i}].content', f'길이 권장 80~200자 ({len(c)}자)')

    if len(set(seen_genres)) < len(seen_genres):
        warn('stories', f'장르 중복: {seen_genres}')

    # === colorInfo ===
    ci = p.get('colorInfo', {})
    cg = ci.get('colorGroup', [])
    if not cg:
        err('colorInfo.colorGroup', '비어있음')
    else:
        invalid = [g for g in cg if g not in VALID_COLOR_GROUPS]
        if invalid:
            err('colorInfo.colorGroup', f'유효하지 않은 값: {invalid}')
    if len(ci.get('hexCodes', [])) != len(ci.get('colorLabels', [])):
        err('colorInfo', 'hexCodes와 colorLabels 개수 불일치')

    # === scentInfo ===
    si = p.get('scentInfo', {})
    sg = si.get('scentGroup', [])
    if not sg:
        err('scentInfo.scentGroup', '비어있음')
    else:
        invalid = [g for g in sg if g not in VALID_SCENT_GROUPS]
        if invalid:
            err('scentInfo.scentGroup', f'유효하지 않은 값: {invalid}')

    # === flowerInfo ===
    fi = p.get('flowerInfo', {})
    lang = fi.get('language', '')
    fg = fi.get('flowerGroup', '')
    if not lang:
        err('flowerInfo.language', '비어있음')
    elif not (5 <= len(lang) <= 50):
        warn('flowerInfo.language', f'길이 권장 5~50자 ({len(lang)}자)')
    if not fg:
        err('flowerInfo.flowerGroup', '비어있음')
    elif fg not in VALID_FLOWER_GROUPS:
        err('flowerInfo.flowerGroup', f'유효하지 않음: {fg!r}')

    # === preContent ===
    pc = p.get('horticulture', {}).get('preContent', '')
    if not pc:
        err('horticulture.preContent', '비어있음')
    elif not (150 <= len(pc) <= 500):
        warn('horticulture.preContent', f'길이 권장 150~500자 ({len(pc)}자)')

    return issues


def main():
    args = sys.argv[1:]
    check_all = '--all' in args
    paths = [a for a in args if not a.startswith('--')]
    path = paths[0] if paths else DEFAULT_DATA

    with open(path, encoding='utf-8') as f:
        data = json.load(f)

    if check_all:
        items = list(data)
        scope = f'전체 {len(items)}종 (v1 1부 + v2 신규)'
    else:
        items = [p for p in data if int(p['_id']) > 1500]
        scope = f'v2 신규 {len(items)}종 (_id > 1500)'

    print(f"검증 대상: {scope}\n")

    clean = 0          # 오류·권장 모두 0
    error_entries = 0  # ERROR 보유 종
    warn_only = 0      # ERROR 없고 WARN만 있는 종
    not_started = 0
    error_count = 0
    warn_count = 0
    err_issues = {}
    warn_issues = {}

    for p in items:
        if not p.get('stories'):
            not_started += 1
            continue
        issues = check_item(p)
        errs = [i for i in issues if i['sev'] == 'error']
        warns = [i for i in issues if i['sev'] == 'warn']
        error_count += len(errs)
        warn_count += len(warns)
        if errs:
            error_entries += 1
            err_issues[p['_id']] = {'name': p['name'], 'issues': errs}
        if warns:
            if not errs:
                warn_only += 1
            warn_issues[p['_id']] = {'name': p['name'], 'issues': warns}
        if not errs and not warns:
            clean += 1

    print("=== 결과 ===")
    print(f"  완료(이슈 0): {clean}")
    print(f"  유효성 오류(ERROR) 보유 종: {error_entries}  (총 {error_count}건)")
    print(f"  권장(WARN)만 있는 종: {warn_only}  (총 {warn_count}건)")
    print(f"  생성 안 됨: {not_started}")
    print(f"  총: {len(items)}")

    if err_issues:
        print(f"\n=== 유효성 오류(ERROR) 샘플 (앞 10개) ===")
        for pid, info in list(err_issues.items())[:10]:
            print(f"\n_id={pid} {info['name']}")
            for i in info['issues']:
                print(f"  [{i['field']}] {i['msg']}")
    else:
        print("\n유효성 오류(ERROR) 0건 -- 통과")

    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        json.dump({
            'scope': 'all' if check_all else 'v2',
            'summary': {
                'total': len(items),
                'clean': clean,
                'error_entries': error_entries,
                'error_count': error_count,
                'warn_only_entries': warn_only,
                'warn_count': warn_count,
                'not_started': not_started,
            },
            'errors': err_issues,
            'warns': warn_issues,
        }, f, ensure_ascii=False, indent=2)
    print(f"\n상세: {REPORT_PATH}")


if __name__ == '__main__':
    main()
