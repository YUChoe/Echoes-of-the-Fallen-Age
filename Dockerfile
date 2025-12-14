# Python 3.13 기반 이미지 사용
FROM python:3.13-slim

# 빌드 인자 정의
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

# 메타데이터 라벨 추가
LABEL maintainer="MUD Engine Team" \
      org.opencontainers.image.title="MUD Engine" \
      org.opencontainers.image.description="Python-based MUD (Multi-User Dungeon) Engine" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.source="https://github.com/your-org/mud-engine"

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 필요한 패키지 설치
RUN apt-get update && apt-get install -y \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Git 정보와 버전 생성 스크립트 복사
COPY .git/ ./.git/
COPY scripts/generate_version_info.py ./scripts/

# 빌드 시점에 버전 정보 생성 (필수)
RUN python scripts/generate_version_info.py

# 소스 코드 복사
COPY src/ ./src/

# Git 디렉토리 제거 (보안상 프로덕션 이미지에서 제거)
RUN rm -rf .git scripts/

# 환경 변수 설정
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 데이터 및 로그 디렉토리 생성
RUN mkdir -p /app/data /app/logs

# Telnet 포트 노출
EXPOSE 4000

# 헬스체크 (선택사항)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import socket; s=socket.socket(); s.connect(('localhost', 4000)); s.close()" || exit 1

# 애플리케이션 실행
CMD ["python", "-m", "src.mud_engine.main"]
