# 🌸 GURU2_floripedia

> **Identify plants with a snap, discover their hidden stories, and find the perfect match for your emotions.**  
> 사진 한 장으로 찾는 식물의 모든 것: 이름부터 숨겨진 이야기, 당신에게 꼭 맞는 추천까지.

Floripedia는 AI 기반 식물 식별, 감성 추천, 그리고 풍부한 식물 정보를 제공하는 통합 플랫폼입니다.

---

## 📑 목차

- [주요 기능](#-주요-기능)
- [화면 구성](#-화면-구성)
- [기술 스택](#-기술-스택)
- [프로젝트 구조](#-프로젝트-구조)
- [시스템 아키텍처](#-시스템-아키텍처)
- [설계 결정](#-설계-결정)
- [다운로드](#-다운로드)
- [API 문서](#-api-문서)
- [데이터베이스 스키마](#-데이터베이스-스키마)
- [테스트](#-테스트)

---

## 🌟 주요 기능

### 🔍 AI 기반 식물 검색

#### 1. 이미지 검색 (Vision Search)
- **Gemini Vision API** 를 활용한 실시간 식물 식별
- 사진 한 장으로 식물의 한글명, 영문명, 학명 자동 인식
- **3단계 매칭 전략**: 학명 정확 → 이름 정확 → 학명 퍼지(속 기준)
- 사전 큐레이션된 DB 기반의 신뢰할 수 있는 식물 정보 제공

#### 2. 텍스트 기반 추천 (Emotion-Based Recommendation)
- 사용자 상황/감정 입력 시 **AI가 맞춤형 식물 추천**
- Gemini가 상황에 맞는 감성 에세이 자동 생성
- 예시: "친구와 화해하고 싶어요" → "물망초" 추천 + 감동적인 추천 에세이

### 🌿 식물 정보 탐색

#### 다층 필터링 시스템
- **계절별 검색** (봄, 여름, 가을, 겨울)
- **개화 월별 검색** (1~12월)
- **4대 카테고리 그룹**
  - 꽃과 풀
  - 나무와 조경
  - 실내 인테리어
  - 텃밭과 정원
- **5가지 색상 그룹**
  - 백색/미색, 노랑/주황, 빨강/분홍, 푸른색, 갈색/검정
- **4가지 향기 그룹**
  - 달콤·화사, 싱그러운·시원, 은은·차분, 무향
- **5가지 꽃말 감성 그룹**
  - 사랑/고백, 위로/슬픔, 감사/존경, 이별/그리움, 행복/즐거움
- **스토리 장르별 탐색**
  - 신화/전설, 과학, 역사, 예술, 에피소드

#### 상세 정보 제공
- 🏷️ **기본 정보**: 학명, 과명, 원산지, 생육 환경
- 🌈 **색상 정보**: HEX 코드, 색상 라벨, 색상 그룹
- 🌺 **꽃말 & 감성 그룹**: 꽃말 의미와 감성 분류
- 📖 **스토리 컬렉션**: 신화, 역사, 예술 등 다양한 이야기
- 🌱 **원예 정보**: 관리법, 용도, 카테고리 분류
- 👃 **향기 정보**: 향기 태그와 향기 그룹

### 💖 사용자 기능

- **꽃갈피 (찜하기)**: 마음에 드는 식물 저장
- **마이페이지**: 프로필, 레벨/경험치(씨앗→식물 마스터), 찜 목록
- **무마찰 온보딩**: 로그인 화면 없이 Firebase 익명 인증으로 즉시 사용
- **프로필 이미지 업로드**: Firebase Storage 연동

---

## 📱 화면 구성

| 스플래시 | 홈 | AI 탐색 | 상세 | 검색 |
|:---:|:---:|:---:|:---:|:---:|
| <img src="docs/screenshots/splash.png" width="150"> | <img src="docs/screenshots/home.png" width="150"> | <img src="docs/screenshots/explore.png" width="150"> | <img src="docs/screenshots/detail.png" width="150"> | <img src="docs/screenshots/search.png" width="150"> |
| 로딩 화면 | 히어로 캐러셀 · 계절 필터 · 인기 스토리 | 상황 입력 → AI 식물 추천 | 이미지 · 꽃말 · 스토리 · 분류 | 키워드 검색 결과 |

---

## 🛠 기술 스택

### Backend
- **프레임워크**: FastAPI 0.115.0
- **데이터베이스**: MongoDB (Motor 3.6.0)
- **AI/ML**: Google Gemini (google-genai 1.65.0) — basic: gemini-3.1-flash-lite, essay: gemini-3.5-flash
- **인증**: Firebase Admin SDK 6.5.0 (익명 인증 + App Check)
- **이미지 처리**: Pillow 10.4.0
- **HTTP 클라이언트**: httpx 0.28.1
- **캐시**: 인메모리 계층 (cachetools, Redis 교체 대비 추상화)

### Android
- **언어**: Kotlin
- **HTTP 클라이언트**: Retrofit2
- **이미지 로딩**: Coil
- **인증**: Firebase SDK

### Infrastructure
- **클라우드 저장소**: Firebase Storage
- **배포**: AWS EC2 + GitHub Actions (SSH 무중단 배포), Nginx + HTTPS
- **ASGI/프로세스 매니저**: Uvicorn 0.32.0 + Gunicorn 23.0.0

---

## 📂 프로젝트 구조

```
GURU2_floripedia/
├── android-app/                    # Android 앱
│   ├── app/
│   │   ├── src/main/java/com/example/plant/
│   │   │   ├── ui/                # UI 레이어 (Activities, Fragments, Adapters)
│   │   │   ├── data/              # 데이터 레이어 (Repository, API, Models)
│   │   │   ├── util/              # 유틸리티 (InputValidator, ErrorHandler)
│   │   │   └── di/                # 의존성 주입
│   │   ├── src/main/res/          # 리소스 (layout, drawable, values)
│   │   └── src/test/              # Unit Tests (50개)
│   └── build.gradle
│
├── backend/                        # FastAPI 백엔드
│   ├── app/
│   │   ├── main.py                # 애플리케이션 진입점
│   │   │
│   │   ├── api/v1/                # API 엔드포인트
│   │   │   └── endpoints/
│   │   │       ├── auth.py        # 인증 (로그인/회원가입)
│   │   │       ├── users.py       # 유저 프로필 관리
│   │   │       ├── plants.py      # 식물 검색/조회/필터링
│   │   │       └── deps.py        # 의존성 주입
│   │   │
│   │   ├── services/              # 비즈니스 로직
│   │   │   ├── gemini_service.py  # Gemini AI 통합
│   │   │   ├── auth_service.py    # Firebase 인증
│   │   │   ├── user_service.py    # 유저 관리
│   │   │   ├── plant_service.py   # 식물 검색/생성/관리
│   │   │   └── firebase_service.py # Firebase Storage 연동
│   │   │
│   │   ├── repositories/          # 데이터 접근 계층
│   │   │   ├── user_repository.py
│   │   │   └── plant_repository.py
│   │   │
│   │   ├── schemas/               # Pydantic 스키마
│   │   │   ├── user.py
│   │   │   └── plant.py
│   │   │
│   │   ├── models/                # MongoDB 모델
│   │   │   ├── user.py
│   │   │   └── plant.py
│   │   │
│   │   ├── core/                  # 핵심 설정
│   │   │   ├── config.py          # 환경 변수 관리
│   │   │   └── security.py        # JWT 토큰 관리
│   │   │
│   │   └── db/                    # 데이터베이스 연결
│   │       ├── session.py         # MongoDB 연결
│   │       └── firebase.py        # Firebase 초기화
│   │
│   ├── scripts/                   # 데이터 전처리 스크립트
│   │   ├── augmentation/
│   │   │   └── build_data.py      # 데이터 증강
│   │   ├── cleaning/              # 데이터 정제
│   │   ├── open_data/             # 공공 데이터 수집
│   │   └── upload_to_mongodb.py   # DB 업로드
│   │
│   ├── tests/                     # pytest 테스트 (98개)
│   ├── data/                      # 데이터셋
│   └── requirements.txt           # Python 패키지
│
├── .env                           # 환경 변수 (gitignore)
└── README.md
```

---

## 🏗 시스템 아키텍처

### 전체 구조

```
┌─────────────────┐
│  Android App    │
│   (Kotlin)      │
└────────┬────────┘
         │ HTTP/REST
         ↓
┌─────────────────────────────────────────┐
│         FastAPI Backend                 │
│  ┌────────────────────────────────────┐ │
│  │   API Layer (Endpoints)            │ │
│  └───────────────┬────────────────────┘ │
│                  ↓                       │
│  ┌────────────────────────────────────┐ │
│  │   Service Layer                    │ │
│  │   - PlantService                   │ │
│  │   - GeminiService                  │ │
│  │   - AuthService                    │ │
│  │   - UserService                    │ │
│  └───────────────┬────────────────────┘ │
│                  ↓                       │
│  ┌────────────────────────────────────┐ │
│  │   Repository Layer                 │ │
│  │   (Data Access)                    │ │
│  └───────────────┬────────────────────┘ │
└──────────────────┼──────────────────────┘
                   │
         ┌─────────┴──────────┐
         ↓                    ↓
    ┌─────────┐         ┌──────────┐
    │ MongoDB │         │ Firebase │
    │ Atlas   │         │ Storage  │
    └─────────┘         └──────────┘
         ↑
         │ AI Processing
    ┌────────────────┐
    │  Gemini API    │
    │ (Google AI)    │
    └────────────────┘
```

### 식물 검색 플로우 (이미지)

```
1. 사용자 → 이미지 업로드
2. FastAPI → Gemini Vision API (식물 식별: 이름, 학명 추출)
3. FastAPI → MongoDB 조회 (3단계 매칭)
   ├─ 1차: 학명 정확 일치
   ├─ 2차: 이름 정확 일치
   └─ 3차: 학명 퍼지 매칭 (속 기준)
4. FastAPI → 사용자 (식물 정보 반환 또는 404)
```

### 학명 매칭 전략

```
Gemini 반환값: { name: "장미", scientificName: "Rosa rugosa" }
                              ↓
                    ┌─────────────────────┐
                    │  3단계 DB 조회       │
                    └─────────────────────┘
                              ↓
    1차: scientificName = "Rosa rugosa" (정확 일치)
                    → 없음
                              ↓
    2차: name = "장미" (정확 일치)
                    → 없음
                              ↓
    3차: scientificName LIKE "Rosa%" (속 기준 퍼지 매칭)
                    → "Rosa canina" 발견!
                              ↓
                      결과 반환
```

> **DB-only 모드**: 모든 식물 데이터는 사전 큐레이션된 DB에서만 조회됩니다.
> DB에 없는 식물은 404 응답을 반환합니다.

---

## 🧭 설계 결정

주요 기술 선택의 **배경과 트레이드오프**를 기록합니다.

### 1. 로그인 대신 익명 인증 (무마찰 온보딩)
- **문제**: 소셜/커뮤니티 기능이 없는 유틸형 앱에서 로그인 강제는 이탈만 키움. 하지만 AI(Gemini) 호출은 건당 과금이라 **비용/어뷰징 통제**가 필요.
- **결정**: 로그인 화면을 없애고 앱 첫 실행 시 **Firebase 익명 인증**으로 세션 발급. 사용자는 아무 행동 없이 바로 사용하되, 백엔드는 익명 `uid` 기반으로 찜·레벨·요청 주체를 그대로 식별.
- **효과**: 로그인 UX 마찰 제거 + 기존 `uid` 기반 기능(찜/레벨) 무변경 유지. 향후 "익명 → 정식 계정" 승격도 가능.

### 2. 다층 봇/어뷰징 방어 (AI 원가 보호)
클라이언트 게이팅(로그인 버튼·광고)은 API를 직접 때리는 봇을 못 막으므로, **서버 측**에 방어를 둠.
- **인증 필수화**: AI 엔드포인트(`/recommend`, `/search/image`)는 유효 Firebase 토큰(익명 포함) 없으면 거부.
- **Firebase App Check**: "정품 앱에서 온 요청"임을 검증(`X-Firebase-AppCheck` 헤더 → 백엔드 검증). `monitor → enforce` 단계적 전환으로 무중단 롤아웃.
- **최후 방어선**: Gemini 예산/할당량 상한(배포 시).

### 3. 인메모리 캐시 + 단일 워커
- 읽기 중심 트래픽에 인메모리 캐시(TTL·네거티브 캐싱)로 DB/AI 호출 절감. 캐시가 프로세스 로컬이라 gunicorn `workers=1` 유지.
- **확장 대비**: `CacheBackend` 추상화로 트래픽 증가 시 Redis 교체 가능하게 설계.

### 4. 무중단 배포 (graceful reload)
- `git push → 테스트 → SSH → gunicorn graceful reload → 헬스체크`. 새 워커가 준비되면 옛 워커를 교체해 진행 중 요청을 끊지 않음. (`backend/deploy/` 참고)

---

## 📲 다운로드

> **별도 회원가입 없이, 설치 후 바로 사용할 수 있습니다.** 첫 실행 시 Firebase 익명 세션이 자동 생성됩니다.

**Google Play** — 출시 준비 중
<!-- TODO: 출시 후 스토어 링크 추가 -->

### 기술 리뷰어용

앱을 직접 빌드하지 않아도, 배포된 백엔드 API를 라이브 문서(Swagger UI)에서 바로 확인할 수 있습니다.

- 🔗 **라이브 API 문서**: https://floripedia.juha.dev/docs
- 설계 의도는 [시스템 아키텍처](#-시스템-아키텍처) · [설계 결정](#-설계-결정) 참고

---

## 📡 API 문서

### Base URL
```
https://floripedia.juha.dev/api/v1
```

### 인증 (Authentication)

> 앱은 첫 실행 시 **Firebase 익명 인증**으로 세션을 만들고, 그 ID Token으로 `/auth/login`을 호출해 유저 문서를 생성합니다. 별도 로그인 화면 없이 즉시 사용 가능합니다.

#### POST `/auth/login`
Firebase ID Token 기반 로그인/자동 회원가입 (익명 토큰 포함)

**Request Body:**
```json
{
  "idToken": "<firebase-id-token>",
  "termsAgreed": true,
  "privacyAgreed": true
}
```
> `termsAgreed`/`privacyAgreed`는 신규 가입 시 동의 캡처용(선택).

**Response:**
```json
{
  "id": "user_id",
  "email": null,
  "nickname": "달콤한 햇살",
  "profileImageUrl": "https://...",
  "createdAt": "2026-01-01T00:00:00"
}
```
> 익명 세션은 `email`이 `null`이고, 닉네임은 랜덤 부여됩니다.

#### GET `/auth/check-email?email={email}`
이메일 중복 확인

---

### 식물 검색 (Plants)

#### POST `/plants/search/image`
이미지 기반 식물 검색 (Vision Search)

**Request:**
- Content-Type: `multipart/form-data`
- Body: `file` (이미지 파일)
- Header: `Authorization: Bearer {firebase_token}` (선택)

**Response:**
```json
{
  "id": "plant_id",
  "name": "장미",
  "englishName": "Rose",
  "scientificName": "Rosa hybrida",
  "imageUrl": "https://...",
  "images": ["url1", "url2", "url3"],
  "isNewlyCreated": true,
  "isFavorite": false,
  "taxonomy": {
    "genus": "Rosa",
    "species": "hybrida",
    "family": "장미과"
  },
  "flowerInfo": {
    "language": "사랑",
    "flowerGroup": "사랑/고백"
  },
  "colorInfo": {
    "hexCodes": ["#FF0000"],
    "colorLabels": ["빨강"],
    "colorGroup": ["빨강/분홍"]
  },
  "scentInfo": {
    "scentTags": ["달콤한", "향긋한"],
    "scentGroup": ["달콤·화사"]
  },
  "horticulture": {
    "category": "관목",
    "categoryGroup": "나무와 조경",
    "usage": ["관상용"],
    "management": "햇빛을 좋아하며...",
    "preContent": "장미는..."
  },
  "stories": [
    {
      "genre": "MYTH",
      "content": "그리스 신화에서..."
    }
  ],
  "season": "SPRING",
  "bloomingMonths": [4, 5, 6],
  "habitat": "온대 기후",
  "searchKeywords": ["장미", "Rose", "로즈"],
  "viewCount": 0,
  "favoriteCount": 0
}
```

#### POST `/plants/recommend?situation={text}`
상황 기반 식물 추천 + 감성 에세이

**Query Parameter:**
- `situation`: "친구에게 사과하고 싶어요"

**Response:**
```json
{
  "id": "plant_id",
  "name": "물망초",
  "recommendation": "친구와의 소중한 인연을 되새기게 하는 물망초를 추천드립니다...",
  ... (식물 정보)
}
```

#### GET `/plants`
식물 목록 조회 (필터링 + 페이지네이션)

**Query Parameters:**
- `season`: SPRING | SUMMER | FALL | WINTER
- `blooming_month`: 1-12
- `category_group`: 꽃과 풀 | 나무와 조경 | 실내 인테리어 | 텃밭과 정원
- `color_group`: 백색/미색 | 노랑/주황 | 빨강/분홍 | 푸른색 | 갈색/검정
- `scent_group`: 달콤·화사 | 싱그러운·시원 | 은은·차분 | 무향
- `flower_group`: 사랑/고백 | 위로/슬픔 | 감사/존경 | 이별/그리움 | 행복/즐거움
- `story_genre`: MYTH | SCIENCE | HISTORY | ART | EPISODE
- `keyword`: 검색어
- `skip`: 0 (기본값)
- `limit`: 20 (기본값, 최대 100)
- `sort_by`: name | viewCount | favoriteCount
- `sort_order`: asc | desc

**Response:**
```json
[
  {
    "id": "plant_id",
    "name": "장미",
    "imageUrl": "https://...",
    "flowerInfo": {
      "language": "사랑",
      "flowerGroup": "사랑/고백"
    }
  },
  ...
]
```

#### GET `/plants/count`
필터 조건에 맞는 식물 총 개수

**Query Parameters:** (위와 동일)

**Response:**
```json
{
  "count": 152
}
```

#### GET `/plants/{plant_id}`
식물 상세 정보 조회

**Path Parameter:**
- `plant_id`: 식물 ID

**Header:** (선택)
- `Authorization: Bearer {firebase_token}`

**Response:** (POST /plants/search/image와 동일)

#### GET `/plants/stories/popular`
인기 스토리 큐레이션 목록

---

### 사용자 (Users)

> 🔒 표시는 인증 필수. 앱은 익명 세션 토큰으로 자동 인증되므로 별도 로그인 없이 호출됩니다.

#### GET `/users/me` 🔒
내 프로필 조회 (닉네임, 레벨/경험치, 찜 목록 등)

**Header:** `Authorization: Bearer {firebase_token}`

**Response:**
```json
{
  "id": "user_id",
  "email": null,
  "nickname": "달콤한 햇살",
  "profileImageUrl": "https://...",
  "favoritePlantIds": ["1", "2"],
  "levelInfo": { "level": 1, "title": "씨앗", "totalExp": 20, "nextLevelExp": 30 },
  "createdAt": "2026-01-01T00:00:00"
}
```
> 익명 세션은 `email`이 `null`입니다.

#### PATCH `/users/me` 🔒
프로필 수정

**Request Body:** `{ "nickname": "새로운 닉네임" }`

#### POST `/users/me/profile-image` 🔒
프로필 이미지 업로드 (`multipart/form-data`, `file`)

#### POST `/users/me/favorites/{plant_id}` 🔒
식물 찜 토글 (추가/취소)

#### GET `/users/me/favorites` 🔒
내 꽃갈피(찜) 목록 조회 — 필터(`season`, `category_group`, `color_group`) + 페이지네이션(`skip`, `limit`)

#### GET `/users/me/favorites/count` 🔒
내 찜 개수

#### POST `/users/logout` 🔒
로그아웃

#### DELETE `/users/me` 🔒
회원 탈퇴

---

### 헬스체크

#### GET `/`
API 정보

#### GET `/health`
서비스 상태 확인

---

## 🗄 데이터베이스 스키마

### Users Collection

```javascript
{
  _id: ObjectId,
  uid: String,              // Firebase UID (unique)
  email: String,            // 이메일
  display_name: String,     // 닉네임
  profile_image_url: String, // 프로필 이미지
  favorites: [String],      // 찜한 식물 ID 배열
  created_at: ISODate,
  updated_at: ISODate
}
```

### Plants Collection

```javascript
{
  _id: String,              // UUID
  name: String,             // 한글 이름
  english_name: String,     // 영문 이름
  scientific_name: String,  // 학명 (unique)
  
  // 학술 정보
  taxonomy: {
    genus: String,          // 속
    species: String,        // 종
    family: String          // 과
  },
  
  // 꽃말 정보
  flower_info: {
    language: String,       // 꽃말
    flower_group: String    // 감성 그룹
  },
  
  // 색상 정보
  color_info: {
    hex_codes: [String],    // HEX 코드 배열
    color_labels: [String], // 색상 라벨
    color_group: [String]   // 색상 그룹 (복수 가능)
  },
  
  // 향기 정보
  scent_info: {
    scent_tags: [String],   // 향기 태그
    scent_group: [String]   // 향기 그룹 (복수 가능)
  },
  
  // 원예 정보
  horticulture: {
    category: String,         // 원예 분류
    category_group: String,   // 4대 카테고리
    usage: [String],          // 용도
    management: String,       // 관리법
    pre_content: String       // 사전 설명
  },
  
  // 스토리
  stories: [
    {
      genre: String,        // MYTH, SCIENCE, HISTORY, ART, EPISODE
      content: String       // 스토리 내용
    }
  ],
  
  // 기타
  season: String,           // SPRING, SUMMER, FALL, WINTER
  blooming_months: [Number], // 개화 월 (1-12)
  habitat: String,          // 서식지
  search_keywords: [String], // 검색 키워드
  
  // 이미지
  image_url: String,        // 대표 이미지
  images: [String],         // 추가 이미지
  
  // 통계
  view_count: Number,       // 조회수
  favorite_count: Number,   // 찜 개수
  
  created_at: ISODate
}
```

### 인덱스

```javascript
// Users
db.users.createIndex({ "uid": 1 }, { unique: true })
db.users.createIndex({ "email": 1 })

// Plants
db.plants.createIndex({ "scientific_name": 1 }, { unique: true })
db.plants.createIndex({ "name": 1 })
db.plants.createIndex({ "season": 1 })
db.plants.createIndex({ "horticulture.category_group": 1 })
db.plants.createIndex({ "color_info.color_group": 1 })
db.plants.createIndex({ "scent_info.scent_group": 1 })
db.plants.createIndex({ "flower_info.flower_group": 1 })
db.plants.createIndex({ "search_keywords": 1 })
```

---

## 🧪 테스트

**총 148개 테스트** (Backend 98 + Android 50) — 에뮬레이터/서버 없이 전부 로컬 실행 가능.

### Backend (pytest, 98개)

```bash
cd backend
pip install -r requirements-dev.txt
pytest -v
```

```
backend/tests/
├── conftest.py                  # 공통 Fixture (MongoDB Mock, Gemini Mock, TestClient)
├── test_plant_repository.py     # Repository 단위 테스트 (8개)
├── test_plant_service.py        # 이미지 검색 · 추천 통합 테스트 (7개)
├── test_user_repository.py      # User Repository 테스트 (6개)
├── test_services.py             # Auth · User Service 테스트 (17개)
├── test_api.py                  # API 엔드포인트 E2E 테스트 (10개)
├── test_cache.py                # 캐시 계층 단위 테스트 (13개)
├── test_cache_integration.py    # 캐시 통합 테스트 (9개)
├── test_curated_stories.py      # 스토리 큐레이션 (4개)
└── test_level_system.py         # 레벨/경험치 시스템 (24개)
```

| 레이어 | 테스트 파일 | 주요 검증 |
|---|---|---|
| Repository | `test_plant_repository.py` | 학명 퍼지 매칭, 이름 조회, 대소문자 무시 |
| Repository | `test_user_repository.py` | 소프트 삭제, 찜 추가/중복/제거 |
| Service | `test_plant_service.py` | Gemini 이미지 검색, 추천 에세이 생성, 에러 핸들링 |
| Service | `test_services.py` | 익명/토큰 검증, 동의 캡처, 랜덤 닉네임, 프로필, 찜 토글 |
| API | `test_api.py` | 식물 목록/상세/검색, 인증, 프로필, 파일 업로드 |
| Cache | `test_cache*.py` | TTL·무효화·네거티브 캐싱, 서비스 통합 |
| Domain | `test_level_system.py` | 경험치 적립, 레벨 임계값, 칭호 산정 |

### Android (JUnit + MockWebServer, 50개)

```bash
cd android-app
./gradlew testDebugUnitTest
```

```
app/src/test/java/com/example/plant/
├── util/
│   ├── InputValidatorTest.kt     # 입력값 검증 (20개)
│   └── ErrorHandlerTest.kt       # 에러 처리 (11개)
├── data/model/
│   └── FilterValidatorTest.kt    # 필터 검증 (13개)
└── data/api/
    └── ApiParsingTest.kt         # API JSON 파싱 (5개)
```

| 테스트 파일 | 주요 검증 |
|---|---|
| `InputValidatorTest` | 비밀번호/닉네임/상황/이미지 포맷/사이즈/검색어 |
| `ErrorHandlerTest` | 인증 에러 판별, 예외별 메시지 변환 |
| `FilterValidatorTest` | FilterType별 유효값 검증, getValidValues 개수 |
| `ApiParsingTest` | MockWebServer로 PlantCardDto/PlantDetailDto/UserResponse/FavoriteToggleResponse 파싱, 404 처리 |

### Postman Collection

```
backend/postman/floripedia_api.postman_collection.json
```

Postman → Import → File 선택 후 사용. `base_url`: `http://localhost:8000`

---

## 📝 라이선스

© 2026 GURU2. All rights reserved.

본 저장소는 포트폴리오 용도로 공개되어 있습니다. 코드·데이터·에셋의 무단 복제, 재배포, 상업적 이용을 금합니다.

---

## 👥 팀

GURU2 팀 - 식물과 AI의 만남

---

## 📧 문의

프로젝트 관련 문의사항은 Issues를 통해 남겨주세요.
