# backend/pipeline/

Floripedia 데이터 작업·실험 공간. (앱이 직접 읽지 않음 — 결과물은 `../data/`에 반영)

```
backend/pipeline/
  raw/          KPNI CSV 원본 (대용량, git 제외 — README만 추적)
  scripts/      변환·검증 스크립트 (validate.py 등)
  stories/      Claude Code 인문 콘텐츠 작업 영역
                (PROMPT_TEMPLATE.md, sample_v1_reference.json,
                 genre_examples.md, chunks.json, _content.py, _meta_*.txt)
  archive/      옛 버전·중간 산출물
  _scratch/     임시 스크립트 (git 제외)
```

## 검증
```
python backend/pipeline/scripts/validate.py
```
기본 대상은 `<repo>/backend/data/floripedia_v2.json`. 스크립트에 `encoding='utf-8'`이 명시되어 있어 `-X utf8` 옵션 없이 동작합니다.
