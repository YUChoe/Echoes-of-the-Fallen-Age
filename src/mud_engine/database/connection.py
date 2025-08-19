"""
데이터베이스 연결 및 초기화 관리
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

import aiosqlite
from dotenv import load_dotenv

from .schema import create_database_schema, verify_schema

logger = logging.getLogger(__name__)


class DatabaseManager:
    """데이터베이스 연결 및 관리 클래스"""

    def __init__(self, database_url: Optional[str] = None):
        """
        DatabaseManager 초기화

        Args:
            database_url: 데이터베이스 URL (기본값: 환경변수에서 로드)
        """
        load_dotenv()

        if database_url:
            self.database_url = database_url
        else:
            self.database_url = os.getenv("DATABASE_URL", "sqlite:///data/mud_engine.db")

        # SQLite URL에서 파일 경로 추출
        if self.database_url.startswith("sqlite:///"):
            self.db_path = self.database_url[10:]  # "sqlite:///" 제거
        else:
            self.db_path = self.database_url

        self._connection: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()

        logger.info(f"DatabaseManager 초기화: {self.db_path}")

    async def initialize(self) -> None:
        """
        데이터베이스 초기화
        - 디렉토리 생성
        - 연결 설정
        - 스키마 생성
        """
        async with self._lock:
            try:
                # 데이터베이스 디렉토리 생성
                db_dir = Path(self.db_path).parent
                db_dir.mkdir(parents=True, exist_ok=True)

                # 데이터베이스 연결
                await self._connect()

                # 스키마 생성
                await create_database_schema(self._connection)

                # 스키마 검증
                if not await verify_schema(self._connection):
                    raise RuntimeError("데이터베이스 스키마 검증 실패")

                logger.info("데이터베이스 초기화 완료")

            except Exception as e:
                logger.error(f"데이터베이스 초기화 실패: {e}")
                await self.close()
                raise

    async def _connect(self) -> None:
        """데이터베이스 연결 생성"""
        if self._connection is None:
            self._connection = await aiosqlite.connect(
                self.db_path,
                timeout=30.0,
                isolation_level=None  # autocommit 모드
            )

            # SQLite 설정 최적화
            await self._connection.execute("PRAGMA foreign_keys = ON")
            await self._connection.execute("PRAGMA journal_mode = WAL")
            await self._connection.execute("PRAGMA synchronous = NORMAL")
            await self._connection.execute("PRAGMA cache_size = -64000")  # 64MB 캐시
            await self._connection.execute("PRAGMA temp_store = MEMORY")

            logger.info("데이터베이스 연결 생성 완료")

    async def get_connection(self) -> aiosqlite.Connection:
        """
        데이터베이스 연결 반환

        Returns:
            aiosqlite.Connection: 데이터베이스 연결 객체
        """
        if self._connection is None:
            await self.initialize()

        return self._connection

    async def execute(self, query: str, parameters: tuple = ()) -> aiosqlite.Cursor:
        """
        SQL 쿼리 실행

        Args:
            query: SQL 쿼리
            parameters: 쿼리 매개변수

        Returns:
            aiosqlite.Cursor: 쿼리 결과 커서
        """
        connection = await self.get_connection()
        return await connection.execute(query, parameters)

    async def execute_many(self, query: str, parameters_list: list) -> aiosqlite.Cursor:
        """
        여러 SQL 쿼리 일괄 실행

        Args:
            query: SQL 쿼리
            parameters_list: 쿼리 매개변수 리스트

        Returns:
            aiosqlite.Cursor: 쿼리 결과 커서
        """
        connection = await self.get_connection()
        return await connection.executemany(query, parameters_list)

    async def fetch_one(self, query: str, parameters: tuple = ()) -> Optional[dict]:
        """
        단일 레코드 조회

        Args:
            query: SQL 쿼리
            parameters: 쿼리 매개변수

        Returns:
            Optional[dict]: 조회 결과 (딕셔너리 형태)
        """
        cursor = await self.execute(query, parameters)
        row = await cursor.fetchone()

        if row is None:
            return None

        # 컬럼명과 함께 딕셔너리로 변환
        columns = [description[0] for description in cursor.description]
        return dict(zip(columns, row))

    async def fetch_all(self, query: str, parameters: tuple = ()) -> list[dict]:
        """
        여러 레코드 조회

        Args:
            query: SQL 쿼리
            parameters: 쿼리 매개변수

        Returns:
            list[dict]: 조회 결과 리스트 (딕셔너리 형태)
        """
        cursor = await self.execute(query, parameters)
        rows = await cursor.fetchall()

        if not rows:
            return []

        # 컬럼명과 함께 딕셔너리로 변환
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row)) for row in rows]

    async def commit(self) -> None:
        """트랜잭션 커밋"""
        if self._connection:
            await self._connection.commit()

    async def rollback(self) -> None:
        """트랜잭션 롤백"""
        if self._connection:
            await self._connection.rollback()

    async def close(self) -> None:
        """데이터베이스 연결 종료"""
        async with self._lock:
            if self._connection:
                try:
                    await self._connection.close()
                    logger.info("데이터베이스 연결 종료 완료")
                except Exception as e:
                    logger.error(f"데이터베이스 연결 종료 중 오류: {e}")
                finally:
                    self._connection = None

    async def health_check(self) -> bool:
        """
        데이터베이스 연결 상태 확인

        Returns:
            bool: 연결 상태 (True: 정상, False: 비정상)
        """
        try:
            cursor = await self.execute("SELECT 1")
            result = await cursor.fetchone()
            return result is not None
        except Exception as e:
            logger.error(f"데이터베이스 헬스체크 실패: {e}")
            return False

    async def get_table_info(self, table_name: str) -> list[dict]:
        """
        테이블 정보 조회

        Args:
            table_name: 테이블명

        Returns:
            list[dict]: 테이블 컬럼 정보
        """
        return await self.fetch_all(f"PRAGMA table_info({table_name})")

    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        await self.close()


# 전역 데이터베이스 매니저 인스턴스
_db_manager: Optional[DatabaseManager] = None


async def get_database_manager() -> DatabaseManager:
    """
    전역 데이터베이스 매니저 인스턴스 반환

    Returns:
        DatabaseManager: 데이터베이스 매니저 인스턴스
    """
    global _db_manager

    if _db_manager is None:
        _db_manager = DatabaseManager()
        await _db_manager.initialize()

    return _db_manager


async def close_database_manager() -> None:
    """전역 데이터베이스 매니저 종료"""
    global _db_manager

    if _db_manager:
        try:
            logger.info("전역 데이터베이스 매니저 종료 시작")
            await _db_manager.close()
            logger.info("전역 데이터베이스 매니저 종료 완료")
        except Exception as e:
            logger.error(f"전역 데이터베이스 매니저 종료 실패: {e}")
        finally:
            _db_manager = None