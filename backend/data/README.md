# backend/data/

backend의 seed 데이터 디렉터리. **런타임(app)은 이 파일들을 직접 읽지 않습니다** — 앱은 MongoDB Atlas에서 데이터를 읽습니다. 이 디렉터리는 Atlas에 적재할 seed 아티팩트를 보관하는 곳입니다.

- `floripedia_v2.json` — **현재 seed**. Floripedia 식물 도감 마스터 데이터(KPNI 1,060종, Phase 2). 데이터 생성·검증 작업은 `backend/pipeline/`에서 이루어지며 결과가 이 파일에 반영됩니다.
- `_legacy/` — Phase 1(v1) 빌드 산출물·중간 스테이징 json/로그. 보존용, 현재 미사용. (`_legacy/_LEGACY.md` 참고)

> `*.json`·`*.txt`는 용량이 커 git에서 제외됩니다(`.gitignore`). 이 README와 `_legacy/_LEGACY.md`만 추적됩니다.
