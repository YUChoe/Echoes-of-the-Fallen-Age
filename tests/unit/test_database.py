"""
데이터베이스 모듈 단위 테스트
"""

import asyncio
import os
import tempfile
from pathlib import Path

import pytest

from src.mud_engine.database import (
    DatabaseManager,
    BaseRepository,
    BaseModel,
    create_database_schema,
    verify_schema
)


class TestModel(BaseModel):
    """테스트용 모델"""

    def __init__(self, id=None, name=None, data=None, **kwargs):
        super().__init__(**kwargs)
        self.id = id
        self.name = name
        self.data = data or {}


class TestRepository(BaseRepository[TestModel]):
    """테스트용 리포지토리"""

    def get_table_name(self) -> str:
        return "test_table"

    def get_model_class(self):
        return TestModel


@pytest.fixture
async def temp_db():
    """임시 데이터베이스 픽스처"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        db_path = tmp_file.name

    try:
        db_manager = DatabaseManager(f"sqlite:///{db_path}")

        # 테스트용 테이블 생성
        await db_manager.initialize()
        connection = await db_manager.get_connection()
        await connection.execute("""
            CREATE TABLE IF NOT EXISTS test_table (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                data TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await connection.commit()

        yield db_manager

    finally:
        await db_manager.close()
        if os.path.exists(db_path):
            os.unlink(db_path)


class TestDatabaseManager:
    """DatabaseManager 테스트"""

    @pytest.mark.asyncio
    async def test_initialization(self, temp_db):
        """데이터베이스 초기화 테스트"""
        assert await temp_db.health_check()

    @pytest.mark.asyncio
    async def test_execute_query(self, temp_db):
        """쿼리 실행 테스트"""
        cursor = await temp_db.execute("SELECT 1 as test")
        result = await cursor.fetchone()
        assert result[0] == 1

    @pytest.mark.asyncio
    async def test_fetch_one(self, temp_db):
        """단일 레코드 조회 테스트"""
        result = await temp_db.fetch_one("SELECT 1 as test")
        assert result == {'test': 1}

    @pytest.mark.asyncio
    async def test_fetch_all(self, temp_db):
        """다중 레코드 조회 테스트"""
        results = await temp_db.fetch_all("SELECT 1 as test UNION SELECT 2 as test")
        assert len(results) == 2
        assert results[0]['test'] == 1
        assert results[1]['test'] == 2


class TestBaseRepository:
    """BaseRepository 테스트"""

    @pytest.mark.asyncio
    async def test_create_record(self, temp_db):
        """레코드 생성 테스트"""
        repo = TestRepository(temp_db)

        data = {
            'name': 'Test Item',
            'data': {'key': 'value'}
        }

        created = await repo.create(data)
        assert created.name == 'Test Item'
        assert created.id is not None

    @pytest.mark.asyncio
    async def test_get_by_id(self, temp_db):
        """ID로 레코드 조회 테스트"""
        repo = TestRepository(temp_db)

        # 레코드 생성
        created = await repo.create({'name': 'Test Item'})

        # 조회
        retrieved = await repo.get_by_id(created.id)
        assert retrieved is not None
        assert retrieved.name == 'Test Item'

    @pytest.mark.asyncio
    async def test_update_record(self, temp_db):
        """레코드 업데이트 테스트"""
        repo = TestRepository(temp_db)

        # 레코드 생성
        created = await repo.create({'name': 'Original Name'})

        # 업데이트
        updated = await repo.update(created.id, {'name': 'Updated Name'})
        assert updated.name == 'Updated Name'

    @pytest.mark.asyncio
    async def test_delete_record(self, temp_db):
        """레코드 삭제 테스트"""
        repo = TestRepository(temp_db)

        # 레코드 생성
        created = await repo.create({'name': 'To Delete'})

        # 삭제
        deleted = await repo.delete(created.id)
        assert deleted is True

        # 삭제 확인
        retrieved = await repo.get_by_id(created.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_find_by_conditions(self, temp_db):
        """조건 검색 테스트"""
        repo = TestRepository(temp_db)

        # 테스트 데이터 생성
        await repo.create({'name': 'Item 1'})
        await repo.create({'name': 'Item 2'})
        await repo.create({'name': 'Item 1'})  # 중복 이름

        # 조건 검색
        results = await repo.find_by(name='Item 1')
        assert len(results) == 2

        for result in results:
            assert result.name == 'Item 1'

    @pytest.mark.asyncio
    async def test_count_records(self, temp_db):
        """레코드 개수 조회 테스트"""
        repo = TestRepository(temp_db)

        # 초기 개수 확인
        initial_count = await repo.count()

        # 레코드 추가
        await repo.create({'name': 'Item 1'})
        await repo.create({'name': 'Item 2'})

        # 개수 확인
        final_count = await repo.count()
        assert final_count == initial_count + 2

    @pytest.mark.asyncio
    async def test_exists_record(self, temp_db):
        """레코드 존재 확인 테스트"""
        repo = TestRepository(temp_db)

        # 레코드 생성
        created = await repo.create({'name': 'Exists Test'})

        # 존재 확인
        exists = await repo.exists(created.id)
        assert exists is True

        # 존재하지 않는 ID 확인
        not_exists = await repo.exists('non-existent-id')
        assert not_exists is False


class TestSchema:
    """스키마 관련 테스트"""

    @pytest.mark.asyncio
    async def test_schema_creation(self):
        """스키마 생성 테스트"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
            db_path = tmp_file.name

        try:
            db_manager = DatabaseManager(f"sqlite:///{db_path}")
            await db_manager.initialize()

            # 스키마 검증
            connection = await db_manager.get_connection()
            is_valid = await verify_schema(connection)
            assert is_valid is True

        finally:
            await db_manager.close()
            if os.path.exists(db_path):
                os.unlink(db_path)


if __name__ == "__main__":
    # 간단한 테스트 실행
    async def run_basic_test():
        print("🧪 데이터베이스 기본 테스트 실행...")

        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
            db_path = tmp_file.name

        try:
            # 데이터베이스 매니저 테스트
            db_manager = DatabaseManager(f"sqlite:///{db_path}")
            await db_manager.initialize()

            print("✅ 데이터베이스 초기화 성공")

            # 헬스체크
            health = await db_manager.health_check()
            print(f"✅ 헬스체크: {'정상' if health else '비정상'}")

            # 리포지토리 테스트
            repo = TestRepository(db_manager)

            # 생성 테스트
            created = await repo.create({'name': '테스트 아이템'})
            print(f"✅ 레코드 생성: {created.id}")

            # 조회 테스트
            retrieved = await repo.get_by_id(created.id)
            print(f"✅ 레코드 조회: {retrieved.name}")

            # 업데이트 테스트
            updated = await repo.update(created.id, {'name': '업데이트된 아이템'})
            print(f"✅ 레코드 업데이트: {updated.name}")

            # 삭제 테스트
            deleted = await repo.delete(created.id)
            print(f"✅ 레코드 삭제: {'성공' if deleted else '실패'}")

            print("🎉 모든 테스트 통과!")

        finally:
            await db_manager.close()
            if os.path.exists(db_path):
                os.unlink(db_path)

    asyncio.run(run_basic_test())