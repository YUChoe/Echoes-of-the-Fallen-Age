# Monster Templates Configuration

## 개요

이 디렉토리는 몬스터 템플릿 파일을 포함합니다.
외부 스폰 스크립트(`scripts/spawn_monster.py`)와 함께 사용됩니다.

## 사용법

### 기본 사용
```bash
# 특정 좌표에 몬스터 스폰
source mud_engine_env/Scripts/activate
PYTHONPATH=. python scripts/spawn_monster.py <template_id> <x> <y>

# 여러 마리 스폰
PYTHONPATH=. python scripts/spawn_monster.py <template_id> <x> <y> --count 3

# 사용 가능한 템플릿 목록 보기
PYTHONPATH=. python scripts/spawn_monster.py --list
```

### 예시
```bash
# 좌표 (5, 0)에 작은 쥐 2마리 스폰
python scripts/spawn_monster.py small_rats 5 0 --count 2

# 좌표 (3, 0)에 숲 고블린 1마리 스폰
python scripts/spawn_monster.py forest_goblins 3 0

# 모든 몬스터 템플릿 목록 확인
python scripts/spawn_monster.py --list
```

### 템플릿 파일 구조

각 몬스터는 개별 JSON 파일로 관리됩니다.

```json
{
  "template_id": "small_rats",
  "name": {
    "en": "Small Rat",
    "ko": "작은 쥐"
  },
  "description": {
    "en": "A small, quick rat scurrying about.",
    "ko": "빠르게 돌아다니는 작은 쥐입니다."
  },
  "monster_type": "PASSIVE",
  "behavior": "ROAMING",
  "stats": {
    "strength": 6,
    "dexterity": 14,
    "constitution": 8,
    "intelligence": 2,
    "wisdom": 10,
    "charisma": 4,
    "level": 1,
    "current_hp": 8
  },
  "gold_reward": 0,
  "drop_items": [],
  "respawn_time": 300,
  "aggro_range": 0,
  "roaming_range": 2
}
```

## 필드 설명

### 기본 정보
- `template_id`: 고유 템플릿 식별자
- `name`: 다국어 이름 (en, ko)
- `description`: 다국어 설명 (en, ko)

### 몬스터 타입
- `AGGRESSIVE`: 선공형 (플레이어를 보면 공격)
- `PASSIVE`: 후공형 (공격받으면 반격)
- `NEUTRAL`: 중립형 (공격하지 않음)

### 행동 패턴
- `ROAMING`: 로밍형 (자유롭게 이동)
- `STATIONARY`: 고정형 (이동하지 않음)
- `PATROLLING`: 순찰형 (정해진 경로 이동, 미구현)

### 스탯 (D&D 5e 기반)
- `strength`: 힘 (1-30) - 물리 공격력
- `dexterity`: 민첩 (1-30) - 명중률, 회피, AC
- `constitution`: 체력 (1-30) - HP
- `intelligence`: 지능 (1-30) - 마법 공격력
- `wisdom`: 지혜 (1-30) - 마법 방어력
- `charisma`: 매력 (1-30) - 특수 능력
- `level`: 레벨 (1-100)
- `current_hp`: 현재 HP

### 기타 설정
- `gold_reward`: 처치 시 골드 보상
- `drop_items`: 드롭 아이템 목록
- `respawn_time`: 리스폰 시간 (초)
- `aggro_range`: 감지 범위 (선공형 몬스터용)
- `roaming_range`: 로밍 범위

## 사용 가능한 템플릿

### 1. small_rats (작은 쥐)
- 타입: PASSIVE (후공형)
- 행동: ROAMING (로밍)
- 레벨: 1
- 특징: 빠르고 약한 몬스터

### 2. forest_goblins (숲 고블린)
- 타입: AGGRESSIVE (선공형)
- 행동: ROAMING (로밍)
- 레벨: 3
- 특징: 중간 강도의 공격형 몬스터

### 3. town_guard (마을 경비병)
- 타입: PASSIVE (후공형)
- 행동: STATIONARY (고정)
- 레벨: 5
- 특징: 마을을 지키는 경비병

### 4. square_guard (광장 경비병)
- 타입: NEUTRAL (중립)
- 행동: STATIONARY (고정)
- 레벨: 8
- 특징: 광장을 지키는 강한 경비병

### 5. light_armored_guard (경장 경비병)
- 타입: NEUTRAL (중립)
- 행동: STATIONARY (고정)
- 레벨: 6
- 특징: 경장갑을 착용한 경비병

### 6. harbor_guide (항구 안내인)
- 타입: NEUTRAL (중립)
- 행동: STATIONARY (고정)
- 레벨: 5
- 특징: 항구에서 안내하는 NPC

## 새 템플릿 추가하기

새로운 몬스터 템플릿을 추가하려면:

1. `configs/monsters/` 디렉토리에 새 JSON 파일 생성
2. 위의 구조에 맞춰 템플릿 정의
3. `template_id`는 파일명과 동일하게 설정
4. 스크립트로 테스트

예시: `configs/monsters/my_monster.json`
```json
{
  "template_id": "my_monster",
  "name": {
    "en": "My Monster",
    "ko": "내 몬스터"
  },
  "description": {
    "en": "A custom monster.",
    "ko": "커스텀 몬스터입니다."
  },
  "monster_type": "AGGRESSIVE",
  "behavior": "ROAMING",
  "stats": {
    "strength": 12,
    "dexterity": 10,
    "constitution": 14,
    "intelligence": 8,
    "wisdom": 10,
    "charisma": 6,
    "level": 2,
    "current_hp": 28
  },
  "gold_reward": 15,
  "drop_items": [],
  "respawn_time": 300,
  "aggro_range": 2,
  "roaming_range": 3
}
```

## 주의사항

1. **좌표 확인**: 스폰하려는 좌표에 방이 존재하는지 확인
2. **스폰 개수**: 너무 많으면 서버 성능에 영향
3. **템플릿 ID**: 파일명과 template_id가 일치해야 함
4. **JSON 형식**: 올바른 JSON 형식을 유지해야 함
