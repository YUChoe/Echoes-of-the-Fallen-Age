"""
데이터베이스 스키마 정의 및 생성 스크립트
"""

import logging
from typing import List

logger = logging.getLogger(__name__)

# 데이터베이스 스키마 정의
DATABASE_SCHEMA: List[str] = [
    """
    -- 플레이어 테이블
    CREATE TABLE IF NOT EXISTS players (
        id TEXT PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        email TEXT,
        preferred_locale TEXT DEFAULT 'en',
        is_admin BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP,

        -- 능력치 시스템
        stat_strength INTEGER DEFAULT 1,
        stat_dexterity INTEGER DEFAULT 1,
        stat_intelligence INTEGER DEFAULT 1,
        stat_wisdom INTEGER DEFAULT 1,
        stat_constitution INTEGER DEFAULT 1,
        stat_charisma INTEGER DEFAULT 1,
        stat_equipment_bonuses TEXT DEFAULT '{}',
        stat_temporary_effects TEXT DEFAULT '{}',
        stat_current TEXT DEFAULT '{}',

        -- 퀘스트 시스템
        completed_quests TEXT DEFAULT '[]', -- JSON 형태로 저장 (완료된 퀘스트 ID 목록)
        quest_progress TEXT DEFAULT '{}' -- JSON 형태로 저장 (진행 중인 퀘스트 상태)
    );
    """,

    """
    -- 방 테이블
    CREATE TABLE IF NOT EXISTS rooms (
        id TEXT PRIMARY KEY,
        description_en TEXT,
        description_ko TEXT,
        exits TEXT DEFAULT '{}', -- JSON 형태로 저장 (방향: 목적지_방_ID)
        x INTEGER, -- X 좌표
        y INTEGER, -- Y 좌표
        blocked_exits TEXT DEFAULT '[]', -- 막힌 출구 방향 (JSON 배열, 예: ["north", "west"])
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,

    """
    -- 게임 객체 테이블
    CREATE TABLE IF NOT EXISTS game_objects (
        id TEXT PRIMARY KEY,
        name_en TEXT NOT NULL,
        name_ko TEXT NOT NULL,
        description_en TEXT,
        description_ko TEXT,
        object_type TEXT NOT NULL, -- 'item', 'npc', 'furniture' 등
        location_type TEXT NOT NULL, -- 'room', 'inventory'
        location_id TEXT, -- room_id 또는 character_id
        properties TEXT DEFAULT '{}', -- JSON 형태로 저장
        weight REAL DEFAULT 1.0, -- 무게 (kg 단위)
        category TEXT DEFAULT 'misc', -- 카테고리: weapon, armor, consumable, misc
        equipment_slot TEXT, -- 장비 슬롯: weapon, armor, accessory
        is_equipped BOOLEAN DEFAULT FALSE, -- 착용 여부
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,

    """
    -- 몬스터 테이블
    CREATE TABLE IF NOT EXISTS monsters (
        id TEXT PRIMARY KEY,
        name_en TEXT NOT NULL,
        name_ko TEXT NOT NULL,
        description_en TEXT,
        description_ko TEXT,
        monster_type TEXT DEFAULT 'passive', -- 'aggressive', 'passive', 'neutral'
        behavior TEXT DEFAULT 'stationary', -- 'stationary', 'roaming', 'territorial'
        stats TEXT DEFAULT '{}', -- JSON 형태로 저장 (MonsterStats)
        drop_items TEXT DEFAULT '[]', -- JSON 형태로 저장 (DropItem 목록)
        x INTEGER, -- X 좌표
        y INTEGER, -- Y 좌표
        respawn_time INTEGER DEFAULT 300, -- 리스폰 시간 (초)
        last_death_time TIMESTAMP, -- 마지막 사망 시간
        is_alive BOOLEAN DEFAULT TRUE, -- 생존 상태
        aggro_range INTEGER DEFAULT 1, -- 어그로 범위
        roaming_range INTEGER DEFAULT 2, -- 로밍 범위
        properties TEXT DEFAULT '{}', -- JSON 형태로 저장
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,

    """
    -- 인덱스 생성
    CREATE INDEX IF NOT EXISTS idx_players_username ON players(username);
    CREATE INDEX IF NOT EXISTS idx_game_objects_location ON game_objects(location_type, location_id);
    CREATE INDEX IF NOT EXISTS idx_monsters_coordinates ON monsters(x, y);
    CREATE INDEX IF NOT EXISTS idx_monsters_type ON monsters(monster_type);
    CREATE INDEX IF NOT EXISTS idx_monsters_alive ON monsters(is_alive);
    """,

    """
    -- 아이템 가격 테이블
    CREATE TABLE IF NOT EXISTS item_prices (
        template_id TEXT PRIMARY KEY,
        buy_price INTEGER DEFAULT 0,
        sell_price INTEGER DEFAULT 0
    );
    """
]

# 초기 데이터
INITIAL_DATA: List[str] = [
    # 기본 방 생성은 제거됨 - UUID 기반 시스템 사용
    # 기본 번역 텍스트도 제거됨 - 별도 시스템 사용
]


async def create_database_schema(db_connection) -> None:
    """
    데이터베이스 스키마를 생성합니다.

    Args:
        db_connection: aiosqlite 데이터베이스 연결 객체
    """
    logger.info("데이터베이스 스키마 생성 시작")

    try:
        # 스키마 생성
        for schema_sql in DATABASE_SCHEMA:
            await db_connection.executescript(schema_sql)

        # 초기 데이터 삽입
        for data_sql in INITIAL_DATA:
            await db_connection.executescript(data_sql)

        await db_connection.commit()
        logger.info("데이터베이스 스키마 생성 완료")

    except Exception as e:
        logger.error(f"데이터베이스 스키마 생성 실패: {e}")
        await db_connection.rollback()
        raise


async def migrate_database(db_manager) -> None:
    """
    데이터베이스 마이그레이션을 수행합니다.

    Args:
        db_manager: DatabaseManager 인스턴스
    """
    logger.info("데이터베이스 마이그레이션 시작")

    try:
        # 현재 테이블 구조 확인
        cursor = await db_manager.execute("PRAGMA table_info(players)")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]

        # is_admin 컬럼 추가
        if 'is_admin' not in column_names:
            logger.info("is_admin 컬럼 추가 중...")
            await db_manager.execute(
                "ALTER TABLE players ADD COLUMN is_admin BOOLEAN DEFAULT FALSE"
            )
            await db_manager.commit()
            logger.info("is_admin 컬럼 추가 완료")

        # 능력치 시스템 컬럼들 추가
        stat_columns = [
            ('stat_strength', 'INTEGER DEFAULT 1'),
            ('stat_dexterity', 'INTEGER DEFAULT 1'),
            ('stat_intelligence', 'INTEGER DEFAULT 1'),
            ('stat_wisdom', 'INTEGER DEFAULT 1'),
            ('stat_constitution', 'INTEGER DEFAULT 1'),
            ('stat_charisma', 'INTEGER DEFAULT 1'),
            ('stat_equipment_bonuses', "TEXT DEFAULT '{}'"),
            ('stat_temporary_effects', "TEXT DEFAULT '{}'"),
            ('stat_current', "TEXT DEFAULT '{}'"),
        ]

        for column_name, column_def in stat_columns:
            if column_name not in column_names:
                logger.info(f"{column_name} 컬럼 추가 중...")
                await db_manager.execute(
                    f"ALTER TABLE players ADD COLUMN {column_name} {column_def}"
                )
                await db_manager.commit()
                logger.info(f"{column_name} 컬럼 추가 완료")

        # game_objects 테이블에 인벤토리 시스템 컬럼들 추가
        cursor = await db_manager.execute("PRAGMA table_info(game_objects)")
        game_objects_columns = await cursor.fetchall()
        game_objects_column_names = [col[1] for col in game_objects_columns]

        inventory_columns = [
            ('weight', 'REAL DEFAULT 1.0'),
            ('category', "TEXT DEFAULT 'misc'"),
            ('equipment_slot', 'TEXT'),
            ('is_equipped', 'BOOLEAN DEFAULT FALSE')
        ]

        for column_name, column_def in inventory_columns:
            if column_name not in game_objects_column_names:
                logger.info(f"game_objects 테이블에 {column_name} 컬럼 추가 중...")
                await db_manager.execute(
                    f"ALTER TABLE game_objects ADD COLUMN {column_name} {column_def}"
                )
                await db_manager.commit()
                logger.info(f"{column_name} 컬럼 추가 완료")

        # Monster 테이블 생성 확인 및 생성
        cursor = await db_manager.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='monsters'")
        monster_table_exists = await cursor.fetchone()

        if not monster_table_exists:
            logger.info("Monster 테이블 생성 중...")
            monster_table_sql = """
            CREATE TABLE IF NOT EXISTS monsters (
                id TEXT PRIMARY KEY,
                name_en TEXT NOT NULL,
                name_ko TEXT NOT NULL,
                description_en TEXT,
                description_ko TEXT,
                monster_type TEXT DEFAULT 'passive',
                behavior TEXT DEFAULT 'stationary',
                stats TEXT DEFAULT '{}',
                drop_items TEXT DEFAULT '[]',
                x INTEGER,
                y INTEGER,
                respawn_time INTEGER DEFAULT 300,
                last_death_time TIMESTAMP,
                is_alive BOOLEAN DEFAULT TRUE,
                aggro_range INTEGER DEFAULT 1,
                roaming_range INTEGER DEFAULT 2,
                properties TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            await db_manager.execute(monster_table_sql)

            # Monster 인덱스 생성
            await db_manager.execute("CREATE INDEX IF NOT EXISTS idx_monsters_coordinates ON monsters(x, y)")
            await db_manager.execute("CREATE INDEX IF NOT EXISTS idx_monsters_type ON monsters(monster_type)")
            await db_manager.execute("CREATE INDEX IF NOT EXISTS idx_monsters_alive ON monsters(is_alive)")

            await db_manager.commit()
            logger.info("Monster 테이블 생성 완료")

        # 사용자 이름 시스템 컬럼 추가
        cursor = await db_manager.execute("PRAGMA table_info(players)")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]

        display_name_columns = [
            ('display_name', 'TEXT'),
            ('last_name_change', 'TIMESTAMP')
        ]

        for column_name, column_def in display_name_columns:
            if column_name not in column_names:
                logger.info(f"{column_name} 컬럼 추가 중...")
                await db_manager.execute(
                    f"ALTER TABLE players ADD COLUMN {column_name} {column_def}"
                )
                await db_manager.commit()
                logger.info(f"{column_name} 컬럼 추가 완료")

        # 마지막 위치 좌표 컬럼 추가
        location_columns = [
            ('last_room_x', 'INTEGER DEFAULT 0'),
            ('last_room_y', 'INTEGER DEFAULT 0')
        ]

        for column_name, column_def in location_columns:
            if column_name not in column_names:
                logger.info(f"{column_name} 컬럼 추가 중...")
                await db_manager.execute(
                    f"ALTER TABLE players ADD COLUMN {column_name} {column_def}"
                )
                await db_manager.commit()
                logger.info(f"{column_name} 컬럼 추가 완료")

        # rooms 테이블에 x, y 좌표 컬럼 추가
        cursor = await db_manager.execute("PRAGMA table_info(rooms)")
        rooms_columns = await cursor.fetchall()
        rooms_column_names = [col[1] for col in rooms_columns]

        coordinate_columns = [
            ('x', 'INTEGER'),
            ('y', 'INTEGER')
        ]

        for column_name, column_def in coordinate_columns:
            if column_name not in rooms_column_names:
                logger.info(f"rooms 테이블에 {column_name} 컬럼 추가 중...")
                await db_manager.execute(
                    f"ALTER TABLE rooms ADD COLUMN {column_name} {column_def}"
                )
                await db_manager.commit()
                logger.info(f"rooms 테이블에 {column_name} 컬럼 추가 완료")

        # 좌표 인덱스 생성
        await db_manager.execute("CREATE INDEX IF NOT EXISTS idx_rooms_coordinates ON rooms(x, y)")
        await db_manager.commit()
        logger.info("rooms 좌표 인덱스 생성 완료")

        # rooms 테이블에 blocked_exits 컬럼 추가
        if 'blocked_exits' not in rooms_column_names:
            logger.info("rooms 테이블에 blocked_exits 컬럼 추가 중...")
            await db_manager.execute(
                "ALTER TABLE rooms ADD COLUMN blocked_exits TEXT DEFAULT '[]'"
            )
            await db_manager.commit()
            logger.info("rooms 테이블에 blocked_exits 컬럼 추가 완료")

        # stat_level 컬럼 삭제 (레벨 시스템 제거)
        cursor = await db_manager.execute("PRAGMA table_info(players)")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]
        if 'stat_level' in column_names:
            logger.info("stat_level 컬럼 삭제 중...")
            await db_manager.execute("ALTER TABLE players DROP COLUMN stat_level")
            await db_manager.commit()
            logger.info("stat_level 컬럼 삭제 완료")

        # item_prices 테이블 생성 확인 및 생성
        cursor = await db_manager.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='item_prices'"
        )
        item_prices_exists = await cursor.fetchone()

        if not item_prices_exists:
            logger.info("item_prices 테이블 생성 중...")
            await db_manager.execute("""
                CREATE TABLE IF NOT EXISTS item_prices (
                    template_id TEXT PRIMARY KEY,
                    buy_price INTEGER DEFAULT 0,
                    sell_price INTEGER DEFAULT 0
                )
            """)
            await db_manager.commit()
            logger.info("item_prices 테이블 생성 완료")

        # item_prices 초기 데이터 삽입 (멱등성 보장: INSERT OR IGNORE)
        logger.info("item_prices 초기 데이터 삽입 중...")
        initial_prices = [
            ("health_potion", 20, 7),
            ("stamina_potion", 16, 5),
            ("bread", 4, 1),
            ("club", 15, 5),
            ("guard_sword", 50, 12),
            ("guard_heavy_sword", 100, 25),
            ("guard_halberd", 80, 20),
            ("guard_spear", 60, 15),
            ("rusty_dagger", 8, 2),
            ("guide_walking_stick", 10, 3),
            ("rope", 10, 3),
            ("torch", 7, 2),
            ("backpack", 25, 8),
            ("saddle", 50, 15),
            ("leather_bridle", 30, 10),
            ("horse_brush", 12, 4),
            ("horseshoe", 8, 3),
            ("oats", 6, 2),
            ("hay_bale", 5, 2),
            ("oak_branch", 3, 1),
            ("forest_mushroom", 2, 1),
            ("wild_berries", 1, 0),
            ("smooth_stone", 1, 0),
            ("wildflower_crown", 3, 1),
            ("empty_bottle", 2, 1),
            ("merchant_journal", 20, 8),
            ("forgotten_scripture", 15, 5),
        ]
        for template_id, buy_price, sell_price in initial_prices:
            await db_manager.execute(
                "INSERT OR IGNORE INTO item_prices (template_id, buy_price, sell_price) "
                "VALUES (?, ?, ?)",
                (template_id, buy_price, sell_price),
            )
        await db_manager.commit()
        logger.info("item_prices 초기 데이터 삽입 완료 (%d건)", len(initial_prices))

        logger.info("데이터베이스 마이그레이션 완료")

    except Exception as e:
        logger.error(f"데이터베이스 마이그레이션 실패: {e}")
        await db_manager.rollback()
        raise


async def verify_schema(db_connection) -> bool:
    """
    데이터베이스 스키마가 올바르게 생성되었는지 확인합니다.

    Args:
        db_connection: aiosqlite 데이터베이스 연결 객체

    Returns:
        bool: 스키마 검증 성공 여부
    """
    expected_tables = ['players', 'rooms', 'game_objects', 'monsters', 'item_prices']

    try:
        cursor = await db_connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        existing_tables = [row[0] for row in await cursor.fetchall()]

        for table in expected_tables:
            if table not in existing_tables:
                logger.error(f"테이블 '{table}'이 존재하지 않습니다")
                return False

        logger.info("데이터베이스 스키마 검증 완료")
        return True

    except Exception as e:
        logger.error(f"스키마 검증 실패: {e}")
        return False