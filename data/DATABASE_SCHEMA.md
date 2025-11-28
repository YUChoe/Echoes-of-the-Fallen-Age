# Database Schema Documentation

**Last Updated**: 2025-11-28  
**Database Version**: 1.1.0 (UUID Migration)

## Overview

이 문서는 Python MUD Engine의 데이터베이스 스키마를 설명합니다.
스키마 변경 시 이 문서를 반드시 업데이트해야 합니다.

## Change Log

### 2025-11-28: UUID Migration (v1.1.0)
- **변경사항**: 모든 `room.id`를 human-readable ID에서 UUID로 변경
- **영향받는 테이블**: `rooms`, `monsters`
- **마이그레이션 스크립트**: `scripts/migrate_to_uuid_safe.py`
- **이유**: 고유성 보장, 자동 생성, 확장성 향상

### 2025-11-27: Initial Schema (v1.0.0)
- 초기 데이터베이스 스키마 생성

---

## Tables

### 1. players

플레이어 계정 정보를 저장합니다.

```sql
CREATE TABLE players (
    id TEXT PRIMARY KEY,              -- UUID
    username TEXT UNIQUE NOT NULL,    -- 사용자명 (고유)
    password_hash TEXT NOT NULL,      -- 비밀번호 해시
    email TEXT,                       -- 이메일 (선택)
    is_admin BOOLEAN DEFAULT 0,       -- 관리자 여부
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    display_name TEXT,                -- 표시 이름
    last_name_change TIMESTAMP        -- 마지막 이름 변경 시간
);
```

**인덱스**:
- `username` (UNIQUE)

**관계**:
- `characters` 테이블과 1:N 관계

---

### 2. characters

플레이어 캐릭터 정보를 저장합니다.

```sql
CREATE TABLE characters (
    id TEXT PRIMARY KEY,              -- UUID
    player_id TEXT NOT NULL,          -- players.id (외래 키)
    name TEXT NOT NULL,               -- 캐릭터 이름
    level INTEGER DEFAULT 1,          -- 레벨
    experience INTEGER DEFAULT 0,     -- 경험치
    gold INTEGER DEFAULT 0,           -- 골드
    stats TEXT DEFAULT '{}',          -- 능력치 (JSON)
    inventory TEXT DEFAULT '[]',      -- 인벤토리 (JSON)
    equipment TEXT DEFAULT '{}',      -- 장비 (JSON)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (player_id) REFERENCES players(id)
);
```

**인덱스**:
- `player_id`

---

### 3. rooms

게임 월드의 방(위치) 정보를 저장합니다.

```sql
CREATE TABLE rooms (
    id TEXT PRIMARY KEY,              -- UUID (v1.1.0부터)
    name_en TEXT NOT NULL,            -- 영어 이름
    name_ko TEXT NOT NULL,            -- 한국어 이름
    description_en TEXT,              -- 영어 설명
    description_ko TEXT,              -- 한국어 설명
    exits TEXT DEFAULT '{}',          -- 출구 정보 (JSON: {direction: room_id})
    x INTEGER,                        -- X 좌표
    y INTEGER,                        -- Y 좌표
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**인덱스**:
- `x, y` (복합 인덱스)

**JSON 필드 예시**:
```json
{
  "exits": {
    "north": "a1b2c3d4-...",
    "south": "e5f6g7h8-...",
    "east": "i9j0k1l2-..."
  }
}
```

**변경 이력**:
- v1.1.0: `id` 타입을 TEXT(human-readable)에서 UUID로 변경
- v1.1.0: `exits` JSON의 room_id 값들도 UUID로 변경

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
    monster_type TEXT NOT NULL,       -- 몬스터 타입 (AGGRESSIVE, PASSIVE, NEUTRAL)
    behavior TEXT NOT NULL,           -- 행동 패턴 (STATIONARY, ROAMING, PATROLLING)
    stats TEXT NOT NULL,              -- 능력치 (JSON: D&D 기반)
    experience_reward INTEGER DEFAULT 0,  -- 경험치 보상
    gold_reward INTEGER DEFAULT 0,    -- 골드 보상
    drop_items TEXT DEFAULT '[]',     -- 드롭 아이템 (JSON)
    spawn_room_id TEXT,               -- 스폰 방 ID (rooms.id, UUID)
    current_room_id TEXT,             -- 현재 방 ID (rooms.id, UUID)
    respawn_time INTEGER DEFAULT 300, -- 리스폰 시간 (초)
    last_death_time TIMESTAMP,        -- 마지막 사망 시간
    is_alive BOOLEAN DEFAULT 1,       -- 생존 여부
    aggro_range INTEGER DEFAULT 0,    -- 어그로 범위
    roaming_range INTEGER DEFAULT 0,  -- 로밍 범위
    properties TEXT DEFAULT '{}',     -- 추가 속성 (JSON)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**인덱스**:
- `current_room_id`
- `is_alive`

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
    {"item_id": "gold_coin", "chance": 0.5, "quantity": [1, 5]}
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

**변경 이력**:
- v1.1.0: `spawn_room_id`, `current_room_id`가 참조하는 room ID가 UUID로 변경

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
    properties TEXT DEFAULT '{}',     -- 속성 (JSON)
    room_id TEXT,                     -- 위치한 방 ID (rooms.id, UUID)
    owner_id TEXT,                    -- 소유자 ID (players.id or characters.id)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**인덱스**:
- `room_id`
- `owner_id`

**변경 이력**:
- v1.1.0: `room_id`가 참조하는 room ID가 UUID로 변경

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
    npc_type TEXT NOT NULL,           -- NPC 타입 (MERCHANT, QUEST_GIVER, etc.)
    dialogue TEXT DEFAULT '{}',       -- 대화 (JSON)
    room_id TEXT,                     -- 위치한 방 ID (rooms.id, UUID)
    properties TEXT DEFAULT '{}',     -- 추가 속성 (JSON)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**인덱스**:
- `room_id`

**변경 이력**:
- v1.1.0: `room_id`가 참조하는 room ID가 UUID로 변경

---

### 7. translations

다국어 번역 정보를 저장합니다.

```sql
CREATE TABLE translations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL,                -- 번역 키
    locale TEXT NOT NULL,             -- 언어 코드 (en, ko, etc.)
    value TEXT NOT NULL,              -- 번역 값
    category TEXT,                    -- 카테고리
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(key, locale)
);
```

**인덱스**:
- `key, locale` (UNIQUE 복합 인덱스)

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

#### Room Exits
```json
{
  "north": "uuid-of-north-room",
  "south": "uuid-of-south-room",
  "east": "uuid-of-east-room",
  "west": "uuid-of-west-room"
}
```

---

## Foreign Key Relationships

```
players (1) ─────< (N) characters
rooms (1) ─────< (N) monsters (spawn_room_id, current_room_id)
rooms (1) ─────< (N) game_objects (room_id)
rooms (1) ─────< (N) npcs (room_id)
```

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

---

**문서 버전**: 1.1.0  
**작성자**: Kiro AI  
**최종 수정**: 2025-11-28
