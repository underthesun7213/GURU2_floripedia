# GURU2_floripedia

Identify plants with a snap, discover their hidden stories, and find the perfect match for your emotions.  
사진 한 장으로 찾는 식물의 모든 것: 이름부터 숨겨진 이야기, 당신에게 꼭 맞는 추천까지.

## 프로젝트 구조

```
root-project/
├── android-app/             # Android Studio 프로젝트
│   ├── app/
│   │   ├── src/main/java/com/example/plant/
│   │   │   ├── ui/          # Activities, Fragments, Adapters
│   │   │   ├── data/        # Repository, ApiInterface, Models
│   │   │   └── di/          # Dependency Injection (Optional)
│   │   └── src/main/res/layout/ # XML Files
├── backend/                 # FastAPI 프로젝트
│   ├── app/
│   │   ├── main.py          # FastAPI 실행 및 라우터 등록
│   │   ├── api/             # API Endpoints (v1)
│   │   ├── services/        # Gemini API 연동, Firebase 로직
│   │   ├── models/          # MongoDB (Motor/Pydantic) 모델
│   │   └── core/            # 보안(JWT), Config 설정
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yml       # 전체 컨테이너 오케스트레이션
└── .env                     # 환경 변수 (API 키, DB URI 등)
```

## 시작하기

### 환경 설정

1. `.env.example` 파일을 참고하여 `.env` 파일을 생성하세요:
```bash
cp .env.example .env
```

2. `.env` 파일에 필요한 API 키와 설정을 입력하세요:
   - Gemini API Key
   - MongoDB Atlas URL
   - Firebase Storage Bucket
   - JWT Secret Key

### Backend 실행

#### Docker를 사용하는 경우:
```bash
docker-compose up --build
```

#### 로컬에서 실행하는 경우:
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend API는 `http://localhost:8000`에서 실행됩니다.

### Android 앱 실행

1. Android Studio에서 `android-app` 폴더를 엽니다.
2. `google-services.json` 파일을 `android-app/app/` 디렉토리에 추가하세요.
3. 프로젝트를 빌드하고 실행하세요.

## 주요 기능

- 📸 식물 사진 인식 (Gemini Vision API)
- 🌿 식물 정보 조회 및 관리
- 🔐 JWT 기반 인증
- ☁️ Firebase Storage를 통한 이미지 저장
- 🗄️ MongoDB를 통한 데이터 저장

## 기술 스택

### Backend
- FastAPI
- MongoDB (Motor)
- Google Gemini API
- Firebase Storage
- JWT 인증

### Android
- Kotlin
- Retrofit2
- Coil (이미지 로딩)
- Firebase SDK
