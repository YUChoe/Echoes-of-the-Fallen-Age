# Database Schema Documentation

**Last Updated**: 2025-12-20

## Overview

이 문서는 Python MUD Engine의 실제 데이터베이스 스키마를 설명합니다.
스키마 변경 시 이 문서를 반드시 업데이트해야 합니다.

---

## Tables

### 1. players

플레이어 계정 정보를 저장합니다.

```sql
CREATE TABLE players (
    id TEXT PRIMARY KEY,                      -- UUID
    username TEXT NOT NULL,                   -- 사용자명 (고유)
    password_hash TEXT NOT NULL,              -- 비밀번호 해시
    email TEXT,                               -- 이메일 (선택)
    preferred_locale TEXT DEFAULT 'en',       -- 선호 언어
    is_admin BOOLEAN DEFAULT FALSE,           -- 관리자 여부
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,

    -- 능력치 (Stats)
    stat_strength INTEGER DEFAULT 10,         -- 힘
    stat_dexterity INTEGER DEFAULT 10,        -- 민첩
    stat_intelligence INTEGER DEFAULT 10,     -- 지능
    stat_wisdom INTEGER DEFAULT 10,           -- 지혜
    stat_constitution INTEGER DEFAULT 10,     -- 체력
    stat_charisma INTEGER DEFAULT 10,         -- 매력
    stat_level INTEGER DEFAULT 1,             -- 레벨
    stat_experience INTEGER DEFAULT 0,        -- 경험치
    stat_experience_to_next INTEGER DEFAULT 100,  -- 다음 레벨까지 필요 경험치
    stat_equipment_bonuses TEXT DEFAULT '{}', -- 장비 보너스 (JSON)
    stat_temporary_effects TEXT DEFAULT '{}', -- 임시 효과 (JSON)

    -- 게임 상태
    gold INTEGER DEFAULT 100,                 -- 골드
    last_room_id TEXT DEFAULT "town_square",  -- 마지막 위치
    last_room_x INTEGER DEFAULT 0,            -- 마지막 X 좌표
    last_room_y INTEGER DEFAULT 0,            -- 마지막 Y 좌표

    -- 사용자 정보
    display_name TEXT,                        -- 표시 이름
    last_name_change TIMESTAMP,               -- 마지막 이름 변경 시간

    -- 종족
    faction_id TEXT DEFAULT 'ash_knights',    -- 종족 ID (factions.id)

    -- 퀘스트 시스템
    completed_quests TEXT DEFAULT '[]',       -- 완료된 퀘스트 목록 (JSON)
    quest_progress TEXT DEFAULT '{}',         -- 진행 중인 퀘스트 (JSON)

    FOREIGN KEY (faction_id) REFERENCES factions(id)
);
```

**인덱스**:
- `CREATE INDEX idx_players_username ON players(username);`

**관계**:
- `characters` 테이블과 1:N 관계
- `factions` 테이블과 N:1 관계

---

### 2. characters

플레이어 캐릭터 정보를 저장합니다. (현재 사용되지 않음 - players 테이블에 통합됨)

```sql
CREATE TABLE characters (
    id TEXT PRIMARY KEY,              -- UUID
    player_id TEXT NOT NULL,          -- players.id (외래 키)
    name TEXT NOT NULL,               -- 캐릭터 이름
    current_room_id TEXT,             -- 현재 방 ID
    inventory TEXT DEFAULT '[]',      -- 인벤토리 (JSON)
    stats TEXT DEFAULT '{}',          -- 능력치 (JSON)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (player_id) REFERENCES players(id)
);
```

**인덱스**:
- `CREATE INDEX idx_characters_player_id ON characters(player_id);`
- `CREATE INDEX idx_characters_current_room ON characters(current_room_id);`

**참고**: 현재 시스템에서는 players 테이블에 캐릭터 정보가 통합되어 있습니다.

---

### 3. rooms

게임 월드의 방(위치) 정보를 저장합니다.

```sql
CREATE TABLE rooms (
    id TEXT PRIMARY KEY,              -- UUID
    description_en TEXT,              -- 영어 설명
    description_ko TEXT,              -- 한국어 설명
    x INTEGER,                        -- X 좌표
    y INTEGER,                        -- Y 좌표
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**인덱스**:
- `CREATE INDEX idx_rooms_coordinates ON rooms(x, y);`

**참고**:
- 방 이름과 출구 정보는 별도 시스템에서 관리됨
- 좌표 기반 위치 시스템 사용

---

### 4. monsters

몬스터 정보를 저장합니다.

```sql
CREATE TABLE monsters (
    id TEXT PRIMARY KEY,              -- UUID
    name_en TEXT NOT NULL,            -- 영어 이름
    name_ko TEXT NOT NULL,            -- 한국어 이름
    description_en TEXT,              -- 영어 설명
    description_ko TEXT,              -- 한국어 설명
    monster_type TEXT DEFAULT 'passive',     -- 몬스터 타입 (aggressive, passive, neutral)
    behavior TEXT DEFAULT 'stationary',      -- 행동 패턴 (stationary, roaming, territorial)
    stats TEXT DEFAULT '{}',          -- 능력치 (JSON: D&D 기반)
    experience_reward INTEGER DEFAULT 50,    -- 경험치 보상
    gold_reward INTEGER DEFAULT 10,   -- 골드 보상
    drop_items TEXT DEFAULT '[]',     -- 드롭 아이템 (JSON)
    respawn_time INTEGER DEFAULT 300, -- 리스폰 시간 (초)
    last_death_time TIMESTAMP,        -- 마지막 사망 시간
    is_alive BOOLEAN DEFAULT TRUE,    -- 생존 여부
    aggro_range INTEGER DEFAULT 1,    -- 어그로 범위
    roaming_range INTEGER DEFAULT 2,  -- 로밍 범위
    properties TEXT DEFAULT '{}',     -- 추가 속성 (JSON)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    faction_id TEXT DEFAULT NULL,     -- 종족 ID (factions.id)
    x INTEGER,                        -- X 좌표
    y INTEGER,                        -- Y 좌표
    FOREIGN KEY (faction_id) REFERENCES factions(id)
);
```

**인덱스**:
- `CREATE INDEX idx_monsters_coordinates ON monsters(x, y);`
- `CREATE INDEX idx_monsters_type ON monsters(monster_type);`
- `CREATE INDEX idx_monsters_alive ON monsters(is_alive);`

**JSON 필드 예시**:
```json
{
  "stats": {
    "strength": 10,
    "dexterity": 14,
    "constitution": 12,
    "intelligence": 8,
    "wisdom": 10,
    "charisma": 6,
    "level": 1,
    "current_hp": 25
  },
  "drop_items": [
    {"item_id": "gold_coin", "drop_chance": 0.5, "min_quantity": 1, "max_quantity": 5}
  ],
  "properties": {
    "template_id": "template_small_rat",
    "roaming_config": {
      "roam_chance": 0.5,
      "roaming_area": {"min_x": -4, "max_x": 4, "min_y": -4, "max_y": 4}
    }
  }
}
```

---

### 5. game_objects

게임 내 오브젝트(아이템, 가구 등) 정보를 저장합니다.

```sql
CREATE TABLE game_objects (
    id TEXT PRIMARY KEY,              -- UUID
    name_en TEXT NOT NULL,            -- 영어 이름
    name_ko TEXT NOT NULL,            -- 한국어 이름
    description_en TEXT,              -- 영어 설명
    description_ko TEXT,              -- 한국어 설명
    object_type TEXT NOT NULL,        -- 오브젝트 타입 (ITEM, WEAPON, ARMOR, etc.)
    location_type TEXT NOT NULL,      -- 위치 타입 (ROOM, INVENTORY, EQUIPPED)
    location_id TEXT,                 -- 위치 ID (room_id or player_id)
    properties TEXT DEFAULT '{}',     -- 속성 (JSON)
    weight REAL DEFAULT 1.0,          -- 무게
    category TEXT DEFAULT 'misc',     -- 카테고리
    equipment_slot TEXT,              -- 장비 슬롯 (HEAD, BODY, WEAPON, etc.)
    is_equipped BOOLEAN DEFAULT FALSE, -- 장착 여부
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**인덱스**:
- `CREATE INDEX idx_game_objects_location ON game_objects(location_type, location_id);`

---

### 6. npcs

NPC(Non-Player Character) 정보를 저장합니다.

```sql
CREATE TABLE npcs (
    id TEXT PRIMARY KEY,              -- UUID
    name_en TEXT NOT NULL,            -- 영어 이름
    name_ko TEXT NOT NULL,            -- 한국어 이름
    description_en TEXT,              -- 영어 설명
    description_ko TEXT,              -- 한국어 설명
    x INTEGER DEFAULT 0,              -- X 좌표
    y INTEGER DEFAULT 0,              -- Y 좌표
    npc_type TEXT DEFAULT 'generic',  -- NPC 타입 (MERCHANT, QUEST_GIVER, etc.)
    dialogue TEXT DEFAULT '{}',       -- 대화 (JSON)
    shop_inventory TEXT DEFAULT '[]', -- 상점 인벤토리 (JSON, MERCHANT 타입용)
    properties TEXT DEFAULT '{}',     -- 추가 속성 (JSON)
    is_active BOOLEAN DEFAULT TRUE,   -- 활성 상태
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    faction_id TEXT,                  -- 종족 ID (factions.id)
    FOREIGN KEY (faction_id) REFERENCES factions(id)
);
```

**인덱스**:
- `CREATE INDEX idx_npcs_coordinates ON npcs(x, y);`
- `CREATE INDEX idx_npcs_type ON npcs(npc_type);`

---

### 7. translations

다국어 번역 정보를 저장합니다.

```sql
CREATE TABLE translations (
    key TEXT NOT NULL PRIMARY KEY,   -- 번역 키
    locale TEXT NOT NULL PRIMARY KEY, -- 언어 코드 (en, ko, etc.)
    value TEXT NOT NULL               -- 번역 값
);
```

**인덱스**:
- `CREATE INDEX idx_translations_key ON translations(key);`

**참고**: 복합 PRIMARY KEY (key, locale) 구조

---

### 8. factions

종족(Faction) 정보를 저장합니다.

```sql
CREATE TABLE factions (
    id TEXT PRIMARY KEY,              -- 종족 ID (예: ash_knights, goblins)
    name_en TEXT NOT NULL,            -- 영어 이름
    name_ko TEXT NOT NULL,            -- 한국어 이름
    description_en TEXT,              -- 영어 설명
    description_ko TEXT,              -- 한국어 설명
    default_stance TEXT DEFAULT 'NEUTRAL',  -- 기본 태도 (FRIENDLY, NEUTRAL, HOSTILE)
    properties TEXT DEFAULT '{}',     -- 추가 속성 (JSON)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**기본 종족**:
- `ash_knights`: 잿빛 기사단 (플레이어 기본 종족)
- `goblins`: 고블린
- `animals`: 동물

---

### 9. faction_relations

종족 간 관계(우호도)를 저장합니다.

```sql
CREATE TABLE faction_relations (
    faction_a_id TEXT NOT NULL PRIMARY KEY, -- 종족 A ID
    faction_b_id TEXT NOT NULL PRIMARY KEY, -- 종족 B ID
    relation_value INTEGER DEFAULT 0,       -- 관계 값 (-100 ~ 100)
    relation_status TEXT DEFAULT 'NEUTRAL', -- 관계 상태
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (faction_a_id) REFERENCES factions(id),
    FOREIGN KEY (faction_b_id) REFERENCES factions(id)
);
```

**관계 값 범위**:
- `-100 ~ -50`: HOSTILE (적대)
- `-49 ~ -1`: UNFRIENDLY (비우호)
- `0`: NEUTRAL (중립)
- `1 ~ 49`: FRIENDLY (우호)
- `50 ~ 100`: ALLIED (동맹)

**기본 관계**:
- 잿빛 기사단 ↔ 고블린: HOSTILE (-80)
- 잿빛 기사단 ↔ 동물: NEUTRAL (0)
- 고블린 ↔ 동물: UNFRIENDLY (-20)

---

## Data Types

### UUID Format
- **형식**: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
- **예시**: `49a55ff4-a1d9-4449-a72c-c664686e1102`
- **생성**: Python `uuid.uuid4()`

### JSON Fields

#### Monster Stats (D&D 5e 기반)
```json
{
  "strength": 10,      // 힘 (1-30)
  "dexterity": 14,     // 민첩 (1-30)
  "constitution": 12,  // 체력 (1-30)
  "intelligence": 8,   // 지능 (1-30)
  "wisdom": 10,        // 지혜 (1-30)
  "charisma": 6,       // 매력 (1-30)
  "level": 1,          // 레벨
  "current_hp": 25     // 현재 HP
}
```

#### Quest Progress
```json
{
  "quest_id_1": {
    "status": "in_progress",
    "objectives": {
      "kill_goblins": {"current": 3, "required": 5},
      "collect_items": {"current": 1, "required": 3}
    }
  }
}
```

---

## Foreign Key Relationships

```
players (1) ─────< (N) characters
factions (1) ─────< (N) monsters (faction_id)
factions (1) ─────< (N) npcs (faction_id)
factions (1) ─────< (N) players (faction_id)
factions (N) ─────< (N) factions (faction_relations)
```

---

## Current Data Statistics

- **players**: 6개
- **characters**: 0개 (사용되지 않음)
- **rooms**: 173개
- **monsters**: 51개
- **game_objects**: 24개
- **npcs**: 0개
- **factions**: 3개
- **faction_relations**: 6개
- **translations**: 10개

---

## Migration Scripts

### Available Scripts

1. **migrate_to_uuid_safe.py**
   - 목적: room ID를 human-readable에서 UUID로 마이그레이션
   - 위치: `scripts/migrate_to_uuid_safe.py`
   - 사용법: `python scripts/migrate_to_uuid_safe.py`
   - 백업: 자동 생성 (`data/mud_engine.db.backup_YYYYMMDD_HHMMSS`)

---

## Backup Strategy

### 자동 백업
- 마이그레이션 스크립트 실행 시 자동 백업 생성
- 형식: `mud_engine.db.backup_YYYYMMDD_HHMMSS`

### 수동 백업
```bash
# 백업 생성
cp data/mud_engine.db data/mud_engine.db.backup_$(date +%Y%m%d_%H%M%S)

# 백업 복원
cp data/mud_engine.db.backup_YYYYMMDD_HHMMSS data/mud_engine.db
```

---

## Schema Modification Guidelines

### 스키마 변경 시 체크리스트

1. **변경 전**
   - [ ] 현재 DB 백업 생성
   - [ ] 영향받는 테이블 및 관계 파악
   - [ ] 마이그레이션 스크립트 작성

2. **변경 중**
   - [ ] 외래 키 제약 조건 고려
   - [ ] 트랜잭션 사용
   - [ ] 롤백 계획 수립

3. **변경 후**
   - [ ] 데이터 무결성 검증
   - [ ] 이 문서(`DATABASE_SCHEMA.md`) 업데이트
   - [ ] Change Log에 변경사항 기록
   - [ ] 관련 코드 모델 업데이트 (`src/mud_engine/game/models.py`)

---

## Notes

- SQLite WAL 모드 사용 중 (`mud_engine.db-wal`, `mud_engine.db-shm` 파일 정상)
- 외래 키 제약 조건은 기본적으로 비활성화되어 있음 (마이그레이션 시 수동 관리)
- JSON 필드는 Python에서 `json.loads()`/`json.dumps()`로 처리
- 모든 timestamp는 UTC 기준
- 좌표 시스템: 모든 엔티티(monsters, npcs, players)는 x, y 좌표 사용
- 방 시스템: rooms 테이블은 좌표 정보만 저장, 이름과 출구는 별도 관리

---

**작성자**: Kiro AI
**최종 수정**: 2025-12-20
