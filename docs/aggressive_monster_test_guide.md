# 공격적 몬스터 시스템 테스트 가이드

## 개요
작업 23.5 "공격적 몬스터 시스템"이 구현되었습니다. 이 문서는 해당 기능을 테스트하는 방법을 설명합니다.

## 구현된 기능

### 1. 몬스터 공격적(Aggressive) 속성
- `MonsterType.AGGRESSIVE`: 선공형 몬스터 타입
- `MonsterType.PASSIVE`: 후공형 몬스터 타입  
- `MonsterType.NEUTRAL`: 중립형 몬스터 타입
- `Monster.is_aggressive()`: 선공형 몬스터 여부 확인 메서드

### 2. 방 입장 시 자동 전투 시작
- 플레이어가 선공형 몬스터가 있는 방에 입장하면 자동으로 전투 시작
- `PlayerMovementManager._check_aggressive_monsters_on_entry()` 메서드에서 처리
- 선공 메시지 브로드캐스트 후 전투 인스턴스 생성

### 3. 몬스터 전투 상태 관리
- `CombatHandler.is_monster_in_combat()`: 몬스터가 전투 중인지 확인
- 전투 중인 몬스터는 다른 플레이어를 공격하지 않음
- 전투가 끝나면 다시 선공 가능 상태로 복귀

## 테스트 시나리오

### 시나리오 1: 선공형 몬스터 자동 공격
1. 테스트 계정(aa / aaaabbbb)으로 로그인
2. 선공형 몬스터가 있는 방으로 이동 (예: forest_7_7)
3. **예상 결과**:
   - 방 입장 즉시 몬스터가 공격 메시지 출력
   - 전투 인스턴스 자동 생성
   - 전투 UI 표시

### 시나리오 2: 전투 중인 몬스터는 재공격 안함
1. 플레이어 A가 선공형 몬스터와 전투 중
2. 플레이어 B가 같은 방에 입장
3. **예상 결과**:
   - 플레이어 B는 자동 공격받지 않음
   - 기존 전투에 참여하거나 별도 행동 가능

### 시나리오 3: 후공형/중립형 몬스터는 선공 안함
1. 후공형(PASSIVE) 또는 중립형(NEUTRAL) 몬스터가 있는 방 입장
2. **예상 결과**:
   - 자동 공격 없음
   - 플레이어가 먼저 공격해야 전투 시작

## 테스트 명령어

### Telnet 접속
```bash
telnet localhost 4000
```

### 웹 브라우저 접속 (레거시)
```
http://localhost:8080
```

### 테스트용 명령어
- `goto forest_7_7`: 선공형 몬스터가 있는 방으로 이동
- `look`: 현재 방 정보 확인 (몬스터 목록 포함)
- `attack <몬스터이름>`: 몬스터 공격
- `combat`: 현재 전투 상태 확인

## 로그 확인

### 선공형 몬스터 체크 로그
```
INFO [player_movement_manager.py:xxx] 선공형 몬스터 체크 시작: 플레이어 aa, 방 forest_7_7
INFO [player_movement_manager.py:xxx] 선공형 몬스터 발견: Green Slime
INFO [player_movement_manager.py:xxx] 선공형 몬스터 Green Slime이 플레이어 aa을 공격!
```

### 전투 시작 로그
```
INFO [combat_handler.py:xxx] 전투 시작: 방 forest_7_7, 플레이어 player_id, 몬스터 2마리
INFO [combat.py:xxx] 전투 combat_id 턴 순서 결정: [player_id, monster_id_1, monster_id_2]
```

### 전투 중 몬스터 체크 로그
```
DEBUG [combat_handler.py:xxx] 방 forest_7_7에 공격 가능한 선공형 몬스터 없음
```

## 주의사항

1. **몬스터 템플릿 오류**: 현재 몬스터 템플릿이 없어서 스폰 포인트 설정 오류가 발생합니다. 이는 기존 문제이며 선공 시스템과는 무관합니다.

2. **테스트 데이터 생성**: 선공형 몬스터를 테스트하려면 먼저 몬스터를 생성해야 합니다:
   ```python
   # scripts/create_aggressive_monsters.py 실행 필요
   ```

3. **전투 종료**: 전투가 끝나면 몬스터는 다시 선공 가능 상태가 됩니다.

## 구현 파일

- `src/mud_engine/game/monster.py`: Monster 모델 및 MonsterType enum
- `src/mud_engine/game/combat_handler.py`: 전투 핸들러 (is_monster_in_combat 추가)
- `src/mud_engine/core/managers/player_movement_manager.py`: 플레이어 이동 시 선공 체크

## 다음 단계

작업 23.6 "전투 테스트 환경 구축"에서 실제 테스트 가능한 환경을 구성할 예정입니다:
- 서쪽 게이트 밖 지역 생성
- 공격적인 고블린 배치
- 자동 전투 시작 테스트
