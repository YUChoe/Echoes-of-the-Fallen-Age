#!/bin/bash
# -*- coding: utf-8 -*-
echo """Telnet 테스트 실행 스크립트"""

# 사용법 확인
if [ $# -eq 0 ]; then
    echo "사용법: $0 <테스트_파일명>"
    echo "예시:"
    echo "  $0 telnet_test.py"
    echo "  $0 telnet_client.py"
    exit 1
fi

# 테스트 파일명
TEST_FILE="$1"

# .py 확장자가 없으면 추가
if [[ ! "$TEST_FILE" == *.py ]]; then
    TEST_FILE="${TEST_FILE}.py"
fi

# telnet 디렉토리의 파일 경로
TEST_PATH="telnet/$TEST_FILE"

# 파일 존재 여부 확인
if [ ! -f "$TEST_PATH" ]; then
    echo "❌ 테스트 파일을 찾을 수 없습니다: $TEST_PATH"
    echo ""
    echo "사용 가능한 테스트 파일들:"
    ls -1 telnet/*.py 2>/dev/null | sed 's/telnet\//  /' || echo "  (telnet 디렉토리에 테스트 파일이 없습니다)"
    exit 1
fi

echo "🚀 Telnet 테스트 실행: $TEST_FILE"
echo "============================================"

# 가상환경 활성화 및 테스트 실행
source mud_engine_env/Scripts/activate && PYTHONPATH=. python "$TEST_PATH"

# 실행 결과 확인
EXIT_CODE=$?
echo ""
echo "============================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ 테스트 완료: $TEST_FILE"
else
    echo "❌ 테스트 실패: $TEST_FILE (종료 코드: $EXIT_CODE)"
fi
