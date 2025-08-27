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
        stat_strength INTEGER DEFAULT 10,
        stat_dexterity INTEGER DEFAULT 10,
        stat_intelligence INTEGER DEFAULT 10,
        stat_wisdom INTEGER DEFAULT 10,
        stat_constitution INTEGER DEFAULT 10,
        stat_charisma INTEGER DEFAULT 10,
        stat_level INTEGER DEFAULT 1,
        stat_experience INTEGER DEFAULT 0,
        stat_experience_to_next INTEGER DEFAULT 100,
        stat_equipment_bonuses TEXT DEFAULT '{}',
        stat_temporary_effects TEXT DEFAULT '{}'
    );
    """,

    """
    -- 캐릭터 테이블
    CREATE TABLE IF NOT EXISTS characters (
        id TEXT PRIMARY KEY,
        player_id TEXT NOT NULL,
        name TEXT NOT NULL,
        current_room_id TEXT,
        inventory TEXT DEFAULT '[]', -- JSON 형태로 저장
        stats TEXT DEFAULT '{}', -- JSON 형태로 저장
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE
    );
    """,

    """
    -- 방 테이블
    CREATE TABLE IF NOT EXISTS rooms (
        id TEXT PRIMARY KEY,
        name_en TEXT NOT NULL,
        name_ko TEXT NOT NULL,
        description_en TEXT,
        description_ko TEXT,
        exits TEXT DEFAULT '{}', -- JSON 형태로 저장 (방향: 목적지_방_ID)
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
    -- 다국어 텍스트 테이블
    CREATE TABLE IF NOT EXISTS translations (
        key TEXT NOT NULL,
        locale TEXT NOT NULL,
        value TEXT NOT NULL,
        PRIMARY KEY (key, locale)
    );
    """,

    """
    -- 인덱스 생성
    CREATE INDEX IF NOT EXISTS idx_players_username ON players(username);
    CREATE INDEX IF NOT EXISTS idx_characters_player_id ON characters(player_id);
    CREATE INDEX IF NOT EXISTS idx_characters_current_room ON characters(current_room_id);
    CREATE INDEX IF NOT EXISTS idx_game_objects_location ON game_objects(location_type, location_id);
    CREATE INDEX IF NOT EXISTS idx_translations_key ON translations(key);
    """
]

# 초기 데이터
INITIAL_DATA: List[str] = [
    """
    -- 기본 방 생성
    INSERT OR IGNORE INTO rooms (id, name_en, name_ko, description_en, description_ko, exits) VALUES
    ('room_001', 'Town Square', '마을 광장',
     'A bustling town square with a fountain in the center. People gather here to chat and trade.',
     '중앙에 분수가 있는 번화한 마을 광장입니다. 사람들이 모여 대화하고 거래를 합니다.',
     '{"north": "room_002", "east": "room_003"}'),
    ('room_002', 'North Street', '북쪽 거리',
     'A quiet street leading north from the town square. Small shops line both sides.',
     '마을 광장에서 북쪽으로 이어지는 조용한 거리입니다. 양쪽에 작은 상점들이 늘어서 있습니다.',
     '{"south": "room_001"}'),
    ('room_003', 'East Market', '동쪽 시장',
     'A busy marketplace filled with merchants selling various goods.',
     '다양한 상품을 파는 상인들로 가득한 번화한 시장입니다.',
     '{"west": "room_001"}');
    """,

    """
    -- 기본 번역 텍스트
    INSERT OR IGNORE INTO translations (key, locale, value) VALUES
    ('welcome_message', 'en', 'Welcome to the MUD Engine!'),
    ('welcome_message', 'ko', 'MUD 엔진에 오신 것을 환영합니다!'),
    ('login_prompt', 'en', 'Please enter your username:'),
    ('login_prompt', 'ko', '사용자명을 입력하세요:'),
    ('password_prompt', 'en', 'Please enter your password:'),
    ('password_prompt', 'ko', '비밀번호를 입력하세요:'),
    ('invalid_credentials', 'en', 'Invalid username or password.'),
    ('invalid_credentials', 'ko', '잘못된 사용자명 또는 비밀번호입니다.'),
    ('command_not_found', 'en', 'Command not found. Type "help" for available commands.'),
    ('command_not_found', 'ko', '명령어를 찾을 수 없습니다. "help"를 입력하여 사용 가능한 명령어를 확인하세요.');
    """
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
            ('stat_strength', 'INTEGER DEFAULT 10'),
            ('stat_dexterity', 'INTEGER DEFAULT 10'),
            ('stat_intelligence', 'INTEGER DEFAULT 10'),
            ('stat_wisdom', 'INTEGER DEFAULT 10'),
            ('stat_constitution', 'INTEGER DEFAULT 10'),
            ('stat_charisma', 'INTEGER DEFAULT 10'),
            ('stat_level', 'INTEGER DEFAULT 1'),
            ('stat_experience', 'INTEGER DEFAULT 0'),
            ('stat_experience_to_next', 'INTEGER DEFAULT 100'),
            ('stat_equipment_bonuses', "TEXT DEFAULT '{}'"),
            ('stat_temporary_effects', "TEXT DEFAULT '{}'")
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
    expected_tables = ['players', 'characters', 'rooms', 'game_objects', 'translations']

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