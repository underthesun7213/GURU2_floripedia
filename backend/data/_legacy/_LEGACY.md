# _legacy/ (backend/data)

Phase 1(v1, 2026-01~03) 빌드 산출물·중간 스테이징 데이터. Phase 2(`backend/pipeline/`, KPNI 1,060종)로 대체됨. **보존용, 현재 미사용.**

- 런타임(app)은 이 파일들을 읽지 않습니다(데이터는 MongoDB Atlas에서 읽음).
- 일부 파일(`all_plants.json`, `v2_data*.json`, `failed_images.json`, `retry_progress.json`, `wikimedia_migration_progress.json` 등)은 `backend/scripts/`의 DORMANT 이미지 스크립트들이 과거 입력으로 사용했습니다. track 2에서 이미지 작업을 재개하면 해당 스크립트는 새 seed(`backend/data/floripedia_v2.json`) 기준으로 입력을 재배선할 예정입니다.
- 현재 seed는 상위 디렉터리의 `floripedia_v2.json` 하나뿐입니다.
