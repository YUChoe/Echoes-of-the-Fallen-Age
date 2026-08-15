# MUD 서버 이미지
#
# 프로덕션(Oracle Linux 7)의 파이썬이 3.9 라 맨몸 배포가 성립하지 않는다.
# `aiohttp` 가 3.10 이상을 요구하고 코드가 PEP 604 유니온(`X | None`)을 쓴다.
# 서버만 컨테이너로 돌리고 게이트웨이는 호스트에서 Node 로 띄운다.
#
# 빌드 산출물이 아니라 소스를 그대로 담는다. 파이썬은 빌드 단계가 없고, 다단계로
# 나눠도 줄어드는 것이 없다.

FROM python:3.14-slim

ARG VERSION=unknown
ARG VCS_REF=unknown
ARG BUILD_DATE=unknown

LABEL org.opencontainers.image.title="Echoes of the Fallen Age" \
      org.opencontainers.image.description="MUD server. JSON line protocol on TCP 4000, admin on 4001" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}"

WORKDIR /app

# 의존성은 모두 휠로 받는다. lupa 와 bcrypt 는 컴파일 확장이지만 manylinux 휠이
# 있어 빌드 도구가 필요하지 않다. 휠이 없는 환경이면 이 단계가 실패하므로
# 조용히 소스 빌드로 넘어가지 않게 --only-binary 로 막는다
COPY requirements.txt ./
RUN pip install --no-cache-dir --only-binary=:all: -r requirements.txt

# 서버가 실행 중에 읽는 것들이다. configs 는 Lua 스크립트를 매 호출 디스크에서
# 읽으므로(핫 리로드) 볼륨으로 덮어쓰면 이미지 사본이 가려진다
COPY src/ ./src/
COPY configs/ ./configs/

# 버전 정보는 빌드 인자로 받는다. 예전에는 .git 을 통째로 복사해 스크립트를
# 돌렸는데 이력이 이미지 레이어에 남았다
RUN printf '{"commit_hash":"%s","commit_hash_full":"%s","branch":"container","commit_date":"%s","version":"%s"}\n' \
    "${VCS_REF}" "${VCS_REF}" "${BUILD_DATE}" "${VERSION}" \
    > src/mud_engine/version_info.json

RUN mkdir -p data logs

ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    TELNET_HOST=0.0.0.0 \
    TELNET_PORT=4000 \
    ADMIN_HOST=0.0.0.0 \
    ADMIN_PORT=4001

# 어드민 포트를 컨테이너 안에서 0.0.0.0 에 여는 것은 호스트의 게이트웨이가
# 닿아야 하기 때문이다. 외부 노출은 발행 단계에서 127.0.0.1 로 묶는다
EXPOSE 4000 4001

# 루트로 돌리지 않는다. 볼륨 소유자도 이 uid 로 맞춰야 한다
RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin mud \
    && chown -R mud:mud /app
USER mud

# 종료는 SIGTERM 이다. ShutdownSignal 이 받아 WAL 체크포인트까지 수행한다.
# 쉘을 거치지 않는 exec 형식이라 신호가 파이썬에 직접 간다
CMD ["python", "-m", "src.mud_engine.main"]
