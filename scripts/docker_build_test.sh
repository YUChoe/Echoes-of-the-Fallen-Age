#!/bin/bash
# -*- coding: utf-8 -*-
"""Docker 빌드 테스트 스크립트"""

set -e

echo "🐳 Docker 빌드 테스트 시작"

# 1. 버전 정보 생성 (로컬에서 확인용)
echo "📝 로컬 버전 정보 생성..."
python scripts/generate_version_info.py

# 2. Docker 빌드 인자 준비
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
VCS_REF=$(git rev-parse HEAD)
COMMIT_HASH=$(git rev-parse --short HEAD)
VERSION=$(git describe --tags --always --dirty)

echo "🔧 빌드 정보:"
echo "  - Build Date: $BUILD_DATE"
echo "  - VCS Ref: $VCS_REF"
echo "  - Commit Hash: $COMMIT_HASH"
echo "  - Version: $VERSION"

# 3. Docker 이미지 빌드
echo "🏗️ Docker 이미지 빌드 중..."
docker build \
    --build-arg BUILD_DATE="$BUILD_DATE" \
    --build-arg VCS_REF="$VCS_REF" \
    --build-arg VERSION="$VERSION" \
    -t mud-engine:test \
    .

# 4. 빌드된 이미지 정보 확인
echo "📋 빌드된 이미지 정보:"
docker inspect mud-engine:test --format='{{json .Config.Labels}}' | python -m json.tool

# 5. 컨테이너 실행 테스트 (백그라운드)
echo "🚀 컨테이너 실행 테스트..."
docker run -d --name mud-engine-test -p 4001:4000 mud-engine:test

# 6. 잠시 대기 후 헬스체크
sleep 5
echo "🔍 헬스체크..."
if docker exec mud-engine-test python -c "import socket; s=socket.socket(); s.connect(('localhost', 4000)); s.close()"; then
    echo "✅ 헬스체크 성공"
else
    echo "❌ 헬스체크 실패"
fi

# 7. 컨테이너 로그 확인
echo "📜 컨테이너 로그 (최근 10줄):"
docker logs --tail 10 mud-engine-test

# 8. 정리
echo "🧹 테스트 컨테이너 정리..."
docker stop mud-engine-test
docker rm mud-engine-test

echo "✅ Docker 빌드 테스트 완료!"
echo "🏷️ 생성된 이미지: mud-engine:test"