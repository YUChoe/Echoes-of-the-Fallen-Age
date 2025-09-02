"""
기본 CRUD 연산을 위한 베이스 리포지토리 클래스
"""

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, TypeVar, Generic, Union, cast
from uuid import uuid4

from .connection import DatabaseManager, get_database_manager

logger = logging.getLogger(__name__)

# 제네릭 타입 변수
T = TypeVar('T', bound='BaseModel')


class BaseModel:
    """기본 모델 클래스"""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def to_dict(self) -> Dict[str, Any]:
        """모델을 딕셔너리로 변환"""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, (list, dict)):
                result[key] = json.dumps(value, ensure_ascii=False)
            else:
                result[key] = value
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseModel':
        """딕셔너리에서 모델 생성"""
        return cls(**data)


class BaseRepository(Generic[T], ABC):
    """기본 리포지토리 클래스"""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        BaseRepository 초기화

        Args:
            db_manager: 데이터베이스 매니저 (기본값: 전역 인스턴스 사용)
        """
        self._db_manager = db_manager
        self._table_name = self.get_table_name()
        self._model_class = self.get_model_class()

    @abstractmethod
    def get_table_name(self) -> str:
        """테이블명 반환"""
        pass

    @abstractmethod
    def get_model_class(self) -> Type[T]:
        """모델 클래스 반환"""
        pass

    async def get_db_manager(self) -> DatabaseManager:
        """데이터베이스 매니저 반환"""
        if self._db_manager is None:
            self._db_manager = await get_database_manager()
        return self._db_manager

    def _generate_id(self) -> str:
        """새로운 ID 생성"""
        return str(uuid4())

    def _prepare_data_for_insert(self, data: Union[Dict[str, Any], BaseModel]) -> Dict[str, Any]:
        """삽입용 데이터 준비"""
        # BaseModel 인스턴스인 경우 딕셔너리로 변환
        if hasattr(data, 'to_dict'):
            prepared_data = data.to_dict()
        else:
            prepared_data = data.copy()

        # ID가 없으면 생성
        if 'id' not in prepared_data or not prepared_data['id']:
            prepared_data['id'] = self._generate_id()

        # 생성 시간 설정
        if 'created_at' not in prepared_data:
            prepared_data['created_at'] = datetime.now().isoformat()

        # JSON 필드 처리
        for key, value in prepared_data.items():
            if isinstance(value, (list, dict)):
                prepared_data[key] = json.dumps(value, ensure_ascii=False)

        return prepared_data

    def _prepare_data_for_update(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """업데이트용 데이터 준비"""
        prepared_data = data.copy()

        # 업데이트 시간 설정 (일반적으로 updated_at 컬럼이 있다고 가정)
        # 실제 테이블 컬럼 확인은 update 메서드에서 수행
        prepared_data['updated_at'] = datetime.now().isoformat()

        # JSON 필드 처리
        for key, value in prepared_data.items():
            if isinstance(value, (list, dict)):
                prepared_data[key] = json.dumps(value, ensure_ascii=False)

        return prepared_data

    async def _get_table_columns(self) -> List[str]:
        """테이블 컬럼 목록 반환"""
        db_manager = await self.get_db_manager()
        table_info = await db_manager.get_table_info(self._table_name)
        return [col['name'] for col in table_info]

    async def create(self, data: Dict[str, Any]) -> T:
        """
        새 레코드 생성

        Args:
            data: 생성할 데이터

        Returns:
            T: 생성된 모델 인스턴스
        """
        try:
            db_manager = await self.get_db_manager()
            prepared_data = self._prepare_data_for_insert(data)

            # 컬럼과 값 분리
            columns = list(prepared_data.keys())
            placeholders = ', '.join(['?' for _ in columns])
            values = list(prepared_data.values())

            # INSERT 쿼리 실행
            query = f"""
                INSERT INTO {self._table_name} ({', '.join(columns)})
                VALUES ({placeholders})
            """

            await db_manager.execute(query, tuple(values))
            await db_manager.commit()

            # 생성된 레코드 반환
            created_record = await self.get_by_id(prepared_data['id'])
            logger.info(f"{self._table_name}에 새 레코드 생성: {prepared_data['id']}")

            return created_record

        except Exception as e:
            logger.error(f"{self._table_name} 레코드 생성 실패: {e}")
            await db_manager.rollback()
            raise

    async def get_by_id(self, record_id: str) -> Optional[T]:
        """
        ID로 레코드 조회

        Args:
            record_id: 레코드 ID

        Returns:
            Optional[T]: 조회된 모델 인스턴스
        """
        try:
            db_manager = await self.get_db_manager()
            query = f"SELECT * FROM {self._table_name} WHERE id = ?"

            result = await db_manager.fetch_one(query, (record_id,))

            if result is None:
                return None

            return cast(T, self._model_class.from_dict(result))

        except Exception as e:
            logger.error(f"{self._table_name} 레코드 조회 실패 (ID: {record_id}): {e}")
            raise

    async def get_all(self, limit: Optional[int] = None, offset: int = 0) -> List[T]:
        """
        모든 레코드 조회

        Args:
            limit: 조회 제한 수
            offset: 조회 시작 위치

        Returns:
            List[T]: 조회된 모델 인스턴스 리스트
        """
        try:
            db_manager = await self.get_db_manager()
            query = f"SELECT * FROM {self._table_name}"

            if limit is not None:
                query += f" LIMIT {limit} OFFSET {offset}"

            results = await db_manager.fetch_all(query)

            return [cast(T, self._model_class.from_dict(result)) for result in results]

        except Exception as e:
            logger.error(f"{self._table_name} 전체 레코드 조회 실패: {e}")
            raise

    async def update(self, record_id: str, data: Dict[str, Any]) -> Optional[T]:
        """
        레코드 업데이트

        Args:
            record_id: 레코드 ID
            data: 업데이트할 데이터

        Returns:
            Optional[T]: 업데이트된 모델 인스턴스
        """
        try:
            db_manager = await self.get_db_manager()

            # 기존 레코드 존재 확인
            existing_record = await self.get_by_id(record_id)
            if existing_record is None:
                logger.warning(f"{self._table_name} 레코드를 찾을 수 없음 (ID: {record_id})")
                return None

            prepared_data = self._prepare_data_for_update(data)

            # 테이블 컬럼 확인 후 updated_at 컬럼이 없으면 제거
            table_columns = await self._get_table_columns()
            if 'updated_at' not in table_columns and 'updated_at' in prepared_data:
                del prepared_data['updated_at']

            # SET 절 생성
            set_clauses = [f"{key} = ?" for key in prepared_data.keys()]
            values = list(prepared_data.values()) + [record_id]

            # UPDATE 쿼리 실행
            query = f"""
                UPDATE {self._table_name}
                SET {', '.join(set_clauses)}
                WHERE id = ?
            """

            await db_manager.execute(query, tuple(values))
            await db_manager.commit()

            # 업데이트된 레코드 반환
            updated_record = await self.get_by_id(record_id)
            logger.info(f"{self._table_name} 레코드 업데이트: {record_id}")

            return updated_record

        except Exception as e:
            logger.error(f"{self._table_name} 레코드 업데이트 실패 (ID: {record_id}): {e}")
            await db_manager.rollback()
            raise

    async def delete(self, record_id: str) -> bool:
        """
        레코드 삭제

        Args:
            record_id: 레코드 ID

        Returns:
            bool: 삭제 성공 여부
        """
        try:
            db_manager = await self.get_db_manager()

            # 기존 레코드 존재 확인
            existing_record = await self.get_by_id(record_id)
            if existing_record is None:
                logger.warning(f"{self._table_name} 레코드를 찾을 수 없음 (ID: {record_id})")
                return False

            # DELETE 쿼리 실행
            query = f"DELETE FROM {self._table_name} WHERE id = ?"
            cursor = await db_manager.execute(query, (record_id,))
            await db_manager.commit()

            deleted_count = cursor.rowcount
            if deleted_count > 0:
                logger.info(f"{self._table_name} 레코드 삭제: {record_id}")
                return True
            else:
                logger.warning(f"{self._table_name} 레코드 삭제 실패: {record_id}")
                return False

        except Exception as e:
            logger.error(f"{self._table_name} 레코드 삭제 실패 (ID: {record_id}): {e}")
            await db_manager.rollback()
            raise

    async def find_by(self, **conditions) -> List[T]:
        """
        조건으로 레코드 검색

        Args:
            **conditions: 검색 조건

        Returns:
            List[T]: 검색된 모델 인스턴스 리스트
        """
        try:
            db_manager = await self.get_db_manager()

            if not conditions:
                return await self.get_all()

            # WHERE 절 생성
            where_clauses = [f"{key} = ?" for key in conditions.keys()]
            values = list(conditions.values())

            query = f"""
                SELECT * FROM {self._table_name}
                WHERE {' AND '.join(where_clauses)}
            """

            results = await db_manager.fetch_all(query, tuple(values))

            return [cast(T, self._model_class.from_dict(result)) for result in results]

        except Exception as e:
            logger.error(f"{self._table_name} 조건 검색 실패: {e}")
            raise

    async def count(self, **conditions) -> int:
        """
        레코드 개수 조회

        Args:
            **conditions: 검색 조건

        Returns:
            int: 레코드 개수
        """
        try:
            db_manager = await self.get_db_manager()

            if conditions:
                where_clauses = [f"{key} = ?" for key in conditions.keys()]
                values = list(conditions.values())
                query = f"""
                    SELECT COUNT(*) as count FROM {self._table_name}
                    WHERE {' AND '.join(where_clauses)}
                """
                result = await db_manager.fetch_one(query, tuple(values))
            else:
                query = f"SELECT COUNT(*) as count FROM {self._table_name}"
                result = await db_manager.fetch_one(query)

            return result['count'] if result else 0

        except Exception as e:
            logger.error(f"{self._table_name} 레코드 개수 조회 실패: {e}")
            raise

    async def exists(self, record_id: str) -> bool:
        """
        레코드 존재 여부 확인

        Args:
            record_id: 레코드 ID

        Returns:
            bool: 존재 여부
        """
        try:
            db_manager = await self.get_db_manager()
            query = f"SELECT 1 FROM {self._table_name} WHERE id = ? LIMIT 1"
            result = await db_manager.fetch_one(query, (record_id,))
            return result is not None

        except Exception as e:
            logger.error(f"{self._table_name} 레코드 존재 확인 실패 (ID: {record_id}): {e}")
            raise