# Floripedia Backend

FastAPI + Motor(async MongoDB) + Firebase + Gemini.

## 🧊 캐시 (Cache)

읽기 위주 워크로드(식물 데이터는 ETL 배치로만 갱신, 런타임 쓰기 거의 없음)를 위한
**인메모리 캐시 계층**. 지금은 프로세스 로컬(`cachetools.TTLCache`)이며,
`CacheBackend` 프로토콜로 추상화돼 있어 추후 `RedisCache` 추가만으로 교체 가능하다.

구현: [`app/cache.py`](app/cache.py) · 미들웨어: [`app/middleware.py`](app/middleware.py) ·
무효화 API: [`app/api/v1/endpoints/admin.py`](app/api/v1/endpoints/admin.py)

### 무엇이 캐시되나
전역(사용자 무관) 읽기만 캐시한다. 사용자별 데이터는 캐시하지 않는다.

| 엔드포인트 | 캐시 키 | 비고 |
|---|---|---|
| `GET /plants/{id}` | `species:{id}:v{N}` | 전역 문서만 캐시(**D2-A**). 조회수 증가·`is_favorite`·EXP는 캐시 밖 |
| `GET /plants` | `species:list:{정렬된 params}:v{N}` | 인기순 정렬의 랜덤 셔플은 TTL 동안 고정 |
| `GET /plants/count` | `species-count:list:{...}:v{N}` | |
| `GET /plants/stories/popular` | `stories-popular:list:{...}:v{N}` | |

**캐시 안 함**: `/plants/favorites`, `/users/me/*`(사용자별), `/plants/recommend`,
`/plants/search/image`(AI·POST), 모든 쓰기.

### 동작 규칙
- **키 규약**: `{리소스}:{식별자}:v{CACHE_SCHEMA_VERSION}`. 목록은 쿼리 파라미터를
  **정렬**해 키를 만들어 순서만 다른 동일 쿼리가 따로 캐시되지 않는다.
- **Cache stampede 방지**: 키별 `asyncio.Lock` + 락 획득 후 **재확인(double-check)**.
  동시 N개 요청이 와도 로더(DB)는 1회만 호출된다. 락 dict는 in-flight 키만 유지(refcount)한다.
- **Negative caching**: 존재하지 않는 리소스(로더가 `None` 반환)도 짧게(`CACHE_NEGATIVE_TTL`)
  캐시해 반복 조회를 막는다. "캐시 미스"(`MISS` 센티넬)와 "캐시된 `None`"을 구분한다.
- **상세 D2-A**: `GET /plants/{id}`는 전역 문서(`get_by_id`)만 캐시한다.
  캐시된 문서는 공유 객체이므로 **복사 후** `is_favorite`를 주입한다(유저 간 오염 방지).
  조회수 증가(`increment_view_count`)는 캐시 히트와 무관하게 항상 실행된다.
- **HTTP 캐시 헤더**: 전역 읽기 응답에 `Cache-Control: public, max-age=<CACHE_TTL>`,
  `ETag`(본문 해시), `Vary: Authorization`(상세의 `is_favorite`가 토큰마다 다름)을 부여.
  `If-None-Match` 일치 시 **304**를 반환(Android OkHttp가 활용).
- **실패 격리**: 캐시 계층 예외는 로그만 남기고 **DB로 폴백**한다. 캐시 실패가 요청 실패로
  이어지지 않는다. 로더(DB) 자체 예외는 정상 전파.

### 무효화 (ETL 후)
종 데이터를 갱신하면 캐시를 비운다.

```bash
# 전체 비우기
curl -X POST http://<host>/api/v1/admin/cache/invalidate \
     -H "X-Admin-Token: $CACHE_INVALIDATE_TOKEN"

# 접두사만 (예: 종 관련만)
curl -X POST http://<host>/api/v1/admin/cache/invalidate \
     -H "X-Admin-Token: $CACHE_INVALIDATE_TOKEN" \
     -H "Content-Type: application/json" -d '{"prefix": "species"}'
```
`X-Admin-Token`이 `CACHE_INVALIDATE_TOKEN`과 불일치하면 401. **토큰 미설정(빈값)이면
엔드포인트 자체가 잠긴다**(실수로 공개되는 것 방지). 스키마가 바뀌면
`CACHE_SCHEMA_VERSION`을 올려 전체를 한 번에 무효화할 수도 있다.

### 환경 변수
| 변수 | 기본값 | 설명 |
|---|---|---|
| `CACHE_ENABLED` | `true` | `false`면 캐시를 완전히 우회(디버깅용) |
| `CACHE_TTL` | `3600` | 기본 캐시 TTL(초) = `Cache-Control max-age` |
| `CACHE_NEGATIVE_TTL` | `60` | 존재하지 않는 리소스(None) 캐시 TTL(초) |
| `CACHE_MAXSIZE` | `2048` | 최대 캐시 엔트리 수(LRU 축출) |
| `CACHE_SCHEMA_VERSION` | `1` | 캐시 키 스키마 버전(올리면 전체 무효화) |
| `CACHE_INVALIDATE_TOKEN` | `""` | 관리자 무효화 토큰. 빈값이면 무효화 API 거부 |

### ⚠️ 멀티 워커 주의 (→ Redis 이전 시점)
인메모리 캐시는 **프로세스 로컬**이다. Uvicorn worker가 1개면 문제없지만,
worker를 2개 이상으로 늘리면 캐시가 워커마다 분리되어 불일치·무효화 누락이 생긴다.
그때 `CacheBackend`를 구현한 `RedisCache`를 추가해 교체하면 워커 간 공유가 해결된다
(이 계층은 그 교체를 위해 추상화돼 있다).

### 테스트
```bash
pytest tests/test_cache.py tests/test_cache_integration.py -q
```
히트/미스, TTL 만료, stampede(동시 N요청 → 로더 1회), negative caching,
무효화, `CACHE_ENABLED=false` 우회, HTTP 헤더/ETag·304를 검증한다.

## ⭐ 인기 스토리 큐레이션

`GET /plants/stories/popular`는 **편집자가 고른 순서 있는 리스트(큐레이션)** 를 우선 사용하고,
없으면 알고리즘(인기순) 폴백. 둘 다 **결정적**이라 캐시와 정합(과거 `$rand` 셔플 제거됨).

- 저장 위치: `config` 컬렉션의 `curated_popular_stories` 문서 → `items: [{plantId, genre}, ...]`
- **초기 시드**: `python scripts/seed_curated_stories.py [개수]` (카테고리 다양성 + 이미지·스토리
  보유 + 인기순 기준 자동 구성. `--dry`로 미리보기)
- **갱신(관리자)**:
  ```bash
  curl -X POST http://<host>/api/v1/admin/curated/stories \
       -H "X-Admin-Token: $CACHE_INVALIDATE_TOKEN" -H "Content-Type: application/json" \
       -d '[{"plantId":"266","genre":"EPISODE"}, {"plantId":"1","genre":"MYTH"}]'
  ```
  저장 후 스토리 캐시(`stories-popular`)를 자동 무효화한다. 응답 스키마(`PopularStoryDto`)는 불변.

> 시간 감쇠(decay) 랭킹은 이벤트 타임스탬프 스키마가 필요해 현재는 미도입(신호가 쌓이면 재검토).
