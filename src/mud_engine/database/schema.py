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
        stat_temporary_effects TEXT DEFAULT '{}',

        -- 경제 시스템
        gold INTEGER DEFAULT 100,

        -- 퀘스트 시스템
        completed_quests TEXT DEFAULT '[]', -- JSON 형태로 저장 (완료된 퀘스트 ID 목록)
        quest_progress TEXT DEFAULT '{}' -- JSON 형태로 저장 (진행 중인 퀘스트 상태)
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
        description_en TEXT,
        description_ko TEXT,
        exits TEXT DEFAULT '{}', -- JSON 형태로 저장 (방향: 목적지_방_ID)
        x INTEGER, -- X 좌표
        y INTEGER, -- Y 좌표
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
    -- NPC 테이블
    CREATE TABLE IF NOT EXISTS npcs (
        id TEXT PRIMARY KEY,
        name_en TEXT NOT NULL,
        name_ko TEXT NOT NULL,
        description_en TEXT,
        description_ko TEXT,
        x INTEGER DEFAULT 0, -- X 좌표
        y INTEGER DEFAULT 0, -- Y 좌표
        npc_type TEXT DEFAULT 'generic', -- 'merchant', 'guard', 'quest_giver', 'generic'
        dialogue TEXT DEFAULT '{}', -- JSON 형태로 저장 {'en': ['line1'], 'ko': ['대사1']}
        shop_inventory TEXT DEFAULT '[]', -- JSON 형태로 저장 (아이템 ID 목록)
        properties TEXT DEFAULT '{}', -- JSON 형태로 저장
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        faction_id TEXT -- 종족 ID
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
        experience_reward INTEGER DEFAULT 50,
        gold_reward INTEGER DEFAULT 10,
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
    CREATE INDEX IF NOT EXISTS idx_npcs_coordinates ON npcs(x, y);
    CREATE INDEX IF NOT EXISTS idx_npcs_type ON npcs(npc_type);
    CREATE INDEX IF NOT EXISTS idx_monsters_coordinates ON monsters(x, y);
    CREATE INDEX IF NOT EXISTS idx_monsters_type ON monsters(monster_type);
    CREATE INDEX IF NOT EXISTS idx_monsters_alive ON monsters(is_alive);
    """
]

# 초기 데이터
INITIAL_DATA: List[str] = [
    # 기본 방 생성은 제거됨 - UUID 기반 시스템 사용

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
            ('stat_temporary_effects', "TEXT DEFAULT '{}'"),
            ('gold', 'INTEGER DEFAULT 100')  # 경제 시스템
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

        # NPC 테이블 생성 확인 및 생성
        cursor = await db_manager.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='npcs'")
        npc_table_exists = await cursor.fetchone()

        if not npc_table_exists:
            logger.info("NPC 테이블 생성 중...")
            npc_table_sql = """
            CREATE TABLE IF NOT EXISTS npcs (
                id TEXT PRIMARY KEY,
                name_en TEXT NOT NULL,
                name_ko TEXT NOT NULL,
                description_en TEXT,
                description_ko TEXT,
                x INTEGER DEFAULT 0,
                y INTEGER DEFAULT 0,
                npc_type TEXT DEFAULT 'generic',
                dialogue TEXT DEFAULT '{}',
                shop_inventory TEXT DEFAULT '[]',
                properties TEXT DEFAULT '{}',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                faction_id TEXT
            );
            """
            await db_manager.execute(npc_table_sql)

            # NPC 인덱스 생성
            await db_manager.execute("CREATE INDEX IF NOT EXISTS idx_npcs_coordinates ON npcs(x, y)")
            await db_manager.execute("CREATE INDEX IF NOT EXISTS idx_npcs_type ON npcs(npc_type)")

            await db_manager.commit()
            logger.info("NPC 테이블 생성 완료")

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
                experience_reward INTEGER DEFAULT 50,
                gold_reward INTEGER DEFAULT 10,
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