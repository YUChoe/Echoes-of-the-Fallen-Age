# 전투 시스템 가이드

## 개요

인스턴스 기반 턴제 전투 시스템이 구현되었습니다. 이 시스템은 다음과 같은 특징을 가지고 있습니다:

- **인스턴스 기반**: 각 전투는 독립적인 인스턴스로 관리됩니다
- **턴제 시스템**: 민첩(Agility) 기반으로 턴 순서가 결정됩니다
- **참가자 구분**: 전투 참가자와 비참가자가 명확히 구분됩니다
- **공격적 몬스터**: 특정 몬스터는 플레이어가 방에 입장하면 자동으로 전투를 시작합니다

## 핵심 컴포넌트

### 1. CombatInstance (전투 인스턴스)
- 전투 ID, 방 ID, 참가자 목록 관리
- 턴 순서 결정 및 관리
- 전투 로그 기록
- 전투 종료 조건 확인

### 2. Combatant (전투 참가자)
- 플레이어 또는 몬스터를 전투 참가자로 추상화
- 능력치: 민첩, HP, 공격력, 방어력
- 방어 상태 관리

### 3. CombatManager (전투 매니저)
- 전투 인스턴스 생성 및 관리
- 플레이어/몬스터를 전투에 추가/제거
- 전투 상태 조회
- 종료된 전투 정리

### 4. CombatHandler (전투 핸들러)
- 전투 시작 로직
- 플레이어/몬스터 행동 처리
- 전투 종료 처리

## 전투 흐름

### 1. 전투 시작
```
플레이어가 방 입장
  ↓
공격적인 몬스터 확인
  ↓
전투 인스턴스 생성
  ↓
플레이어와 몬스터를 참가자로 추가
  ↓
민첩 기반 턴 순서 결정
```

### 2. 턴 진행
```
현재 턴 참가자 확인
  ↓
행동 선택 (공격/방어/도망/대기)
  ↓
행동 실행
  ↓
전투 로그 기록
  ↓
다음 턴으로 진행
  ↓
전투 종료 조건 확인
```

### 3. 전투 종료
```
한쪽 전멸 확인
  ↓
승리자 결정
  ↓
전투 인스턴스 종료
  ↓
참가자 매핑 정리
```

## 전투 행동

### Attack (공격)
- 대상에게 데미지를 입힙니다
- 데미지 = 공격력 * (0.8 ~ 1.2 랜덤)
- 10% 확률로 크리티컬 (1.5배 데미지)
- 방어 중인 대상은 데미지 50% 감소

### Defend (방어)
- 방어 자세를 취합니다
- 다음 공격 데미지 50% 감소
- 턴이 지나면 방어 상태 해제

### Flee (도망)
- 50% 확률로 전투에서 탈출
- 실패 시 턴 소모

### Wait (대기)
- 아무 행동도 하지 않습니다
- 방어 상태 해제

## 몬스터 AI

현재 몬스터는 간단한 AI로 동작합니다:
- 생존한 플레이어 중 랜덤하게 선택하여 공격
- 향후 더 복잡한 AI 패턴 추가 가능

## 데이터 구조

### CombatInstance
```python
{
    'id': str,
    'room_id': str,
    'combatants': List[Combatant],
    'turn_order': List[str],  # combatant_id 순서
    'current_turn_index': int,
    'turn_number': int,
    'is_active': bool,
    'started_at': datetime,
    'ended_at': Optional[datetime]
}
```

### Combatant
```python
{
    'id': str,
    'name': str,
    'combatant_type': 'player' | 'monster',
    'agility': int,
    'max_hp': int,
    'current_hp': int,
    'attack_power': int,
    'defense': int,
    'is_defending': bool
}
```

## 사용 예시

### 전투 시작
```python
# 플레이어가 방에 입장할 때 자동으로 전투 시작
combat = await combat_handler.check_and_start_combat(
    room_id=room_id,
    player=player,
    player_id=player_id,
    monsters=monsters_in_room
)
```

### 플레이어 행동 처리
```python
result = await combat_handler.process_player_action(
    combat_id=combat_id,
    player_id=player_id,
    action=CombatAction.ATTACK,
    target_id=monster_id
)
```

### 몬스터 턴 처리
```python
result = await combat_handler.process_monster_turn(combat_id)
```

### 전투 상태 조회
```python
status = combat_handler.get_combat_status(combat_id)
```

## 향후 개선 사항

1. **다양한 행동 옵션**
   - 스킬 시스템
   - 아이템 사용
   - 특수 능력

2. **경험치 및 레벨업**
   - 전투 승리 시 경험치 획득
   - 레벨업 시스템

3. **전리품 드롭**
   - 몬스터 처치 시 아이템 드롭
   - 골드 획득

4. **전투 UI 개선**
   - Telnet CLI 전투 인터페이스
   - 실시간 전투 상태 표시

5. **성능 최적화**
   - 전투 인스턴스 메모리 관리
   - 대규모 전투 지원

## 테스트 방법

1. 서버 시작
2. 플레이어로 로그인
3. 공격적인 몬스터가 있는 방으로 이동
4. 자동으로 전투 시작
5. 전투 명령어 사용 (attack, defend, flee 등)

## 주의사항

- 전투 중인 플레이어는 다른 전투에 참가할 수 없습니다
- 전투가 종료되면 자동으로 인스턴스가 정리됩니다
- 몬스터 AI는 현재 간단한 랜덤 공격만 지원합니다
