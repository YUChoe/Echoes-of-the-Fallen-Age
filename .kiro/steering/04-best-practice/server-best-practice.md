# 서버 개발 베스트 프랙티스

## 핵심 개념 및 원칙

### 기본 설계 원칙
- **단순함의 힘**: 복잡한 조건문보다 명확한 구조
- **일관성 유지**: 모든 메시지는 동일한 방식으로 처리
- **단일 책임 원칙**: 하나의 함수는 하나의 역할만
- **예측 가능성**: 코드 동작이 명확하게 예측 가능해야 함

### 기존 시스템 활용 원칙
- **기존 매니저 우선 사용**: 직접 구현보다 기존 매니저 메서드 활용
- **패턴 일관성**: 기존 구현 패턴을 참고하여 일관된 코드 작성
- **점진적 확장**: 기존 구조에 자연스럽게 확장

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

## 데이터 모델 및 타입 안전성

### 복합 객체 직렬화 패턴
```python
# 안전한 JSON 직렬화 패턴
class ComplexModel(BaseModel):
    def to_dict(self) -> Dict[str, Any]:
        # 1단계: 복합 객체들을 임시로 단순 객체로 변환
        original_complex_field = self.complex_field
        if isinstance(self.complex_field, list):
            self.complex_field = [item.to_dict() if hasattr(item, 'to_dict') else item
                                 for item in self.complex_field]

        # 2단계: BaseModel의 to_dict 호출 (안전한 JSON 직렬화)
        data = super().to_dict()

        # 3단계: 원본 복합 객체 복원 (객체 상태 유지)
        self.complex_field = original_complex_field

        return data
```

### 데이터 타입 일관성 확보 원칙
```python
# JSON 필드 대응 패턴
@classmethod
def from_dict(cls, data: Dict[str, Any]) -> 'Monster':
    converted_data = data.copy()

    # JSON 문자열 필드 변환
    if 'properties' in converted_data and isinstance(converted_data['properties'], str):
        try:
            converted_data['properties'] = json.loads(converted_data['properties'])
        except (json.JSONDecodeError, TypeError):
            converted_data['properties'] = {}  # 기본값 설정

    # 날짜 필드 변환
    if 'created_at' in converted_data and isinstance(converted_data['created_at'], str):
        converted_data['created_at'] = datetime.fromisoformat(converted_data['created_at'])

    return cls(**converted_data)
```

### 타입 힐트 완전성 원칙
```python
# 제네릭 타입 매개변수 명시
class MonsterRepository(BaseRepository[Monster]):
    """\uba3c스터 리포지토리"""

    def get_table_name(self) -> str:
        return "monsters"

    # 반환 타입 명시
    async def get_all_active(self) -> List[Monster]:
        return await self.get_all()

# 복잡한 타입 구조 명시
def process_combat_data(
    session_data: Dict[str, Union[str, int]],
    monster_data: Dict[str, Any]
) -> Optional[CombatResult]:
    # ...
```

### 모델과 스키마 일치
```python
# ❌ 잘못된 가정 (코드 모델과 DB 스키마 불일치)
"name": {"en": "Gate", "ko": "성문"}

# ✅ 실제 DB 스키마에 맞춤
"name_en": "Gate"
"name_ko": "성문"
```

## 데이터베이스 스키마 및 마이그레이션 관리

### 스키마 정의와 마이그레이션 동기화
```python
# 스키마 정의 및 마이그레이션 예시
async def migrate_database(db_manager) -> None:
    """데이터베이스 마이그레이션 수행"""
    # 기존 테이블 마이그레이션
    # ...

    # Monster 테이블 생성 확인 및 생성
    cursor = await db_manager.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='monsters'"
    )
    monster_table_exists = await cursor.fetchone()

    if not monster_table_exists:
        logger.info("Monster 테이블 생성 중...")
        await db_manager.execute("""
            CREATE TABLE monsters (
                id TEXT PRIMARY KEY,
                name_en TEXT NOT NULL,
                name_ko TEXT NOT NULL,
                level INTEGER DEFAULT 1,
                max_hp INTEGER DEFAULT 20,
                current_hp INTEGER DEFAULT 20,
                properties TEXT DEFAULT '{}',
                drop_items TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 인덱스 생성
        await db_manager.execute(
            "CREATE INDEX IF NOT EXISTS idx_monsters_level ON monsters(level)"
        )

        logger.info("Monster 테이블 생성 완료")

# 메타데이터 및 스키마 검증
def validate_schema_migration_sync():
    """스키마 정의와 마이그레이션 동기화 검증"""
    schema_tables = extract_tables_from_schema()
    migration_tables = extract_tables_from_migration()

    missing_in_migration = schema_tables - migration_tables
    if missing_in_migration:
        raise ValueError(f"마이그레이션에 누락된 테이블: {missing_in_migration}")
```

### 안전한 데이터 생성 패턴
```python
# 멱등성 보장 (중복 생성 방지)
async def create_room_safely(repo, room_data):
    """안전한 방 생성 (중복 방지)"""
    existing = await repo.get_by_id(room_data['id'])
    if existing:
        logger.info(f"Room {room_data['id']} 이미 존재")
        return existing

    new_room = await repo.create(room_data)
    logger.info(f"Room {room_data['id']} 생성 완료")
    return new_room

# 데이터 검증 및 변환
def safe_json_parse(json_str: str, default_value=None):
    """안전한 JSON 파싱"""
    if not json_str:
        return default_value or {}

    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"JSON 파싱 실패: {json_str}, 오류: {e}")
        return default_value or {}
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

## 명령어 시스템 및 관리자 기능

### 관리자 명령어 구현 템플릿
```python
class NewAdminCommand(AdminCommand):
    def __init__(self):
        super().__init__(
            name="commandname",
            description="명령어 설명",
            aliases=["alias1", "alias2"]
        )

    async def execute(self, session, game_engine, args):
        # 1. 관리자 권한 확인 (AdminCommand에서 자동 처리)

        # 2. 인자 검증
        if not args:
            return self.create_error_result("사용법: commandname <인자>")

        # 3. 기존 매니저 메서드 활용
        try:
            result = await game_engine.some_manager.some_method(args[0])
            if not result:
                return self.create_error_result("처리할 수 없습니다.")
        except Exception as e:
            self.logger.error(f"명령어 실행 오류: {e}")
            return self.create_error_result("명령어 실행 중 오류가 발생했습니다.")

        # 4. 성공 응답 및 브로드캐스트
        await session.send_success({"message": "처리 완료"})

        # 5. 필요시 다른 플레이어에게 알림
        await game_engine.broadcast_to_room(
            session.current_room_id,
            {"type": "admin_action", "message": f"관리자가 {action}을 실행했습니다."},
            exclude_session=session.session_id
        )

        return self.create_success_result("명령어 실행 완료")
```

### 매개변수 전달 및 별칭 시스템
```python
# 올바른 AdminCommand 매개변수 순서
class AdminCommand(BaseCommand):
    def __init__(self, name: str, description: str, aliases: List[str] = None):
        # ✅ 올바른 매개변수 순서
        super().__init__(name, description, aliases or [])
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

# 별칭 등록 검증 패턴
def register_command(self, command_instance):
    """명령어 등록 시 별칭 검증"""
    if hasattr(command_instance, 'aliases') and command_instance.aliases:
        if isinstance(command_instance.aliases, str):
            # 문자열이 개별 문자로 분해되는 것을 방지
            self.logger.warning(f"별칭이 문자열로 전달됨: {command_instance.aliases}")
            command_instance.aliases = [command_instance.aliases]

        # 각 별칭이 유효한지 검증
        for alias in command_instance.aliases:
            if len(alias) == 1 and ord(alias) > 127:  # 한글 단일 문자 검출
                self.logger.error(f"잘못된 별칭 감지: '{alias}' (한글 단일 문자)")
                raise ValueError(f"별칭에 한글 단일 문자가 포함됨: {alias}")
```

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

## 전투 시스템 및 게임 로직

### 전투 상태 관리 패턴
```python
# 세션별 전투 상태 관리
class CombatManager:
    def __init__(self):
        self.combat_sessions = {}  # 세션별 전투 상태

    async def start_combat(self, session, monster):
        # 전투 시작 로직
        combat_state = {
            'monster': monster,
            'turn': 'player',
            'start_time': datetime.now()
        }
        self.combat_sessions[session.session_id] = combat_state

        await session.send_message({
            "type": "combat_start",
            "message": f"{monster.name_ko}와의 전투를 시작합니다!"
        })

    async def process_combat_turn(self, session, action):
        # 턴 처리 로직
        combat_state = self.combat_sessions.get(session.session_id)
        if not combat_state:
            return

        if action == 'attack':
            damage = random.randint(5, 10)
            combat_state['monster'].current_hp -= damage

            await session.send_message({
                "type": "combat_action",
                "message": f"{combat_state['monster'].name_ko}에게 {damage} 데미지를 입혔습니다."
            })

    async def end_combat(self, session, victory=True):
        # 전투 종료 및 보상 처리
        combat_state = self.combat_sessions.pop(session.session_id, None)
        if not combat_state:
            return

        if victory:
            exp_gain = 50
            gold_gain = 10

            session.player.experience += exp_gain
            session.player.gold += gold_gain

            await session.send_success({
                "message": "몹스터를 처치했습니다!",
                "exp_gained": exp_gain,
                "gold_gained": gold_gain
            })
```

### 게임 데이터 검증 패턴
```python
# 방 ID 유효성 검증
async def validate_room_id(self, game_engine, room_id: str) -> bool:
    """방 ID 유효성 검증"""
    try:
        room = await game_engine.world_manager.get_room(room_id)
        return room is not None
    except Exception as e:
        self.logger.error(f"방 ID 검증 오류: {e}")
        return False

# 플레이어 존재 여부 검증
async def validate_player_exists(self, game_engine, player_id: str) -> bool:
    """플레이어 존재 여부 검증"""
    try:
        player = await game_engine.session_manager.get_player_by_id(player_id)
        return player is not None
    except Exception as e:
        self.logger.error(f"플레이어 검증 오류: {e}")
        return False
```

### 서버 측 로깅
```python
# Session 구조 확인
logger.debug(f"Session attributes: {dir(session)}")
logger.debug(f"Player: {session.player}")

# 데이터 구조 확인
logger.debug(f"Received data: {data}")
logger.debug(f"Room exits: {room.exits}")
```

## 로깅, 디버깅 및 에러 처리

### 체계적 디버깅 전략
```python
def debug_data_flow(self, data: Any, context: str) -> None:
    """데이터 흐름 디버깅 헬퍼"""
    logger.debug(f"{context} - Type: {type(data)}")
    logger.debug(f"{context} - Content: {data}")

    if isinstance(data, dict):
        for key, value in data.items():
            logger.debug(f"{context}.{key} - Type: {type(value)}, Value: {value}")

    if hasattr(data, '__dict__'):
        logger.debug(f"{context} - Attributes: {data.__dict__}")

# 서버 측 로깅 패턴
logger.debug(f"Session attributes: {dir(session)}")
logger.debug(f"Player: {session.player}")
logger.debug(f"Received data: {data}")
logger.debug(f"Room exits: {room.exits}")
```

### 에러 처리 및 복구 패턴
```python
# 방어적 에러 처리
try:
    result = await some_complex_operation()
    return self.create_success_result(result)
except ValidationError as e:
    logger.warning(f"데이터 검증 실패: {e}")
    return self.create_error_result("입력 데이터가 올바르지 않습니다.")
except DatabaseError as e:
    logger.error(f"데이터베이스 오류: {e}")
    return self.create_error_result("데이터 처리 중 오류가 발생했습니다.")
except Exception as e:
    logger.error(f"예상치 못한 오류: {e}", exc_info=True)
    return self.create_error_result("서버 내부 오류가 발생했습니다.")

# 자동 복구 로직
class AutoRecoveryManager:
    async def safe_execute_with_retry(self, operation, max_retries=3):
        for attempt in range(max_retries):
            try:
                return await operation()
            except RecoverableError as e:
                logger.warning(f"시도 {attempt + 1}/{max_retries} 실패: {e}")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # 지수 백오프
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

## 서버 개발 체크리스트 및 품질 관리

### 새로운 데이터 모델 추가 시
- [ ] 기존 패키지 구조 분석 및 적절한 위치 선정
- [ ] 복합 객체 포함 시 직렬화 순서 고려
- [ ] 데이터베이스 스키마 정의 및 마이그레이션 추가
- [ ] 타입 힐트 완전성 확보
- [ ] Repository 클래스에 Generic 타입 매개변수 명시

### JSON 직렬화 구현 시
- [ ] BaseModel.to_dict() 호출 전 복합 객체 전처리
- [ ] 원본 객체 상태 보존을 위한 백업/복원 로직
- [ ] 직렬화 불가능한 객체 타입 사전 확인
- [ ] 에러 발생 시 명확한 디버깅 정보 제공

### 관리자 명령어 구현 시
- [ ] 관련 매니저 클래스의 실제 메서드 확인
- [ ] 기존 유사 기능의 구현 패턴 분석
- [ ] 데이터베이스 실제 데이터 구조 확인
- [ ] 테스트 환경의 데이터 형식 파악

### 데이터베이스 작업 시
- [ ] 스키마 정의와 마이그레이션 스크립트 동시 작성
- [ ] 테이블 존재 여부 확인 후 생성
- [ ] 필요한 인덱스 및 제약조건 포함
- [ ] 기존 데이터와의 호환성 고려

### API 변경 시
- [ ] 서버-클라이언트 양쪽 동시 수정 계획
- [ ] 하위 호환성 고려
- [ ] 메시지 형식 일관성 유지
- [ ] 변경 영향 범위 분석
- [ ] 공통 함수 변경 시 모든 사용처 확인

## 피해야 할 패턴

### 코드 설계 및 구현
- 기존 코드 구조 확인 없이 추측으로 구현
- 복잡한 로직을 직접 구현하려는 시도
- JSON 필드 변환 로직 생략
- 제네릭 타입 매개변수 누락

### 디버깅 및 문제 해결
- 에러 메시지 분석 소홀
- 표면적 증상에만 집중하는 디버깅
- Import 의존성 확인 소홀
- 단계별 검증 없이 일괄 수정

## 권장 패턴

### 설계 및 개발 접근
- 사전 구조 분석을 통한 안전한 구현
- 기존 매니저 시스템 적극 활용
- 데이터 흐름 전체를 고려한 설계
- 타입 안전성을 최우선으로 고려

### 문제 해결 및 디버깅
- 체계적인 디버꺅으로 근본 원인 파악
- 서버 로그 기반 정확한 문제 파악
- 사전 예방을 위한 검증 로직 구현
- 단계별 검증으로 안정성 확보