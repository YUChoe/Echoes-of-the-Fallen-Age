# Python 3.13 기반 이미지 사용
FROM python:3.13-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 필요한 패키지 설치
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY src/ ./src/

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
