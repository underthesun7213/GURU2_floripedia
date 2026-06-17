# _legacy/ (backend/scripts)

Phase 1(v1, 2026-01~03) 빌드 스크립트. Phase 2(`backend/pipeline/`, KPNI 1,060종)로 대체됨. **보존용, 현재 미사용.**

- `base_data/` — v1 데이터 빌드 체인 (collect.py → build_data.py → clean_data.py → refine.py → del_birth.py → categorizer.py → add_images.py → upload_to_mongodb.py). data.go.kr 수집·Gemini 분류·v1 Mongo 업로드까지의 전체 파이프라인.
- `etl_add_plants.py`, `patch_*.py` — v1 데이터 보정/패치 스크립트 (v2_data*.json 대상).
- `inspect_plants.py` — v1 데이터 점검용 스크립트.

> 이미지 트랙 스크립트(collect_images.py, upload_images_to_firebase.py, migrate_wikimedia_to_firebase.py, retry_wikimedia_uploads.py)는 재사용 대상이라 `backend/scripts/` 루트에 유지됩니다(DORMANT 주석 표기).
