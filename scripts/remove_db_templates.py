#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""데이터베이스에서 템플릿 몬스터들을 제거하는 스크립트"""

import sqlite3
import logging
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def remove_template_monsters():
    """데이터베이스에서 템플릿 몬스터들을 제거합니다."""
    db_path = project_root / "data" / "mud_engine.db"
    
    if not db_path.exists():
        logger.error(f"데이터베이스 파일을 찾을 수 없습니다: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 템플릿 몬스터들 조회
        cursor.execute("SELECT id, name_ko FROM monsters WHERE id LIKE 'template_%'")
        templates = cursor.fetchall()
        
        if not templates:
            logger.info("제거할 템플릿 몬스터가 없습니다.")
            conn.close()
            return True
        
        logger.info(f"제거할 템플릿 몬스터 {len(templates)}개:")
        for template_id, name_ko in templates:
            logger.info(f"  - {template_id}: {name_ko}")
        
        # 사용자 확인
        response = input("\n이 템플릿들을 데이터베이스에서 제거하시겠습니까? (y/N): ")
        if response.lower() != 'y':
            logger.info("작업이 취소되었습니다.")
            conn.close()
            return False
        
        # 템플릿 몬스터들 제거
        cursor.execute("DELETE FROM monsters WHERE id LIKE 'template_%'")
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ {deleted_count}개의 템플릿 몬스터가 제거되었습니다.")
        logger.info("이제 몬스터 템플릿은 configs/monsters/ 디렉토리의 파일에서만 관리됩니다.")
        
        return True
        
    except Exception as e:
        logger.error(f"템플릿 제거 중 오류 발생: {e}")
        return False


def main():
    """메인 함수"""
    logger.info("데이터베이스 템플릿 제거 스크립트 시작")
    
    success = remove_template_monsters()
    
    if success:
        logger.info("템플릿 제거 완료")
    else:
        logger.error("템플릿 제거 실패")
        sys.exit(1)


if __name__ == "__main__":
    main()