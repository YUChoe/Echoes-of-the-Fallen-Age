# 글로벌 스케줄러 사용 가이드

## 개요

글로벌 스케줄러는 0, 15, 30, 45초에 정확하게 작동하는 이벤트 시스템입니다.
주기적으로 실행해야 하는 작업을 등록하고 관리할 수 있습니다.

## 기본 개념

### 실행 간격

스케줄러는 매 분마다 다음 시점에 이벤트를 실행합니다:
- 0초 (매 분 정각)
- 15초
- 30초
- 45초

### 이벤트 등록

이벤트는 `ScheduleInterval` 열거형을 사용하여 실행 간격을 지정합니다:
- `ScheduleInterval.SECOND_00` - 0초
- `ScheduleInterval.SECOND_15` - 15초
- `ScheduleInterval.SECOND_30` - 30초
- `ScheduleInterval.SECOND_45` - 45초

## 사용 방법

### 1. 이벤트 콜백 함수 작성

```python
async def my_scheduled_task():
    """스케줄러에서 실행할 비동기 함수"""
    logger.info("스케줄된 작업 실행 중...")
    # 작업 수행
    await some_async_operation()
    logger.info("스케줄된 작업 완료")
```

### 2. 이벤트 등록

GameEngine 시작 시 또는 런타임에 이벤트를 등록합니다:

```python
from src.mud_engine.core.managers.scheduler_manager import ScheduleInterval

# 0초와 30초마다 실행
game_engine.scheduler_manager.register_event(
    name="my_task",
    callback=my_scheduled_task,
    intervals=[ScheduleInterval.SECOND_00, ScheduleInterval.SECOND_30]
)

# 15초마다만 실행
game_engine.scheduler_manager.register_event(
    name="another_task",
    callback=another_task,
    intervals=[ScheduleInterval.SECOND_15]
)

# 모든 간격에서 실행 (0, 15, 30, 45초)
game_engine.scheduler_manager.register_event(
    name="frequent_task",
    callback=frequent_task,
    intervals=[
        ScheduleInterval.SECOND_00,
        ScheduleInterval.SECOND_15,
        ScheduleInterval.SECOND_30,
        ScheduleInterval.SECOND_45
    ]
)
```

### 3. 이벤트 관리

```python
# 이벤트 비활성화
game_engine.scheduler_manager.disable_event("my_task")

# 이벤트 활성화
game_engine.scheduler_manager.enable_event("my_task")

# 이벤트 등록 해제
game_engine.scheduler_manager.unregister_event("my_task")

# 이벤트 정보 조회
info = game_engine.scheduler_manager.get_event_info("my_task")
print(f"실행 횟수: {info['run_count']}")
print(f"오류 횟수: {info['error_count']}")

# 모든 이벤트 목록
events = game_engine.scheduler_manager.list_events()
for event in events:
    print(f"{event['name']}: {event['enabled']}")
```

## 관리자 명령어

게임 내에서 관리자는 다음 명령어로 스케줄러를 관리할 수 있습니다:

```
scheduler list                  - 등록된 이벤트 목록
scheduler info <이벤트명>       - 이벤트 상세 정보
scheduler enable <이벤트명>     - 이벤트 활성화
scheduler disable <이벤트명>    - 이벤트 비활성화
```

별칭: `sched`

## 실제 사용 예시

### 예시 1: 몬스터 스폰 시스템

```python
async def spawn_monsters_scheduled():
    """30초마다 몬스터 스폰"""
    try:
        spawned = await game_engine.world_manager.spawn_monsters_in_all_rooms()
        logger.info(f"스케줄 스폰: {spawned}마리 생성")
    except Exception as e:
        logger.error(f"스폰 오류: {e}")

# GameEngine.start()에서 등록
game_engine.scheduler_manager.register_event(
    name="monster_spawn",
    callback=spawn_monsters_scheduled,
    intervals=[ScheduleInterval.SECOND_00, ScheduleInterval.SECOND_30]
)
```

### 예시 2: 자동 저장 시스템

```python
async def auto_save_players():
    """1분마다 모든 플레이어 자동 저장"""
    try:
        count = 0
        for session in game_engine.session_manager.iter_authenticated_sessions():
            if session.player:
                await game_engine.player_manager.save_player(session.player)
                count += 1
        logger.info(f"자동 저장 완료: {count}명")
    except Exception as e:
        logger.error(f"자동 저장 오류: {e}")

# 0초에만 실행 (1분마다)
game_engine.scheduler_manager.register_event(
    name="auto_save",
    callback=auto_save_players,
    intervals=[ScheduleInterval.SECOND_00]
)
```

### 예시 3: 정리 작업

```python
async def cleanup_expired_data():
    """15초마다 만료된 데이터 정리"""
    try:
        # 전투 타임아웃 체크
        await game_engine.combat_manager.check_combat_timeouts()
        
        # 비활성 세션 정리
        await game_engine.session_manager.cleanup_inactive_sessions()
        
        logger.debug("정리 작업 완료")
    except Exception as e:
        logger.error(f"정리 작업 오류: {e}")

# 모든 간격에서 실행
game_engine.scheduler_manager.register_event(
    name="cleanup",
    callback=cleanup_expired_data,
    intervals=[
        ScheduleInterval.SECOND_00,
        ScheduleInterval.SECOND_15,
        ScheduleInterval.SECOND_30,
        ScheduleInterval.SECOND_45
    ]
)
```

### 예시 4: 통계 수집

```python
async def collect_statistics():
    """1분마다 서버 통계 수집"""
    try:
        stats = {
            "timestamp": datetime.now().isoformat(),
            "active_players": len(list(game_engine.session_manager.iter_authenticated_sessions())),
            "total_rooms": await game_engine.world_manager.get_room_count(),
            "active_combats": game_engine.combat_manager.get_active_combat_count()
        }
        
        # 통계 저장 또는 로깅
        logger.info(f"서버 통계: {stats}")
        
    except Exception as e:
        logger.error(f"통계 수집 오류: {e}")

# 0초에만 실행
game_engine.scheduler_manager.register_event(
    name="statistics",
    callback=collect_statistics,
    intervals=[ScheduleInterval.SECOND_00]
)
```

## GameEngine 통합 예시

```python
# src/mud_engine/core/game_engine.py의 start() 메서드에서

async def start(self) -> None:
    """게임 엔진 시작"""
    # ... 기존 코드 ...
    
    # 글로벌 스케줄러 시작
    await self.scheduler_manager.start()
    
    # 스케줄 이벤트 등록
    self._register_scheduled_events()
    
    logger.info("GameEngine 시작 완료")

def _register_scheduled_events(self) -> None:
    """스케줄 이벤트 등록"""
    from .managers.scheduler_manager import ScheduleInterval
    
    # 몬스터 스폰 (30초마다)
    self.scheduler_manager.register_event(
        name="monster_spawn",
        callback=self._scheduled_monster_spawn,
        intervals=[ScheduleInterval.SECOND_00, ScheduleInterval.SECOND_30]
    )
    
    # 자동 저장 (1분마다)
    self.scheduler_manager.register_event(
        name="auto_save",
        callback=self._scheduled_auto_save,
        intervals=[ScheduleInterval.SECOND_00]
    )
    
    # 정리 작업 (15초마다)
    self.scheduler_manager.register_event(
        name="cleanup",
        callback=self._scheduled_cleanup,
        intervals=[
            ScheduleInterval.SECOND_00,
            ScheduleInterval.SECOND_15,
            ScheduleInterval.SECOND_30,
            ScheduleInterval.SECOND_45
        ]
    )
    
    logger.info("스케줄 이벤트 등록 완료")

async def _scheduled_monster_spawn(self) -> None:
    """스케줄된 몬스터 스폰"""
    try:
        spawned = await self.world_manager.spawn_monsters_in_all_rooms()
        logger.debug(f"스케줄 스폰: {spawned}마리")
    except Exception as e:
        logger.error(f"스폰 오류: {e}")

async def _scheduled_auto_save(self) -> None:
    """스케줄된 자동 저장"""
    try:
        count = 0
        for session in self.session_manager.iter_authenticated_sessions():
            if session.player:
                await self.player_manager.save_player(session.player)
                count += 1
        logger.info(f"자동 저장: {count}명")
    except Exception as e:
        logger.error(f"자동 저장 오류: {e}")

async def _scheduled_cleanup(self) -> None:
    """스케줄된 정리 작업"""
    try:
        await self.combat_manager.check_combat_timeouts()
        logger.debug("정리 작업 완료")
    except Exception as e:
        logger.error(f"정리 작업 오류: {e}")
```

## 주의사항

### 1. 비동기 함수 사용

콜백은 반드시 `async def`로 정의된 비동기 함수여야 합니다.

```python
# ✅ 올바른 방법
async def my_callback():
    await some_async_operation()

# ❌ 잘못된 방법
def my_callback():  # async 없음
    some_operation()
```

### 2. 예외 처리

콜백 내부에서 예외를 처리하여 스케줄러가 중단되지 않도록 합니다.

```python
async def safe_callback():
    try:
        await risky_operation()
    except Exception as e:
        logger.error(f"작업 실패: {e}")
        # 복구 로직
```

### 3. 실행 시간

콜백은 가능한 빠르게 완료되어야 합니다. 긴 작업은 별도 태스크로 분리합니다.

```python
async def quick_callback():
    # 빠른 작업만 수행
    asyncio.create_task(long_running_task())  # 별도 태스크로 실행
```

### 4. 이벤트 이름 중복

같은 이름으로 이벤트를 등록하면 기존 이벤트를 덮어씁니다.

```python
# 첫 번째 등록
scheduler.register_event("task", callback1, [ScheduleInterval.SECOND_00])

# 두 번째 등록 - callback1이 callback2로 교체됨
scheduler.register_event("task", callback2, [ScheduleInterval.SECOND_15])
```

## 디버깅

### 로그 레벨 설정

```python
# 스케줄러 디버그 로그 활성화
logging.getLogger("src.mud_engine.core.managers.scheduler_manager").setLevel(logging.DEBUG)
```

### 이벤트 실행 확인

```python
# 이벤트 정보로 실행 여부 확인
info = scheduler.get_event_info("my_task")
print(f"실행 횟수: {info['run_count']}")
print(f"마지막 실행: {info['last_run']}")
print(f"오류 횟수: {info['error_count']}")
```

## 성능 고려사항

1. 콜백은 가볍게 유지
2. 무거운 작업은 별도 태스크로 분리
3. 데이터베이스 작업은 배치 처리
4. 불필요한 이벤트는 비활성화

## 요약

글로벌 스케줄러는 정확한 시간 간격으로 작업을 실행하는 강력한 도구입니다.
몬스터 스폰, 자동 저장, 정리 작업 등 주기적인 작업에 활용하세요.
