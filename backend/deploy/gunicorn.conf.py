"""
Gunicorn 설정 (Uvicorn worker). 무중단 배포용.

- worker_class = uvicorn worker → FastAPI(ASGI) 구동.
- workers = 1 : 인메모리 캐시가 프로세스 로컬이라 일관성 위해 단일 워커 유지.
                (멀티 워커로 늘리려면 캐시를 Redis로 교체 후 — app/cache.py 참고)
- systemd `ExecReload=kill -s HUP` → gunicorn이 워커를 graceful 교체(진행 중 요청 유지).
"""
bind = "127.0.0.1:8000"
workers = 1
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120          # AI/이미지 요청이 길 수 있어 넉넉히
graceful_timeout = 30
keepalive = 5
accesslog = "-"        # stdout → journald
errorlog = "-"
