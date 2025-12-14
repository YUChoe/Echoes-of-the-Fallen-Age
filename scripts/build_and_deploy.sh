#!/bin/bash
# -*- coding: utf-8 -*-
"""빌드 및 배포 스크립트"""

set -e  # 오류 발생 시 스크립트 중단

echo "🚀 MUD Engine 빌드 및 배포 시작"

# 1. 버전 정보 생성
echo "📝 버전 정보 생성 중..."
python scripts/generate_version_info.py

# 2. 타입 검사
echo "🔍 타입 검사 실행 중..."
source mud_engine_env/Scripts/activate && PYTHONPATH=. mypy src/

# 3. 테스트 실행 (있는 경우)
if [ -d "tests" ] && [ "$(ls -A tests)" ]; then
    echo "🧪 테스트 실행 중..."
    source mud_engine_env/Scripts/activate && PYTHONPATH=. pytest
fi

# 4. Docker 이미지 빌드 (선택사항)
if [ "$1" = "--docker" ]; then
    echo "🐳 Docker 이미지 빌드 중..."
    
    # 빌드 인자 준비
    BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
    VCS_REF=$(git rev-parse HEAD)
    COMMIT_HASH=$(git rev-parse --short HEAD)
    VERSION=$(git describe --tags --always --dirty)
    
    # Docker 이미지 빌드
    docker build \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$VCS_REF" \
        --build-arg VERSION="$VERSION" \
        -t mud-engine:latest \
        -t mud-engine:$COMMIT_HASH \
        .
    
    echo "✅ Docker 이미지 빌드 완료:"
    echo "  - mud-engine:latest"
    echo "  - mud-engine:$COMMIT_HASH"
    echo "  - Build Date: $BUILD_DATE"
    echo "  - VCS Ref: $VCS_REF"
    echo "  - Version: $VERSION"
fi

echo "✅ 빌드 및 배포 완료!"
echo "📋 버전 정보:"
cat src/mud_engine/version_info.json | python -m json.tool