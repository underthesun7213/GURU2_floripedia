# 배포 (EC2 + GitHub Actions, 무중단)

`main`에 `backend/**` 변경이 push되면 GitHub Actions가 테스트 → SSH로 EC2에 pull +
gunicorn graceful reload + 헬스체크를 수행한다. (워크플로: `.github/workflows/deploy.yml`)

## 사전 준비 (한 번만)

### 1. 고정 주소
- EC2에 **Elastic IP** 연결 (IP 고정). 가능하면 **도메인**을 Elastic IP로 연결.
- 안드로이드 `local.properties`의 `SERVER_URL`을 이 주소(HTTPS 권장)로 설정.

### 2. EC2 초기 설정
```bash
cd ~ && git clone https://github.com/underthesun7213/GURU2_floripedia.git
cd GURU2_floripedia/backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
# .env 생성 (MONGO_URI, GEMINI_API_KEY 등) + firebase-key.json 배치  ※ git에 올리지 말 것
sudo cp deploy/floripedia.service /etc/systemd/system/   # 경로/User 확인·수정
sudo systemctl daemon-reload && sudo systemctl enable --now floripedia
curl -s localhost:8000/health   # {"status":"healthy"}
```

### 3. Nginx + HTTPS (권장)
```bash
sudo apt install -y nginx certbot python3-certbot-nginx
sudo cp deploy/nginx.conf.example /etc/nginx/sites-available/floripedia   # server_name 수정
sudo ln -s /etc/nginx/sites-available/floripedia /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d api.example.com   # 443 + 인증서 자동
```

### 4. sudo 비번 없이 reload 허용 (Actions가 systemctl 호출)
`sudo visudo`에 추가:
```
ubuntu ALL=(ALL) NOPASSWD: /bin/systemctl reload floripedia, /bin/systemctl restart floripedia
```

### 5. GitHub Secrets 등록 (레포 Settings → Secrets and variables → Actions)
| Secret | 값 |
|---|---|
| `EC2_HOST` | Elastic IP 또는 도메인 |
| `EC2_USER` | 예: `ubuntu` |
| `EC2_SSH_KEY` | EC2 접속 개인키(pem 파일 내용 전체) |

## 무중단 원리
`systemctl reload` → gunicorn 마스터에 `HUP` → 새 코드로 워커를 새로 띄우고 준비되면
옛 워커를 graceful 종료(진행 중 요청은 끝까지 처리). 리스닝 소켓은 유지되어 연결이 끊기지 않는다.

## ⚠️ 워커 수
`gunicorn.conf.py`의 `workers=1` 유지. 인메모리 캐시가 프로세스 로컬이라 멀티 워커면
캐시가 쪼개진다. 늘리려면 캐시를 Redis로 교체(`app/cache.py`의 `CacheBackend`) 후.
