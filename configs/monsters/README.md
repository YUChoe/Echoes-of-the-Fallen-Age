# Monster Spawn Configuration

## 개요

이 디렉토리는 몬스터 스폰 설정 파일을 포함합니다.
범용 스폰 스크립트(`scripts/spawn_monsters.py`)와 함께 사용됩니다.

## 사용법

### 기본 사용
```bash
source mud_engine_env/Scripts/activate
PYTHONPATH=. python scripts/spawn_monsters.py --config configs/monsters/small_rats.json
```

### 설정 파일 구조

```json
{
  "template": {
    "id": "template_monster_name",
    "name": {"en": "Monster Name", "ko": "몬스터 이름"},
    "description": {"en": "...", "ko": "..."},
    "monster_type": "AGGRESSIVE|PASSIVE|NEUTRAL",
    "behavior": "ROAMING|STATIONARY|PATROLLING",
    "stats": {
      "strength": 10,
      "dexterity": 10,
      "constitution": 10,
      "intelligence": 10,
      "wisdom": 10,
      "charisma": 10,
      "level": 1,
      "current_hp": 20
    },
    "rewards": {
      "experience": 50,
      "gold": 10
    },
    "drop_items": [],
    "respawn_time": 300,
    "aggro_range": 2,
    "roaming_range": 3
  },
  "spawn_criteria": {
    "name_contains": "평원",
    "area": {
      "min_x": -4,
      "max_x": 4,
      "min_y": -4,
      "max_y": 4
    }
  },
  "spawn": {
    "template_id": "template_monster_name",
    "count": 20,
    "roaming": {
      "enabled": true,
      "chance": 0.5,
      "range": 2
    }
  }
}
```

## 필드 설명

### template

#### monster_type
- `AGGRESSIVE`: 선공형 (플레이어를 보면 공격)
- `PASSIVE`: 후공형 (공격받으면 반격)
- `NEUTRAL`: 중립형 (공격하지 않음)

#### behavior
- `ROAMING`: 로밍형 (자유롭게 이동)
- `STATIONARY`: 고정형 (이동하지 않음)
- `PATROLLING`: 순찰형 (정해진 경로 이동, 미구현)

#### stats (D&D 5e 기반)
- `strength`: 힘 (1-30) - 물리 공격력
- `dexterity`: 민첩 (1-30) - 명중률, 회피, AC
- `constitution`: 체력 (1-30) - HP
- `intelligence`: 지능 (1-30) - 마법 공격력
- `wisdom`: 지혜 (1-30) - 마법 방어력
- `charisma`: 매력 (1-30) - 특수 능력
- `level`: 레벨 (1-100)
- `current_hp`: 현재 HP (자동 계산 가능)

### spawn_criteria

방을 찾는 조건입니다.

- `name_contains`: 방 이름에 포함될 문자열 (예: "평원", "숲")
- `area`: 좌표 범위
  - `min_x`, `max_x`: X 좌표 범위
  - `min_y`, `max_y`: Y 좌표 범위
- `room_ids`: 특정 방 ID 목록 (UUID)

### spawn

스폰 설정입니다.

- `template_id`: 사용할 템플릿 ID
- `count`: 스폰할 개수
- `spawn_area`: 스폰 영역 (선택)
- `roaming`: 로밍 설정
  - `enabled`: true/false (로밍 활성화 여부)
  - `chance`: 0.0-1.0 (이동 확률)
  - `range`: 로밍 범위 (칸 수)
  - `area`: 로밍 영역 (선택, 생략 시 spawn_area 사용)

## 예시

### 1. 작은 쥐 (로밍형)
```bash
python scripts/spawn_monsters.py --config configs/monsters/small_rats.json
```
- 평원 전체에 20마리 분산 스폰
- 50% 확률로 로밍
- 후공형 (공격받으면 반격)

### 2. 숲 고블린 (공격형)
```bash
python scripts/spawn_monsters.py --config configs/monsters/forest_goblins.json
```
- 숲 지역에 10마리 스폰
- 30% 확률로 로밍
- 선공형 (플레이어 발견 시 공격)

### 3. 마을 경비병 (고정형)
```bash
python scripts/spawn_monsters.py --config configs/monsters/town_guard.json
```
- 특정 위치에 고정
- 로밍 비활성화
- 중립형 (공격하지 않음)

## 로밍 설정

### 로밍 활성화
```json
"roaming": {
  "enabled": true,
  "chance": 0.5,
  "range": 2
}
```

### 로밍 비활성화 (고정)
```json
"roaming": {
  "enabled": false
}
```

### 제한된 영역 로밍
```json
"roaming": {
  "enabled": true,
  "chance": 0.3,
  "range": 3,
  "area": {
    "min_x": 0,
    "max_x": 5,
    "min_y": 0,
    "max_y": 5
  }
}
```

## 주의사항

1. **템플릿 ID**: 고유해야 하며, `template_` 접두사 사용 권장
2. **스폰 개수**: 너무 많으면 서버 성능에 영향
3. **로밍 범위**: 너무 크면 몬스터가 너무 멀리 이동
4. **aggro_range**: 선공형 몬스터의 감지 범위

## 기존 스크립트와의 차이

### 기존 (spawn_small_rats.py)
- 작은 쥐 전용
- 하드코딩된 설정
- 재사용 불가

### 새 버전 (spawn_monsters.py)
- 모든 몬스터 지원
- JSON 설정 파일 사용
- 재사용 가능
- 로밍 활성화/비활성화 선택 가능
