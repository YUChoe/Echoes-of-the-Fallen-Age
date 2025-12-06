# -*- coding: utf-8 -*-
"""
SQLite 유틸리티 함수들
"""

import sqlite3
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class SQLiteUtils:
    """SQLite 데이터베이스 유틸리티 클래스"""
    
    def __init__(self, db_path: str):
        """
        SQLite 유틸리티 초기화
        
        Args:
            db_path: 데이터베이스 파일 경로
        """
        self.db_path = db_path
    
    def execute_query(
        self,
        query: str,
        params: Optional[Tuple] = None,
        fetch_one: bool = False,
        fetch_all: bool = True
    ) -> Optional[List[Tuple] | Tuple]:  # type: ignore[return]
        """
        SQL 쿼리 실행
        
        Args:
            query: SQL 쿼리 문자열
            params: 쿼리 파라미터 (선택)
            fetch_one: 단일 결과 반환 여부
            fetch_all: 모든 결과 반환 여부
        
        Returns:
            쿼리 결과 (fetch_one=True면 Tuple, fetch_all=True면 List[Tuple])
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if fetch_one:
                return cursor.fetchone()
            elif fetch_all:
                return cursor.fetchall()
            else:
                return None
        except Exception as e:
            logger.error(f"쿼리 실행 오류: {e}")
            logger.error(f"쿼리: {query}")
            logger.error(f"파라미터: {params}")
            raise
        finally:
            if conn:
                conn.close()
    
    def execute_update(
        self,
        query: str,
        params: Optional[Tuple] = None
    ) -> int:
        """
        UPDATE/INSERT/DELETE 쿼리 실행
        
        Args:
            query: SQL 쿼리 문자열
            params: 쿼리 파라미터 (선택)
        
        Returns:
            영향받은 행 수
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            conn.commit()
            return cursor.rowcount
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"업데이트 쿼리 실행 오류: {e}")
            logger.error(f"쿼리: {query}")
            logger.error(f"파라미터: {params}")
            raise
        finally:
            if conn:
                conn.close()

    
    def get_table_info(self, table_name: str) -> List[Tuple]:
        """
        테이블 스키마 정보 조회
        
        Args:
            table_name: 테이블 이름
        
        Returns:
            테이블 컬럼 정보 리스트
        """
        query = f"PRAGMA table_info({table_name})"
        result = self.execute_query(query, fetch_all=True)
        if isinstance(result, list):
            return result
        return []
    
    def get_all_tables(self) -> List[str]:
        """
        데이터베이스의 모든 테이블 목록 조회
        
        Returns:
            테이블 이름 리스트
        """
        query = "SELECT name FROM sqlite_master WHERE type='table'"
        results = self.execute_query(query, fetch_all=True)
        return [row[0] for row in results] if results else []
    
    def select_by_id(
        self,
        table_name: str,
        id_value: str,
        id_column: str = 'id'
    ) -> Optional[Tuple]:
        """
        ID로 레코드 조회
        
        Args:
            table_name: 테이블 이름
            id_value: ID 값
            id_column: ID 컬럼 이름 (기본: 'id')
        
        Returns:
            레코드 (없으면 None)
        """
        query = f"SELECT * FROM {table_name} WHERE {id_column} = ?"
        result = self.execute_query(query, params=(id_value,), fetch_one=True)
        if isinstance(result, tuple):
            return result
        return None
    
    def select_by_condition(
        self,
        table_name: str,
        condition: str,
        params: Optional[Tuple] = None
    ) -> List[Tuple]:
        """
        조건으로 레코드 조회
        
        Args:
            table_name: 테이블 이름
            condition: WHERE 절 조건
            params: 쿼리 파라미터
        
        Returns:
            레코드 리스트
        """
        query = f"SELECT * FROM {table_name} WHERE {condition}"
        result = self.execute_query(query, params=params, fetch_all=True)
        if isinstance(result, list):
            return result
        return []
    
    def update_by_id(
        self,
        table_name: str,
        id_value: str,
        updates: Dict[str, Any],
        id_column: str = 'id'
    ) -> int:
        """
        ID로 레코드 업데이트
        
        Args:
            table_name: 테이블 이름
            id_value: ID 값
            updates: 업데이트할 컬럼과 값 딕셔너리
            id_column: ID 컬럼 이름 (기본: 'id')
        
        Returns:
            영향받은 행 수
        """
        set_clause = ", ".join([f"{col} = ?" for col in updates.keys()])
        query = f"UPDATE {table_name} SET {set_clause} WHERE {id_column} = ?"
        params = tuple(updates.values()) + (id_value,)
        return self.execute_update(query, params=params)
    
    def delete_by_id(
        self,
        table_name: str,
        id_value: str,
        id_column: str = 'id'
    ) -> int:
        """
        ID로 레코드 삭제
        
        Args:
            table_name: 테이블 이름
            id_value: ID 값
            id_column: ID 컬럼 이름 (기본: 'id')
        
        Returns:
            영향받은 행 수
        """
        query = f"DELETE FROM {table_name} WHERE {id_column} = ?"
        return self.execute_update(query, params=(id_value,))
    
    def count_records(
        self,
        table_name: str,
        condition: Optional[str] = None,
        params: Optional[Tuple] = None
    ) -> int:
        """
        레코드 개수 조회
        
        Args:
            table_name: 테이블 이름
            condition: WHERE 절 조건 (선택)
            params: 쿼리 파라미터 (선택)
        
        Returns:
            레코드 개수
        """
        if condition:
            query = f"SELECT COUNT(*) FROM {table_name} WHERE {condition}"
        else:
            query = f"SELECT COUNT(*) FROM {table_name}"
        
        result = self.execute_query(query, params=params, fetch_one=True)
        if isinstance(result, tuple) and len(result) > 0:
            return int(result[0])
        return 0


# 전역 유틸리티 인스턴스 생성 함수
def get_sqlite_utils(db_path: Optional[str] = None) -> SQLiteUtils:
    """
    SQLite 유틸리티 인스턴스 생성
    
    Args:
        db_path: 데이터베이스 파일 경로 (None이면 기본 경로 사용)
    
    Returns:
        SQLiteUtils 인스턴스
    """
    if db_path is None:
        # 기본 데이터베이스 경로
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent.parent
        db_path = str(project_root / "data" / "mud_engine.db")
    
    return SQLiteUtils(db_path)
