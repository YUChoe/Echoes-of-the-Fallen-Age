#!/bin/bash
# -*- coding: utf-8 -*-
"""Scripts 디렉토리의 Python 스크립트 실행 도구"""

# 사용법 확인
if [ $# -eq 0 ]; then
    echo "사용법: $0 <스크립트_파일명>"
    echo "예시:"
    echo "  $0 check_player_location.py"
    echo "  $0 setup_tutorial.py"
    echo ""
    echo "사용 가능한 스크립트 파일들:"
    ls -1 scripts/*.py 2>/dev/null | sed 's/scripts\//  /' || echo "  (scripts 디렉토리에 Python 파일이 없습니다)"
    exit 1
fi

# 스크립트 파일명
SCRIPT_FILE="$1"

# .py 확장자가 없으면 추가
if [[ ! "$SCRIPT_FILE" == *.py ]]; then
    SCRIPT_FILE="${SCRIPT_FILE}.py"
fi

# scripts 디렉토리의 파일 경로
SCRIPT_PATH="scripts/$SCRIPT_FILE"

# 파일 존재 여부 확인
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "❌ 스크립트 파일을 찾을 수 없습니다: $SCRIPT_PATH"
    echo ""
    echo "사용 가능한 스크립트 파일들:"
    ls -1 scripts/*.py 2>/dev/null | sed 's/scripts\//  /' || echo "  (scripts 디렉토리에 Python 파일이 없습니다)"
    exit 1
fi

echo "🚀 스크립트 실행: $SCRIPT_FILE"
echo "============================================"

# 가상환경 활성화 및 스크립트 실행
source mud_engine_env/Scripts/activate && PYTHONPATH=. python "$SCRIPT_PATH"

# 실행 결과 확인
EXIT_CODE=$?
echo ""
echo "============================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ 스크립트 완료: $SCRIPT_FILE"
else
    echo "❌ 스크립트 실패: $SCRIPT_FILE (종료 코드: $EXIT_CODE)"
fi