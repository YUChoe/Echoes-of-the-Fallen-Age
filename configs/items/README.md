# Item Templates Configuration

## 개요

이 디렉토리는 아이템 템플릿 파일을 포함합니다.
외부 스폰 스크립트(`scripts/spawn_items.py`)와 함께 사용됩니다.

## 사용법

### 기본 사용
```bash
# 특정 좌표에 아이템 스폰
source mud_engine_env/Scripts/activate
PYTHONPATH=. python scripts/spawn_items.py <template_id> <x> <y>

# 여러 개 스폰
PYTHONPATH=. python scripts/spawn_items.py <template_id> <x> <y> --count 5

# 사용 가능한 템플릿 목록 보기
PYTHONPATH=. python scripts/spawn_items.py --list
```

### 예시
```bash
# 좌표 (3, 0)에 횃불 3개 스폰
python scripts/spawn_items.py torch 3 0 --count 3

# 좌표 (5, 0)에 빵 1개 스폰
python scripts/spawn_items.py bread 5 0

# 모든 아이템 템플릿 목록 확인
python scripts/spawn_items.py --list
```

### 템플릿 파일 구조

각 아이템은 개별 JSON 파일로 관리됩니다.

```json
{
  "template_id": "torch",
  "name_en": "Torch",
  "name_ko": "횃불",
  "description_en": "A wooden torch that provides light.",
  "description_ko": "빛을 제공하는 나무 횃불입니다.",
  "object_type": "item",
  "category": "misc",
  "weight": 0.5,
  "properties": {
    "light_duration": 3600
  },
  "stackable": true,
  "max_stack": 50
}
```

## 필드 설명

### 기본 정보
- `template_id`: 고유 템플릿 식별자 (파일명과 동일)
- `name_en`: 영어 이름
- `name_ko`: 한국어 이름
- `description_en`: 영어 설명
- `description_ko`: 한국어 설명

### 아이템 타입
- `item`: 일반 아이템
- `consumable`: 소비 가능한 아이템
- `equipment`: 장비 아이템 (미구현)
- `weapon`: 무기 (미구현)
- `armor`: 방어구 (미구현)

### 카테고리
- `misc`: 기타 아이템
- `consumable`: 소비품
- `currency`: 화폐
- `tool`: 도구
- `material`: 재료

### 기타 속성
- `weight`: 무게 (kg)
- `properties`: 아이템별 특수 속성
- `stackable`: 스택 가능 여부 (true/false)
- `max_stack`: 최대 스택 개수
- `equipment_slot`: 장비 슬롯 (장비 아이템용)
## 사용 가능한 템플릿

### 소비품 (Consumables)

#### bread (빵)
- 타입: consumable
- 카테고리: consumable
- 무게: 0.3kg
- 스택: 최대 10개
- 특징: 배고픔 회복 아이템

#### health_potion (체력 물약)
- 타입: consumable
- 카테고리: consumable
- 무게: 0.2kg
- 스택: 최대 5개
- 특징: 체력 회복 아이템

#### forest_mushroom (숲 버섯)
- 타입: consumable
- 카테고리: consumable
- 무게: 0.1kg
- 스택: 최대 20개
- 특징: 자연에서 채집한 버섯

#### wild_berries (야생 베리)
- 타입: consumable
- 카테고리: consumable
- 무게: 0.1kg
- 스택: 최대 30개
- 특징: 야생에서 채집한 베리

#### essence_of_life (생명의 정수)
- 타입: consumable
- 카테고리: consumable
- 무게: 0.1kg
- 스택: 최대 3개
- 특징: 희귀한 생명력 회복 아이템

### 일반 아이템 (Items)

#### torch (횃불)
- 타입: item
- 카테고리: misc
- 무게: 0.5kg
- 스택: 최대 50개
- 특징: 빛을 제공하는 도구

#### rope (밧줄)
- 타입: item
- 카테고리: misc
- 무게: 1.0kg
- 스택: 최대 5개
- 특징: 다양한 용도로 사용 가능

#### smooth_stone (매끄러운 돌)
- 타입: item
- 카테고리: misc
- 무게: 0.8kg
- 스택: 최대 20개
- 특징: 건축이나 제작에 사용

#### oak_branch (참나무 가지)
- 타입: item
- 카테고리: misc
- 무게: 0.3kg
- 스택: 최대 30개
- 특징: 제작 재료로 사용

#### wildflower_crown (야생화 화관)
- 타입: item
- 카테고리: misc
- 무게: 0.1kg
- 스택: 불가 (1개)
- 특징: 장식용 아이템

#### backpack (배낭)
- 타입: item
- 카테고리: misc
- 무게: 2.0kg
- 스택: 불가 (1개)
- 특징: 인벤토리 확장 아이템

### 화폐 (Currency)

#### gold_coin (골드)
- 타입: item
- 카테고리: currency
- 무게: 0.01kg
- 스택: 최대 1000개
- 특징: 게임 내 화폐
## 새 템플릿 추가하기

새로운 아이템 템플릿을 추가하려면:

1. `configs/items/` 디렉토리에 새 JSON 파일 생성
2. 위의 구조에 맞춰 템플릿 정의
3. `template_id`는 파일명과 동일하게 설정
4. 스크립트로 테스트

### 일반 아이템 예시
`configs/items/my_item.json`
```json
{
  "template_id": "my_item",
  "name_en": "My Item",
  "name_ko": "내 아이템",
  "description_en": "A custom item.",
  "description_ko": "커스텀 아이템입니다.",
  "object_type": "item",
  "category": "misc",
  "weight": 1.0,
  "properties": {
    "durability": 100
  },
  "stackable": true,
  "max_stack": 10
}
```

### 소비품 예시
`configs/items/my_potion.json`
```json
{
  "template_id": "my_potion",
  "name_en": "My Potion",
  "name_ko": "내 물약",
  "description_en": "A custom healing potion.",
  "description_ko": "커스텀 치료 물약입니다.",
  "object_type": "consumable",
  "category": "consumable",
  "weight": 0.2,
  "properties": {
    "heal_amount": 50,
    "effect_duration": 0
  },
  "stackable": true,
  "max_stack": 5
}
```

### 장비 아이템 예시 (미구현)
`configs/items/my_sword.json`
```json
{
  "template_id": "my_sword",
  "name_en": "My Sword",
  "name_ko": "내 검",
  "description_en": "A custom sword.",
  "description_ko": "커스텀 검입니다.",
  "object_type": "weapon",
  "category": "weapon",
  "weight": 3.0,
  "equipment_slot": "main_hand",
  "properties": {
    "damage": 15,
    "durability": 100,
    "attack_speed": 1.2
  },
  "stackable": false
}
```

## 속성(Properties) 가이드

### 소비품 속성
- `heal_amount`: 체력 회복량
- `mana_restore`: 마나 회복량
- `hunger_restore`: 배고픔 회복량
- `effect_duration`: 효과 지속 시간 (초)
- `buff_type`: 버프 타입
- `buff_strength`: 버프 강도

### 도구 속성
- `light_duration`: 빛 지속 시간 (초)
- `durability`: 내구도
- `efficiency`: 효율성
- `range`: 사용 범위

### 장비 속성 (미구현)
- `damage`: 공격력
- `defense`: 방어력
- `attack_speed`: 공격 속도
- `critical_chance`: 치명타 확률
- `durability`: 내구도

## 주의사항

1. **좌표 확인**: 스폰하려는 좌표에 방이 존재하는지 확인
2. **스폰 개수**: 너무 많으면 서버 성능에 영향
3. **템플릿 ID**: 파일명과 template_id가 일치해야 함
4. **JSON 형식**: 올바른 JSON 형식을 유지해야 함
5. **무게 설정**: 현실적인 무게 값 설정
6. **스택 설정**: 아이템 특성에 맞는 스택 개수 설정

## 스택 가능 설정 가이드

### 스택 가능 (stackable: true)
- 소비품: 물약, 음식, 재료
- 화폐: 골드, 보석
- 재료: 돌, 나무, 광물
- 도구: 횃불, 화살

### 스택 불가 (stackable: false)
- 장비: 무기, 방어구
- 고유 아이템: 열쇠, 특별한 장신구
- 대형 아이템: 배낭, 가구

### 권장 스택 개수
- 화폐: 1000개
- 소비품: 5-30개
- 재료: 20-50개
- 도구: 10-50개
- 희귀 아이템: 1-5개