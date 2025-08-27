# 서버 개발 베스트 프랙티스

## 핵심 원칙
- **타입 안전성**: enum, 타입 힌트 적극 활용
- **의존성 주입**: 모든 의존성을 명시적으로 주입
- **방어적 프로그래밍**: 타입과 존재 여부 항상 확인
- **충분한 로깅**: 디버깅에 필요한 모든 정보 기록

## 주요 실수 패턴

### 1. 타입 불일치 오류
```python
# ❌ 잘못된 방법
base_strength = self.stats.get_primary_stat('strength')

# ✅ 올바른 방법
from .stats import StatType
base_strength = self.stats.get_primary_stat(StatType.STR)
```

### 2. 데이터베이스 저장 로직 불일치
```python
# ❌ 잘못된 방법
created_room = await self._room_repo.create(room)

# ✅ 올바른 방법
created_room = await self._room_repo.create(room.to_dict())
```

### 3. 의존성 주입 누락
```python
# ❌ 잘못된 방법
server = MudServer(host, port, player_manager)

# ✅ 올바른 방법
server = MudServer(host, port, player_manager, db_manager)
```

### 4. 속성 존재 확인 누락
```python
# ❌ 잘못된 방법
self.chat_manager.subscribe_to_channel(player.id, "ooc")

# ✅ 올바른 방법
if hasattr(self, 'chat_manager') and self.chat_manager:
    self.chat_manager.subscribe_to_channel(player.id, "ooc")
```

## 권장 개발 패턴

### 1. 계층별 책임 분리
```python
# Controller Layer - 입력 검증만
async def execute_admin(self, session: Session, args: List[str]) -> CommandResult:
    pass

# Service Layer - 비즈니스 로직
async def create_room_realtime(self, room_data: Dict[str, Any]) -> bool:
    pass

# Repository Layer - 데이터 접근만
async def create(self, data: Dict[str, Any]) -> Model:
    pass
```

### 2. 포괄적 오류 처리
```python
def execute_command(self, session, args):
    try:
        result = self.process_command(session, args)
        logger.debug(f"명령어 실행 성공: {result}")
        return result
    except SpecificException as e:
        logger.error(f"특정 오류: {e}", exc_info=True)
        return self.create_error_result("특정 오류 메시지")
    except Exception as e:
        logger.error(f"예상치 못한 오류: {e}", exc_info=True)
        return self.create_error_result("일반 오류 메시지")
```

### 3. 상태 변화 추적
```python
async def move_player_to_room(self, session, room_id, skip_followers=False):
    old_room_id = getattr(session, 'current_room_id', None)  # 이전 상태 보존
    session.current_room_id = room_id  # 상태 변경

    if not skip_followers and old_room_id:
        await self.handle_followers(session, room_id, old_room_id)
```

### 4. 재귀 방지
```python
async def recursive_method(self, data, prevent_recursion=False):
    process_data(data)

    if not prevent_recursion:
        for related_data in get_related_data(data):
            await self.recursive_method(related_data, prevent_recursion=True)
```

## 체크리스트

### 구현 전
- [ ] 의존성 체인 전체 매핑
- [ ] Repository 인터페이스 확인
- [ ] 타입 힌트 및 enum 사용법 확인
- [ ] 이벤트 데이터 스키마 설계

### 구현 중
- [ ] enum 타입 메서드에는 enum 값 전달
- [ ] 각 메서드의 입출력 타입 일치성 확인
- [ ] 방어적 프로그래밍 적용
- [ ] 예외 처리 시 스택 트레이스 포함

### 구현 후
- [ ] End-to-End 테스트 수행
- [ ] 로그를 통한 전체 플로우 확인
- [ ] 데이터베이스 실제 저장 확인
- [ ] 오류 시나리오 테스트

## 로깅 전략
```python
# 개발 시 DEBUG 레벨 사용
LOG_LEVEL=DEBUG

# 구조화된 로그 메시지
logger.debug(f"Processing: {operation} for {user}")
logger.info(f"Operation completed: {result}")
logger.error(f"Operation failed: {error}", exc_info=True)
```