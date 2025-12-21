#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""통합 월드 맵을 HTML로 추출하는 스크립트"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.mud_engine.database.connection import DatabaseManager
from src.mud_engine.utils.map_exporter import MapExporter


async def main():
    """메인 실행 함수"""
    print("=== 통합 월드 맵 HTML 추출 시작 ===\n")

    db_manager = DatabaseManager()
    await db_manager.initialize()

    try:
        # MapExporter 인스턴스 생성
        map_exporter = MapExporter(db_manager)

        # HTML 파일로 내보내기
        output_file = "world_map_unified.html"
        success = await map_exporter.export_to_file(output_file)

        if success:
            print(f"✅ HTML 파일 생성 완료: {output_file}")
            print(f"\n브라우저에서 {output_file}을 열어 통합 지도를 확인하세요.")
            print("방을 클릭하면 상세 정보(enter 연결 포함)를 볼 수 있습니다.")
        else:
            print("❌ HTML 파일 생성 실패")
            return 1

    finally:
        await db_manager.close()

    return 0


if __name__ == "__main__":
    asyncio.run(main())
