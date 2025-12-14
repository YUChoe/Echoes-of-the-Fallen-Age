#!/bin/bash
# -*- coding: utf-8 -*-
"""개발 환경 설정 스크립트"""

set -e

echo "🛠️ 개발 환경 설정 시작"

# 1. 가상환경 활성화 확인
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️ 가상환경이 활성화되지 않았습니다."
    echo "다음 명령어로 가상환경을 활성화하세요:"
    echo "source mud_engine_env/Scripts/activate"
    exit 1
fi

echo "✅ 가상환경 활성화됨: $VIRTUAL_ENV"

# 2. 버전 정보 생성
echo "📝 버전 정보 생성 중..."
python scripts/generate_version_info.py

# 3. 타입 검사
echo "🔍 타입 검사 실행 중..."
PYTHONPATH=. mypy src/

# 4. 서버 상태 확인
echo "🔍 서버 프로세스 확인..."
if pgrep -f "python -m src.mud_engine.main" > /dev/null; then
    echo "✅ MUD Engine 서버가 실행 중입니다"
    echo "📊 프로세스 정보:"
    ps aux | grep "python -m src.mud_engine.main" | grep -v grep
else
    echo "⚠️ MUD Engine 서버가 실행되지 않았습니다"
    echo "다음 명령어로 서버를 시작할 수 있습니다:"
    echo "PYTHONPATH=. python -m src.mud_engine.main"
fi

# 5. 버전 정보 표시
echo "📋 현재 버전 정보:"
if [ -f "src/mud_engine/version_info.json" ]; then
    cat src/mud_engine/version_info.json | python -m json.tool
else
    echo "❌ 버전 정보 파일이 없습니다"
fi

echo "✅ 개발 환경 설정 완료!"