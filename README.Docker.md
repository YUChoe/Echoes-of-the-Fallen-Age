# Docker 배포 가이드

## 개요

이 프로젝트는 Docker를 사용하여 Python MUD Engine을 컨테이너화하여 배포할 수 있습니다.

## 파일 구조

```
.
├── Dockerfile              # Docker 이미지 빌드 파일
├── docker-compose.yml      # 프로덕션 환경 설정
├── docker-compose.dev.yml  # 개발 환경 설정
├── .dockerignore           # Docker 빌드 시 제외할 파일
└── volumes/                # 영속 데이터 저장 (자동 생성)
    ├── data/               # 데이터베이스 파일
    └── logs/               # 로그 파일
```

## 빠른 시작

### 1. 프로덕션 환경 실행

```bash
# 이미지 빌드 및 컨테이너 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 컨테이너 중지
docker-compose down
```

### 2. 개발 환경 실행

```bash
# 개발 환경으로 시작 (소스 코드 마운트)
docker-compose -f docker-compose.dev.yml up -d

# 로그 확인
docker-compose -f docker-compose.dev.yml logs -f

# 컨테이너 중지
docker-compose -f docker-compose.dev.yml down
```

## 상세 설정

### 환경 변수

`.env` 파일을 생성하여 환경 변수를 설정할 수 있습니다:

```bash
# .env 파일 예시
SECRET_KEY=your-production-secret-key
DEBUG=False
LOG_LEVEL=INFO
DEFAULT_LOCALE=ko
```

### 포트 설정

기본적으로 Telnet 서버는 4000번 포트를 사용합니다. 다른 포트를 사용하려면 `docker-compose.yml`을 수정하세요:

```yaml
ports:
  - "4001:4000"  # 호스트:컨테이너
```

### 볼륨 관리

데이터와 로그는 `volumes/` 디렉토리에 영속적으로 저장됩니다:

- `volumes/data/`: 데이터베이스 파일 (mud_engine.db)
- `volumes/logs/`: 로그 파일 (mud_engine-*.log)

#### 데이터 백업

```bash
# 데이터 백업
tar -czf backup-$(date +%Y%m%d).tar.gz volumes/data/

# 데이터 복원
tar -xzf backup-20241207.tar.gz
```

## Docker 명령어

### 이미지 관리

```bash
# 이미지 빌드
docker-compose build

# 이미지 강제 재빌드
docker-compose build --no-cache

# 이미지 목록 확인
docker images | grep mud-engine
```

### 컨테이너 관리

```bash
# 컨테이너 시작
docker-compose up -d

# 컨테이너 중지
docker-compose down

# 컨테이너 재시작
docker-compose restart

# 컨테이너 상태 확인
docker-compose ps

# 컨테이너 로그 확인
docker-compose logs -f

# 컨테이너 내부 접속
docker-compose exec mud-engine bash
```

### 데이터 관리

```bash
# 볼륨 확인
docker volume ls

# 볼륨 정리 (주의: 데이터 삭제됨)
docker-compose down -v

# 데이터베이스 직접 접근
docker-compose exec mud-engine python -c "import sqlite3; conn = sqlite3.connect('/app/data/mud_engine.db'); print(conn.execute('SELECT COUNT(*) FROM players').fetchone())"
```

## 개발 환경

개발 환경에서는 소스 코드가 컨테이너에 마운트되어 코드 변경 시 즉시 반영됩니다:

```bash
# 개발 환경 시작
docker-compose -f docker-compose.dev.yml up -d

# 코드 수정 후 컨테이너 재시작
docker-compose -f docker-compose.dev.yml restart

# 개발 환경 로그 확인 (DEBUG 레벨)
docker-compose -f docker-compose.dev.yml logs -f
```

## 프로덕션 배포

### 1. 환경 변수 설정

```bash
# .env 파일 생성
cat > .env << EOF
SECRET_KEY=$(openssl rand -hex 32)
DEBUG=False
LOG_LEVEL=INFO
DEFAULT_LOCALE=ko
EOF
```

### 2. 이미지 빌드 및 배포

```bash
# 이미지 빌드
docker-compose build

# 백그라운드에서 실행
docker-compose up -d

# 상태 확인
docker-compose ps
docker-compose logs -f
```

### 3. 헬스체크

```bash
# 컨테이너 헬스 상태 확인
docker inspect --format='{{.State.Health.Status}}' mud-engine

# Telnet 연결 테스트
telnet localhost 4000
```

## 문제 해결

### 컨테이너가 시작되지 않는 경우

```bash
# 로그 확인
docker-compose logs

# 컨테이너 상태 확인
docker-compose ps

# 컨테이너 재시작
docker-compose restart
```

### 데이터베이스 초기화

```bash
# 컨테이너 중지
docker-compose down

# 데이터 삭제 (주의!)
rm -rf volumes/data/*

# 컨테이너 재시작 (새 데이터베이스 생성)
docker-compose up -d
```

### 로그 확인

```bash
# 실시간 로그
docker-compose logs -f

# 최근 100줄
docker-compose logs --tail=100

# 특정 시간 이후 로그
docker-compose logs --since 30m
```

## 보안 고려사항

1. **SECRET_KEY 변경**: 프로덕션 환경에서는 반드시 강력한 SECRET_KEY를 설정하세요.
2. **포트 노출**: 필요한 포트만 노출하세요.
3. **로그 관리**: 민감한 정보가 로그에 기록되지 않도록 주의하세요.
4. **정기 업데이트**: 베이스 이미지와 의존성을 정기적으로 업데이트하세요.

## 성능 최적화

### 멀티스테이지 빌드 (선택사항)

더 작은 이미지 크기를 원한다면 Dockerfile을 멀티스테이지 빌드로 수정할 수 있습니다:

```dockerfile
# 빌드 스테이지
FROM python:3.13-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# 실행 스테이지
FROM python:3.13-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY src/ ./src/
COPY configs/ ./configs/
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app
CMD ["python", "-m", "src.mud_engine.main"]
```

## 모니터링

### Docker Stats

```bash
# 리소스 사용량 확인
docker stats mud-engine

# 모든 컨테이너 리소스 확인
docker-compose stats
```

### 로그 모니터링

```bash
# 에러 로그만 필터링
docker-compose logs | grep ERROR

# 특정 플레이어 로그 필터링
docker-compose logs | grep "player5426"
```

## 참고 자료

- [Docker 공식 문서](https://docs.docker.com/)
- [Docker Compose 문서](https://docs.docker.com/compose/)
- [Python Docker 이미지](https://hub.docker.com/_/python)
