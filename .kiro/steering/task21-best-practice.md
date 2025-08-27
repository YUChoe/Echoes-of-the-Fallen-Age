# Task 21 Best Practice - NPC 상호작용 시스템 구현

## 발생한 주요 실수들과 해결책

### 1. Session 객체 속성 불일치 문제 (가장 심각한 실수)

**실수 1**: `session.player_id` 속성 사용 시도

- `src/mud_engine/game/models.py`의 `Session` 모델과 `src/mud_engine/server/session.py`의 `Session` 클래스가 서로 다른 구조
- 실제 서버 Session에는 `player_id` 속성이 없음

**에러 로그**:

```
'Session' object has no attribute 'player_id'
```

**실수 2**: `session.player_name` 속성 사용 시도

- 서버 Session에는 `player_name` 속성도 없음

**에러 로그**:

```
'Session' object has no attribute 'player_name'
```

**실수 3**: `session.character_id` 속성 사용 시도

- 서버 Session에는 `character_id` 속성도 없음

**에러 로그**:

```
'Session' object has no attribute 'character_id'
```

**실수 4**: `session.character_name` 속성 사용 시도

- 서버 Session에는 `character_name` 속성도 없음

**에러 로그**:

```
'Session' object has no attribute 'character_name'
```

**해결책**:

- 실제 서버 Session 클래스 구조 확인: `session.player` 객체 사용
- 플레이어 정보는 `session.player`에서 직접 가져옴
- 인벤토리 조회는 `session.player.id` 사용
- 브로드캐스트 메시지는 `session.player.username` 사용
- 세션 ID는 `session.session_id` 사용

**Best Practice**:

```python
# ❌ 잘못된 방법들
player = await game_engine.model_manager.players.get_by_id(session.player_id)
players = await game_engine.model_manager.players.find_by(username=session.player_name)
inventory = await game_engine.model_manager.game_objects.get_objects_in_inventory(session.character_id)
message = f"{session.character_name}이(가) 구매했습니다."

# ✅ 올바른 방법
if not session.player:
    return self.create_error_result("플레이어 정보를 찾을 수 없습니다.")
player = session.player
inventory = await game_engine.world_manager.get_inventory_objects(session.player.id)
message = f"{session.player.username}이(가) 구매했습니다."
```

### 2. 기존 코드 패턴 미준수

**실수**:

- 다른 명령어들이 사용하는 패턴을 확인하지 않고 새로운 방식으로 구현
- 인벤토리 조회 방식이 다른 명령어와 불일치

**해결책**:

- 기존 `object_commands.py`의 패턴 분석
- `game_engine.world_manager.get_inventory_objects(session.player.id)` 사용
- 일관된 데이터 접근 방식 적용

**Best Practice**:

```python
# ✅ 기존 패턴과 일치하는 방법
inventory_objects = await game_engine.world_manager.get_inventory_objects(session.player.id)
```

### 3. 코드 작성 전 구조 분석 부족

**실수**:

- 새로운 기능 구현 전에 기존 코드베이스의 구조를 충분히 분석하지 않음
- 다른 명령어들이 어떻게 플레이어 정보를 조회하는지 확인하지 않음

**해결책**:

- 새로운 기능 구현 전에 기존 명령어들의 패턴 분석
- 유사한 기능을 가진 기존 코드 참조
- 데이터 모델과 실제 사용되는 객체 구조 확인

**Best Practice**:

1. 기존 명령어 파일들을 먼저 검토
2. Session 객체 사용 패턴 파악
3. 데이터베이스 접근 방식 확인
4. 일관된 패턴으로 구현

### 4. 단계별 테스트 부족

**실수**:

- 명령어 구현 후 실제 테스트 없이 완료로 판단
- 각 단계별 에러를 수정하면서 새로운 에러 발생

**해결책**:

- 구현 완료 후 즉시 기본 시나리오 테스트
- 각 에러 수정 후 재테스트
- 로그 모니터링을 통한 실시간 디버깅

**Best Practice**:

1. 구현 → 즉시 테스트 → 수정 → 재테스트 사이클
2. 성공 케이스와 실패 케이스 모두 테스트
3. 서버 로그 실시간 모니터링

### 5. 에러 메시지 분석 미흡

**실수**:

- 에러 메시지를 정확히 분석하지 않고 추측으로 수정
- 한 번에 여러 속성을 수정하여 어떤 수정이 효과적인지 파악 어려움

**해결책**:

- 에러 메시지를 정확히 읽고 해당 속성이 실제로 존재하는지 확인
- 한 번에 하나씩 수정하여 각 수정의 효과 확인
- `grepSearch`를 활용하여 기존 코드에서 올바른 사용법 찾기

### 6. 브로드캐스트 메서드 사용법 오류

**실수 1**: `broadcast_to_room` 매개변수 이름 오류

- `exclude_session_id` 사용했지만 실제로는 `exclude_session` 매개변수명

**에러 로그**:

```
GameEngine.broadcast_to_room() got an unexpected keyword argument 'exclude_session_id'
```

**실수 2**: 브로드캐스트 메시지 형식 오류

- 문자열을 직접 전달했지만 딕셔너리 형태가 필요
- 메서드 시그니처: `broadcast_to_room(room_id: str, message: Dict[str, Any], exclude_session: Optional[str] = None)`

**해결책**:

- 실제 메서드 시그니처 확인: `grepSearch "def broadcast_to_room"`
- 기존 사용 예시 확인: `grepSearch "await.*broadcast_to_room"`
- 올바른 형식으로 수정

**Best Practice**:

```python
# ❌ 잘못된 방법
await game_engine.broadcast_to_room(
    session.current_room_id,
    f"{session.player.username}이(가) 구매했습니다.",
    exclude_session_id=session.session_id
)

# ✅ 올바른 방법
await game_engine.broadcast_to_room(
    session.current_room_id,
    {
        "type": "room_message",
        "message": f"{session.player.username}이(가) 구매했습니다."
    },
    exclude_session=session.session_id
)
```

## 개선된 개발 프로세스

### 1. 사전 분석 단계

- [ ] 기존 코드베이스 구조 분석
- [ ] 유사 기능 구현 방식 조사
- [ ] 실제 사용되는 객체 구조 확인 (Session, Player 등)
- [ ] 의존성 및 연동 방식 파악

### 2. 구현 단계

- [ ] 기존 패턴을 따르는 일관된 구현
- [ ] 에러 처리 및 예외 상황 고려
- [ ] 로깅 및 디버깅 정보 추가

### 3. 테스트 단계

- [ ] 기본 시나리오 테스트
- [ ] 에러 케이스 테스트
- [ ] 로그 모니터링
- [ ] 각 수정 사항별 개별 테스트

### 4. 검증 단계

- [ ] 전체 기능 통합 테스트
- [ ] 성능 및 안정성 확인
- [ ] 사용자 시나리오 검증

## 핵심 체크리스트

### 새로운 명령어 구현 시

- [ ] 기존 명령어들의 Session 객체 사용 방식 확인
- [ ] 플레이어/캐릭터 정보 조회 방식 통일
- [ ] 에러 처리 및 메시지 일관성 유지
- [ ] 게임 엔진 접근 방식 확인
- [ ] 브로드캐스트 메서드 시그니처 및 사용법 확인

### Session 객체 사용 시

- [ ] `session.player` 객체 존재 여부 확인
- [ ] `session.player.id`로 플레이어 ID 접근
- [ ] `session.player.username`으로 플레이어 이름 접근
- [ ] `session.session_id`로 세션 ID 접근

### 데이터베이스 관련 작업 시

- [ ] 모델 클래스와 실제 테이블 스키마 일치 확인
- [ ] 기존 명령어와 동일한 데이터 접근 방식 사용
- [ ] 인벤토리 조회는 `world_manager.get_inventory_objects()` 사용

### 브로드캐스트 메시지 사용 시

- [ ] `broadcast_to_room` 메서드 시그니처 확인
- [ ] 매개변수명: `exclude_session` (not `exclude_session_id`)
- [ ] 메시지 형식: 딕셔너리 `{"type": "room_message", "message": "..."}`
- [ ] 기존 사용 예시 참조하여 올바른 형식 적용

## 디버깅 팁

### 1. Session 객체 관련 오류

```python
# Session 객체 구조 확인
logger.debug(f"Session attributes: {dir(session)}")
logger.debug(f"Session player: {session.player}")
logger.debug(f"Player attributes: {dir(session.player) if session.player else 'None'}")
```

### 2. 기존 코드 패턴 확인

```bash
# 다른 명령어에서 Session 사용 방식 검색
grepSearch "session\.player" --includePattern="src/mud_engine/commands/*.py"

# 인벤토리 조회 방식 검색
grepSearch "get_inventory_objects" --includePattern="src/mud_engine/commands/*.py"

# 브로드캐스트 메서드 시그니처 확인
grepSearch "def broadcast_to_room" --includePattern="src/mud_engine/**/*.py"

# 브로드캐스트 사용 예시 확인
grepSearch "await.*broadcast_to_room" --includePattern="src/mud_engine/**/*.py"
```

### 3. 에러 발생 시 단계별 접근

1. 에러 메시지 정확히 읽기
2. 해당 속성/매개변수가 실제로 존재하는지 확인
3. 기존 코드에서 올바른 사용법 찾기
4. 한 번에 하나씩 수정하여 테스트
5. 메서드 시그니처와 실제 사용법 비교

## 결론

이번 Task 21에서 가장 큰 교훈은 **실제 사용되는 객체 구조와 메서드 시그니처를 정확히 파악하는 것**의 중요성입니다. 특히:

### 핵심 교훈들:

1. **Session 객체 구조**: `session.player` 객체를 통해 플레이어 정보에 접근
2. **메서드 시그니처 확인**: `broadcast_to_room`의 정확한 매개변수명과 메시지 형식
3. **기존 패턴 준수**: 다른 명령어들과 일관된 데이터 접근 방식 사용
4. **단계별 디버깅**: 한 번에 하나씩 수정하여 각 변경사항의 효과 확인

### 개발 프로세스 개선:

1. **사전 분석**: 새로운 기능 구현 전에 반드시 기존 코드 분석 먼저 수행
2. **정확한 에러 분석**: 에러 메시지를 정확히 읽고 해당 구조/시그니처 확인
3. **즉시 테스트**: 구현 후에는 즉시 테스트를 통해 검증
4. **일관성 유지**: 기존 패턴과 일관성을 유지하는 습관
5. **문서화**: 실수와 해결책을 문서화하여 재발 방지

### 기억해야 할 핵심 사항:

- **Session 객체**: `session.player`를 통해 플레이어 정보 접근
- **브로드캐스트**: `exclude_session` 매개변수와 딕셔너리 메시지 형식 사용
- **인벤토리**: `world_manager.get_inventory_objects(session.player.id)` 사용
- **에러 해결**: `grepSearch`를 활용하여 기존 사용법 확인
