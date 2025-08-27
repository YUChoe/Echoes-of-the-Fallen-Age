# 태스크 20-1 Follow 기능 방 정보 자동 갱신 - 베스트 프랙티스

## 실수 분석 및 교훈

### 1. 문제 파악 단계에서의 실수

**실수**: 초기에 follow 관련 코드를 찾기 위해 잘못된 검색 패턴 사용

```bash
# ❌ 잘못된 검색 방법
grepSearch "follow.*command"  # 결과 없음
grepSearch "follow"           # 결과 없음
grepSearch "Follow"           # 결과 없음
```

**해결**:

```bash
# ✅ 올바른 검색 방법
grepSearch "follow" --includePattern="*.py"  # 파일 타입 지정
# 또는 특정 파일에서 검색
grepSearch "follow" --includePattern="src/mud_engine/commands/interaction_commands.py"
```

**교훈**:

- 코드 검색 시 파일 타입을 명시적으로 지정할 것
- 검색어가 없을 때는 관련 파일을 직접 확인할 것
- 프로젝트 구조를 먼저 파악한 후 검색할 것

### 2. 코드 구조 이해 부족

**실수**: PlayerMovementManager의 위치를 잘못 파악

```python
# ❌ 잘못된 경로 추정
src/mud_engine/core/managers.py  # 존재하지 않음
```

**해결**:

```python
# ✅ 실제 경로 확인
src/mud_engine/core/managers/player_movement_manager.py
```

**교훈**:

- 파일 구조를 가정하지 말고 `listDirectory`로 실제 구조 확인
- 모듈 import 오류 시 실제 파일 위치부터 확인
- 프로젝트가 리팩토링되었을 가능성 고려

### 3. 기존 메서드 존재 여부 미확인

**실수**: Session 클래스에 `send_ui_update` 메서드가 이미 있는지 확인하지 않고 추가하려 함

```python
# 이미 존재하는 메서드를 다시 만들려고 시도
async def send_ui_update(self, ui_data: Dict[str, Any]) -> bool:
```

**해결**:

- 파일을 끝까지 읽어서 기존 메서드 확인
- 메서드 추가 전 `grepSearch`로 존재 여부 확인

**교훈**:

- 새 메서드 추가 전 기존 코드에서 동일한 기능이 있는지 확인
- 파일을 부분적으로 읽지 말고 전체 구조 파악
- 중복 구현 방지를 위한 사전 조사 필수

### 4. 프로세스 관리 명령어 혼동

**실수**: gitbash 환경에서 Windows CMD 명령어 사용 시도

```bash
# ❌ gitbash에서 Windows CMD 명령어 사용
netstat -ano | findstr :8080  # Windows CMD 명령어
tasklist | findstr python     # Windows CMD 명령어
```

**해결**:

```bash
# ✅ gitbash에서 올바른 명령어 사용
ps aux | grep python  # bash 명령어
kill -9 <PID>         # bash 명령어
```

**교훈**:

- gitbash 환경에서는 bash 명령어만 사용할 것
- Windows CMD 명령어와 bash 명령어 구분 필수
- dev-environment.md의 "gitbash 사용" 원칙 준수
- 환경에 맞지 않는 명령어 사용 시 즉시 중단하고 올바른 명령어 사용

## 올바른 개발 프로세스

### 1. 문제 분석 단계

```bash
# 1단계: 프로젝트 구조 파악
listDirectory "src/mud_engine" --depth=2

# 2단계: 관련 기능 검색
grepSearch "follow" --includePattern="*.py"

# 3단계: 핵심 파일 식별 및 읽기
readFile "src/mud_engine/commands/interaction_commands.py"
```

### 2. 코드 수정 전 확인사항

```python
# 기존 메서드 존재 여부 확인
grepSearch "send_ui_update" --includePattern="*.py"

# 관련 클래스 구조 파악
readFile "src/mud_engine/server/session.py"

# 의존성 체인 확인
grepSearch "PlayerMovementManager" --includePattern="*.py"
```

### 3. 단계별 구현 접근법

1. **문제 정확한 파악**: 로그 분석으로 현재 동작 확인
2. **기존 코드 구조 이해**: 관련 클래스와 메서드 파악
3. **최소한의 수정**: 기존 구조를 최대한 활용
4. **점진적 구현**: 서버 → 클라이언트 순서로 수정
5. **즉시 테스트**: 각 단계마다 동작 확인

### 4. 클라이언트-서버 통신 패턴

```javascript
// 서버에서 새로운 메시지 타입 추가 시
// 1. 서버에서 메시지 전송
await session.send_message({
    "type": "room_info",
    "room": room_data
});

// 2. 클라이언트 MessageHandler에 케이스 추가
case 'room_info':
    this.client.gameModule.handleRoomInfo(data);
    break;

// 3. GameModule에 핸들러 메서드 추가
handleRoomInfo(data) {
    // 처리 로직
}
```

## 권장 개발 패턴

### 1. 기능 확장 시 체크리스트

- [ ] 기존 코드에서 유사한 기능 검색
- [ ] 관련 클래스와 메서드 구조 파악
- [ ] 최소한의 수정으로 목표 달성 가능한지 확인
- [ ] 서버-클라이언트 메시지 프로토콜 일관성 확인
- [ ] 기존 메서드 재사용 가능성 검토

### 2. 코드 검색 전략

```bash
# 기능별 검색
grepSearch "follow" --includePattern="*.py"

# 클래스별 검색
grepSearch "PlayerMovementManager" --includePattern="*.py"

# 메서드별 검색
grepSearch "send_ui_update" --includePattern="*.py"

# 메시지 타입별 검색
grepSearch "room_info" --includePattern="*.js"
```

### 3. 파일 구조 탐색 패턴

```bash
# 1. 전체 구조 파악
listDirectory "src/mud_engine" --depth=2

# 2. 특정 모듈 상세 확인
listDirectory "src/mud_engine/core/managers"

# 3. 관련 파일 읽기
readFile "src/mud_engine/core/managers/player_movement_manager.py"
```

### 4. 메서드 추가 시 안전한 접근법

```python
# 1. 기존 메서드 확인
grepSearch "method_name" --includePattern="target_file.py"

# 2. 클래스 전체 구조 파악
readFile "target_file.py"

# 3. 적절한 위치에 메서드 추가
# 4. 기존 코드와의 일관성 확인
```

## 환경별 주의사항

### gitbash 환경에서의 프로세스 관리

```bash
# ✅ 올바른 방법 (dev-environment.md 준수)
# 프로세스 확인
ps aux | grep python  # bash 명령어

# 프로세스 종료
kill -9 <PID>  # bash 명령어

# ❌ 잘못된 방법 (Windows CMD 명령어를 gitbash에서 사용)
netstat -ano | findstr :8080  # 작동하지 않음
tasklist | findstr python     # 작동하지 않음
```

### 가상환경 및 실행 패턴

```bash
# ✅ 표준 실행 패턴
source mud_engine_env/Scripts/activate && PYTHONPATH=. python -m src.mud_engine.main
```

## 결론

이번 태스크에서 가장 중요한 교훈은:

1. **기존 코드 구조 충분히 파악**: 수정 전 관련 코드 전체 이해
2. **최소한의 수정 원칙**: 기존 구조 최대한 활용
3. **단계별 검증**: 각 수정사항을 즉시 테스트
4. **환경별 명령어 준수**: Steering 파일 가이드라인 우선 참조
5. **중복 구현 방지**: 기존 메서드 존재 여부 사전 확인

특히 follow 기능처럼 기존 시스템에 새로운 동작을 추가할 때는 기존 메시지 흐름을 이해하고, 최소한의 수정으로 목표를 달성하는 것이 핵심입니다.
