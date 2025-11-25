#!/bin/bash
# 월드 맵 HTML 생성 스크립트

echo "=== 월드 맵 생성 시작 ==="

# 가상환경 활성화 및 스크립트 실행
source mud_engine_env/Scripts/activate && PYTHONPATH=. python scripts/export_unified_map.py

# 결과 확인
if [ -f "world_map_unified.html" ]; then
    echo ""
    echo "✅ 맵 생성 완료: world_map_unified.html"
    echo "브라우저에서 파일을 열어 확인하세요."
else
    echo ""
    echo "❌ 맵 생성 실패"
    exit 1
fi
