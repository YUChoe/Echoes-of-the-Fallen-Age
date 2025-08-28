# 서버 개발 베스트 프랙티스

## Session 객체 사용 패턴

### 올바른 Session 접근법
```python
# ✅ 올바른 Session 사용법
if not session.player:
    return self.create_error_result("플레이어 정보를 찾을 수 없습니다.")

player_id = session.player.id
player_name = session.player.username
session_id = session.session_id
```

### 흔한 Session 실수들
```python
# ❌ 흔한 실수들 (속성이 존재하지 않음)
session.player_id        # 속성 없음
session.character_name   # 속성 없음
session.player_name      # 속성 없음
session.character_id     # 속성 없음
```

## 서버-클라이언트 통신

### 메시지 전송 패턴
```python
# 개별 메시지 전송
await session.send_message({
    "type": "room_info",
    "message": "내용"
})

# 성공 응답
await session.send_success({
    "action": "login_success",
    "data": player_data
})

# 에러 응답
await session.send_error("에러 메시지")
```

### 브로드캐스트 메시지
```python
# ✅ 올바른 브로드캐스트 형식
await game_engine.broadcast_to_room(
    room_id,
    {"type": "room_message", "message": "내용"},
    exclude_session=session.session_id  # exclude_session_id 아님
)

# ❌ 잘못된 사용법
await game_engine.broadcast_to_room(
    room_id,
    "메시지 문자열",  # 딕셔너리가 아님
    exclude_session_id=session.session_id  # 잘못된 매개변수명
)
```

## 데이터베이스 작업

### 모델과 스키마 일치
```python
# ❌ 잘못된 가정 (코드 모델과 DB 스키마 불일치)
"name": {"en": "Gate", "ko": "성문"}

# ✅ 실제 DB 스키마에 맞춤
"name_en": "Gate"
"name_ko": "성문"
```

### 안전한 데이터 생성
```python
# ✅ 멱등성 보장 (중복 생성 방지)
existing = await repo.get_by_id(item_id)
if existing:
    print(f"{item_id} 이미 존재")
    return
await repo.create(item_data)
```

### 데이터 검증 패턴
```python
# 타입 안전성 확보
exits = town_square.exits if isinstance(town_square.exits, dict) else json.loads(town_square.exits)

# 필수 데이터 존재 여부 확인
if not session.player:
    return self.create_error_result("플레이어 정보가 필요합니다.")
```

## 모듈 Import 패턴

### 올바른 Import 경로
```python
# ✅ 실제 구조 확인 후 사용
from src.mud_engine.game.models import Room, Player
from src.mud_engine.game.repositories import RoomRepository, GameObjectRepository
from src.mud_engine.database.connection import DatabaseManager

# ❌ 추측으로 작성 (존재하지 않는 경로)
from src.mud_engine.models.room import Room
from src.mud_engine.database.db_manager import DatabaseManager
```

## 명령어 시스템

### 새로운 명령어 구현 시 체크리스트
- [ ] 기존 명령어들의 Session 사용 패턴 확인
- [ ] `session.player` 존재 여부 먼저 확인
- [ ] 브로드캐스트 메서드 시그니처 정확히 사용
- [ ] 게임 엔진 접근 방식 기존 패턴 준수

### 명령어 처리 패턴
```python
async def execute(self, session, game_engine, args):
    # 1. 세션 검증
    if not session.player:
        return self.create_error_result("로그인이 필요합니다.")

    # 2. 인벤토리 조회 (기존 패턴 준수)
    inventory = await game_engine.world_manager.get_inventory_objects(session.player.id)

    # 3. 비즈니스 로직 처리
    # ...

    # 4. 응답 전송
    await session.send_success({"message": "처리 완료"})

    # 5. 필요시 브로드캐스트
    await game_engine.broadcast_to_room(
        session.current_room_id,
        {"type": "room_message", "message": f"{session.player.username}이(가) 행동했습니다."},
        exclude_session=session.session_id
    )
```

## 로깅 및 디버깅

### 서버 측 로깅
```python
# Session 구조 확인
logger.debug(f"Session attributes: {dir(session)}")
logger.debug(f"Player: {session.player}")

# 데이터 구조 확인
logger.debug(f"Received data: {data}")
logger.debug(f"Room exits: {room.exits}")
```

### 에러 처리 패턴
```python
try:
    # 비즈니스 로직
    result = await some_operation()
    return self.create_success_result(result)
except Exception as e:
    logger.error(f"작업 실패: {e}")
    return self.create_error_result("작업을 완료할 수 없습니다.")
```

## API 설계 원칙

### 응답 일관성
```python
# 성공 응답 형식 통일
{
    "status": "success",
    "data": {
        "action": "specific_action",
        "message": "처리 완료",
        "data": actual_data
    }
}

# 에러 응답 형식 통일
{
    "status": "error",
    "message": "구체적인 에러 메시지"
}
```

### 하위 호환성 고려
```python
# API 변경 시 기존 클라이언트 고려
def send_response(self, data):
    # 새로운 형식
    response = {"status": "success", "data": data}

    # 하위 호환성을 위한 필드 추가
    if "action" in data:
        response["action"] = data["action"]  # 기존 클라이언트용

    return response
```

## 데이터 작업 체크리스트

### 스크립트/모델 작성 시
- [ ] 데이터베이스 스키마 확인 (`PRAGMA table_info`)
- [ ] 기존 데이터 존재 여부 확인
- [ ] 타입 안전성 확보 (`isinstance` 사용)
- [ ] 예외 처리 및 로깅 추가
- [ ] 멱등성 보장 (중복 생성 방지)

### API 변경 시
- [ ] 서버-클라이언트 양쪽 동시 수정 계획
- [ ] 하위 호환성 고려
- [ ] 메시지 형식 일관성 유지
- [ ] 변경 영향 범위 분석
- [ ] 공통 함수 변경 시 모든 사용처 확인

## 성능 고려사항

### 데이터베이스 최적화
- SQLite 제약사항 고려한 쿼리 작성
- 대량 데이터 처리 시 배치 처리 고려
- 트랜잭션 적절히 활용

### 메모리 관리
- 세션 데이터 적절한 정리
- 대용량 응답 데이터 스트리밍 고려
- 불필요한 객체 참조 해제