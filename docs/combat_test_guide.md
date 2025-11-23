# 전투 테스트 가이드

## 개요

이 문서는 전투 시스템 테스트를 위한 가이드입니다. 서쪽 게이트 밖에 공격적인 고블린들이 배치된 테스트 지역이 생성되어 있으며, 플레이어가 해당 지역에 입장하면 자동으로 전투가 시작됩니다.

## 테스트 환경 구성

### 1. 테스트 지역 생성

스크립트를 실행하여 테스트 환경을 구축합니다:

```bash
source mud_engine_env/Scripts/activate && PYTHONPATH=. python scripts/create_combat_test_area.py
```

이 스크립트는 다음을 수행합니다:
- 서쪽 게이트 밖에 "고블린 매복 지점" (test_combat_area) 생성
- 서쪽 성문에서 테스트 지역으로 가는 출구 추가
- 3마리의 공격적인 고블린 배치 (goblin_test_1, goblin_test_2, goblin_test_3)

### 2. 서버 시작

```bash
source mud_engine_env/Scripts/activate && PYTHONPATH=. python -m src.mud_engine.main
```

## 테스트 절차

### 1. Telnet 접속

```bash
telnet localhost 4000
```

또는 Windows에서:
```bash
telnet 127.0.0.1 4000
```

### 2. 로그인

테스트 계정으로 로그인합니다:
- 사용자명: `aa`
- 비밀번호: `aaaabbbb`

### 3. 테스트 지역으로 이동

```
west        # 마을 광장 → 서쪽 성문
west        # 서쪽 성문 → 고블린 매복 지점
```

### 4. 자동 전투 시작 확인

테스트 지역(test_combat_area)에 입장하면:
- 공격적인 고블린들이 자동으로 전투를 시작합니다
- 전투 인스턴스가 생성됩니다
- 턴제 전투가 시작됩니다

## 테스트 항목

### 1. 자동 전투 시작

- [ ] 테스트 지역 입장 시 전투가 자동으로 시작되는가?
- [ ] 전투 시작 메시지가 표시되는가?
- [ ] 몬스터 정보가 올바르게 표시되는가?

### 2. 전투 인스턴스 관리

- [ ] 전투 인스턴스가 정상적으로 생성되는가?
- [ ] 참가자 구분이 올바르게 되는가? (전투 참가/비참가)
- [ ] 턴 순서가 민첩 수치 기반으로 결정되는가?

### 3. 전투 명령어

다음 명령어들을 테스트합니다:

```
attack      # 공격
defend      # 방어
flee        # 도망
combat      # 전투 상태 확인
```

- [ ] `attack` 명령어가 정상 작동하는가?
- [ ] `defend` 명령어가 정상 작동하는가?
- [ ] `flee` 명령어가 정상 작동하는가?
- [ ] `combat` 명령어로 전투 상태를 확인할 수 있는가?

### 4. 전투 종료

- [ ] 몬스터를 처치하면 전투가 종료되는가?
- [ ] 도망에 성공하면 전투가 종료되는가?
- [ ] 플레이어가 사망하면 전투가 종료되는가?
- [ ] 전투 종료 후 정상적으로 이동할 수 있는가?

### 5. 다중 몬스터 전투

- [ ] 여러 마리의 몬스터와 동시에 전투할 수 있는가?
- [ ] 각 몬스터의 턴이 올바르게 처리되는가?
- [ ] 한 마리를 처치한 후 다른 몬스터와 계속 전투할 수 있는가?

## 테스트 지역 정보

### 고블린 매복 지점 (test_combat_area)

**위치**: 서쪽 성문 바로 밖

**설명**:
- 영어: "A dangerous clearing just outside the west gate. The ground is littered with bones and broken weapons. Several aggressive goblins lurk here, ready to attack any intruders."
- 한국어: "서쪽 성문 바로 밖의 위험한 공터입니다. 땅에는 뼈와 부서진 무기들이 흩어져 있습니다. 여러 마리의 공격적인 고블린들이 이곳에 숨어 있으며, 침입자를 공격할 준비가 되어 있습니다."

**출구**:
- east: room_gate_west (서쪽 성문으로 돌아가기)

### 공격적인 고블린 정보

**goblin_test_1 (알파)**
- 이름: Aggressive Goblin Alpha / 공격적인 고블린 알파
- 타입: AGGRESSIVE (선공형)
- 행동: STATIONARY (고정형)
- 능력치:
  - HP: 100/100
  - 공격력: 18
  - 방어력: 6
  - 속도: 14
  - 명중률: 78%
  - 크리티컬 확률: 10%
- 보상:
  - 경험치: 60
  - 골드: 15
  - 드롭 아이템: 고블린 발톱, 녹슨 단검, 구리 동전

**goblin_test_2 (베타)**, **goblin_test_3 (감마)**
- 알파와 동일한 능력치

## 예상 동작

### 1. 입장 시

```
You enter the Goblin Ambush Point.
A dangerous clearing just outside the west gate...

Aggressive Goblin Alpha spots you and attacks!
Combat has started!

Turn order:
1. Aggressive Goblin Alpha (Speed: 14)
2. You (Speed: 10)
3. Aggressive Goblin Beta (Speed: 14)
4. Aggressive Goblin Gamma (Speed: 14)

It's Aggressive Goblin Alpha's turn!
Aggressive Goblin Alpha attacks you for 12 damage!

It's your turn! What will you do?
> 
```

### 2. 공격 시

```
> attack
You attack Aggressive Goblin Alpha for 15 damage!
Aggressive Goblin Alpha: 85/100 HP

It's Aggressive Goblin Beta's turn!
...
```

### 3. 도망 시

```
> flee
You attempt to flee from combat!
You successfully escaped!
You are now in West Gate.
```

## 문제 해결

### 전투가 시작되지 않는 경우

1. 몬스터가 올바르게 배치되었는지 확인:
```bash
source mud_engine_env/Scripts/activate && PYTHONPATH=. python -c "
import asyncio
from src.mud_engine.database.connection import DatabaseManager
from src.mud_engine.game.repositories import MonsterRepository

async def check():
    db = DatabaseManager()
    await db.initialize()
    repo = MonsterRepository(db)
    for i in range(1, 4):
        monster = await repo.get_by_id(f'goblin_test_{i}')
        if monster:
            print(f'✓ {monster.id}: {monster.name} at {monster.current_room_id}')
        else:
            print(f'✗ goblin_test_{i} not found')
    await db.close()

asyncio.run(check())
"
```

2. 서버 로그 확인:
```bash
tail -f logs/mud_engine-*.log
```

### 전투 명령어가 작동하지 않는 경우

1. 전투 상태 확인:
```
combat
```

2. 사용 가능한 명령어 확인:
```
help
```

## 추가 테스트 시나리오

### 시나리오 1: 단일 몬스터 전투

1. 테스트 지역에 입장
2. 한 마리의 고블린만 공격
3. 처치 후 전투 종료 확인

### 시나리오 2: 다중 몬스터 전투

1. 테스트 지역에 입장
2. 여러 마리의 고블린과 동시 전투
3. 순차적으로 처치하며 전투 진행

### 시나리오 3: 도망 테스트

1. 테스트 지역에 입장
2. 전투 시작 후 즉시 도망
3. 성공적으로 탈출 확인

### 시나리오 4: 재입장 테스트

1. 테스트 지역에 입장하여 전투
2. 도망으로 탈출
3. 다시 입장하여 전투 재시작 확인

## 정리

테스트 완료 후:

1. 서버 종료: Ctrl+C
2. 테스트 데이터 정리 (선택사항):
```bash
# 테스트 고블린 삭제
source mud_engine_env/Scripts/activate && PYTHONPATH=. python -c "
import asyncio
from src.mud_engine.database.connection import DatabaseManager
from src.mud_engine.game.repositories import MonsterRepository

async def cleanup():
    db = DatabaseManager()
    await db.initialize()
    repo = MonsterRepository(db)
    for i in range(1, 4):
        await repo.delete(f'goblin_test_{i}')
        print(f'Deleted goblin_test_{i}')
    await db.close()

asyncio.run(cleanup())
"
```

## 참고 문서

- [전투 시스템 가이드](combat_system_guide.md)
- [공격적 몬스터 테스트 가이드](aggressive_monster_test_guide.md)
