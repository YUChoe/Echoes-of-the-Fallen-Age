# Telnet 클라이언트 테스트 가이드

## 개요

Python MUD 엔진의 Telnet CLI 클라이언트를 통해 게임을 테스트하는 방법을 설명합니다.

## 서버 시작

### 1. 서버 실행

```bash
# 가상환경 활성화 및 서버 시작
source mud_engine_env/Scripts/activate
PYTHONPATH=. python -m src.mud_engine.main
```

서버가 정상적으로 시작되면 다음 메시지가 표시됩니다:
```
📡 Telnet 서버가 telnet://0.0.0.0:4000 에서 실행 중입니다.
```

### 2. 서버 종료

```bash
# 실행 중인 서버 프로세스 확인
ps aux | grep python | grep mud_engine

# 프로세스 종료
kill -9 <PID>
```

## 테스트 계정

### 기본 테스트 계정

- **사용자명**: `player5426`
- **비밀번호**: `test1234`
- **권한**: 일반 사용자

### 계정 확인

```bash
# 가상환경 활성화
source mud_engine_env/Scripts/activate

# 플레이어 목록 확인
PYTHONPATH=. python scripts/check_players.py
```

### 새 계정 생성

```bash
# 가상환경 활성화
source mud_engine_env/Scripts/activate

# 테스트 계정 생성 스크립트 실행
PYTHONPATH=. python scripts/create_test_account.py
```

## Telnet 접속 방법

### 방법 1: Telnet 클라이언트 사용

```bash
# Windows (PowerShell)
telnet localhost 4000

# Linux/Mac
telnet localhost 4000
```

### 방법 2: Python 스크립트 사용

프로젝트 루트에 제공된 `test_telnet_combat.py` 스크립트를 사용:

```bash
source mud_engine_env/Scripts/activate
PYTHONPATH=. python test_telnet_combat.py
```

## 로그인 절차

### 1. 초기 화면

Telnet 접속 시 다음과 같은 환영 화면이 표시됩니다:

```
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║        Echoes of the Fallen Age                        ║
║                                                               ║
║        몰락의 대륙, 카르나스에 오신 것을 환영합니다        ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝

1. 로그인 (login)
2. 회원가입 (register)
3. 종료 (quit)

선택>
```

### 2. 로그인 선택

```
선택> 1
```

### 3. 사용자명 입력

```
=== 로그인 ===
사용자명: player5426
```

### 4. 비밀번호 입력

```
비밀번호: test1234
```

### 5. 로그인 완료

성공적으로 로그인하면 다음과 같은 메시지가 표시됩니다:

```
🏰 Town Square
============================================================
A bustling town square with a fountain in the center.

🚪 출구: north, east, west

✅ 'player5426'님, 환영합니다!
게임에 입장했습니다!
'help' 명령어로 도움말을 확인하세요.

>
```

## 기본 명령어

### 이동 명령어

```bash
# 방향으로 이동
north, south, east, west, up, down
n, s, e, w, u, d  # 단축 명령어

# 현재 위치 확인
look

# 출구 확인
exits
```

### 전투 명령어

```bash
# 몬스터 공격
attack <몬스터명>
attack goblin

# 전투 상태 확인
combat

# 방어
defend

# 도망
flee
```

### 정보 확인 명령어

```bash
# 능력치 확인
stats

# 인벤토리 확인
inventory
inv

# 도움말
help
```

### 시스템 명령어

```bash
# 게임 종료
quit
```

## 전투 테스트 절차

### 1. 전투 테스트 지역으로 이동

```bash
# Town Square에서 시작
> west          # West Gate로 이동
> west          # West Gate Outside로 이동
```

### 2. 몬스터 확인

```bash
> look

# 출력 예시:
👹 이곳에 있는 몬스터들:
  • Aggressive Goblin Alpha (레벨 1, HP: 100/100)
  • Aggressive Goblin Beta (레벨 1, HP: 100/100)
  • Aggressive Goblin Gamma (레벨 1, HP: 100/100)
```

### 3. 전투 시작

공격적인 몬스터가 있는 방에 입장하면 자동으로 전투가 시작됩니다.

```bash
> attack goblin

# 출력 예시:
✅ ⚔️ 공격적인 고블린 알파이(가) 전투에 참여했습니다!
```

### 4. 전투 상태 확인

```bash
> combat

# 출력 예시:
⚔️ 다중 전투 상태 (턴 1)
🎯 현재 턴: 공격적인 고블린 알파
⏱️ 상태: active

👤 player5426 (Initiative: 10):
   HP: 160/160 (100.0%)

👹 공격적인 고블린 알파 (Initiative: 14) 🎯:
   HP: 100/100 (100.0%)
```

### 5. 전투 진행

```bash
# 공격
> attack goblin

# 방어
> defend

# 도망
> flee
```

## 문제 해결

### 서버 연결 실패

```bash
# 서버가 실행 중인지 확인
ps aux | grep python | grep mud_engine

# 포트가 사용 중인지 확인
netstat -tulpn | grep 4000  # Linux
netstat -ano | findstr :4000  # Windows
```

### 로그인 실패

```bash
# 계정 확인
PYTHONPATH=. python scripts/check_players.py

# 데이터베이스 확인
sqlite3 data/mud_engine.db "SELECT username FROM players;"
```

### 전투 시작 안됨

- 공격적인 몬스터가 있는 방으로 이동했는지 확인
- `look` 명령어로 몬스터 존재 여부 확인
- 서버 로그에서 에러 메시지 확인

## 자동화 테스트

### Python 스크립트 사용

```bash
# 전투 테스트 스크립트 실행
source mud_engine_env/Scripts/activate
PYTHONPATH=. python test_telnet_combat.py
```

이 스크립트는 다음을 자동으로 수행합니다:
1. Telnet 서버 연결
2. 로그인 (player5426/test1234)
3. 전투 지역으로 이동
4. 몬스터 공격
5. 전투 상태 확인
6. 능력치 확인
7. 연결 종료

## 참고 문서

- [전투 시스템 가이드](combat_system_guide.md)
- [공격적 몬스터 테스트 가이드](aggressive_monster_test_guide.md)
- [전투 테스트 가이드](combat_test_guide.md)

## 주의사항

1. **서버 재시작**: 코드 변경 후에는 반드시 서버를 재시작해야 합니다.
2. **포트 충돌**: 4000번 포트가 이미 사용 중이면 서버가 시작되지 않습니다.
3. **데이터베이스**: 테스트 중 데이터베이스가 손상되면 백업에서 복원하거나 초기화가 필요합니다.
4. **인코딩**: Windows 환경에서는 UTF-8 인코딩 문제가 발생할 수 있습니다.

## 로그 확인

### 서버 로그

서버 실행 중 콘솔에 실시간으로 로그가 출력됩니다:

```
21:46:51.328 INFO [src.mud_engine.server.telnet_server:68] Telnet 서버가 성공적으로 시작되었습니다.
21:53:25.570 INFO [src.mud_engine.game.combat:450] 몬스터 goblin_test_1를 전투에 추가
```

### 로그 파일

로그 파일은 `logs/` 디렉토리에 저장됩니다:

```bash
# 최신 로그 확인
tail -f logs/mud_engine-*.log
```

## 테스트 체크리스트

- [ ] 서버 정상 시작
- [ ] Telnet 연결 성공
- [ ] 로그인 성공
- [ ] 기본 이동 명령어 작동
- [ ] 몬스터 확인 가능
- [ ] 전투 시작 성공
- [ ] 전투 상태 확인 가능
- [ ] 공격 명령어 작동
- [ ] 능력치 확인 가능
- [ ] 정상 종료 가능
