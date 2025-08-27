# 태스크 20 월드 생성 베스트 프랙티스

## 실수 분석 및 교훈

### 1. 모듈 import 경로 오류

**실수**: 초기에 잘못된 모듈 경로로 import 시도
```python
# ❌ 잘못된 방법
from src.mud_engine.database.db_manager import DatabaseManager
from src.mud_engine.models.room import Room
```

**해결**:
```python
# ✅ 올바른 방법
from src.mud_engine.database.connection import DatabaseManager
from src.mud_engine.game.models import Room
from src.mud_engine.game.repositories import RoomRepository, GameObjectRepository
```

**교훈**:
- 스크립트 작성 전 실제 프로젝트 구조를 확인할 것
- `listDirectory`와 `grepSearch`를 활용하여 정확한 모듈 위치 파악
- 클래스명으로 검색하여 실제 정의 위치 확인

### 2. 데이터 모델 구조 불일치

**실수**: 코드 모델과 데이터베이스 스키마 구조 차이 간과
- 코드에서는 `Room.name`이 딕셔너리 형태
- 데이터베이스에서는 `name_en`, `name_ko`로 분리

**해결**:
```python
# ❌ 잘못된 방법
"name": {"en": "West Gate", "ko": "서쪽 성문"}

# ✅ 올바른 방법 (DB 스키마에 맞춤)
"name_en": "West Gate",
"name_ko": "서쪽 성문"
```

**교훈**:
- 스크립트 작성 전 데이터베이스 스키마 확인 필수
- `PRAGMA table_info(table_name)` 명령으로 실제 컬럼 구조 파악
- 모델 클래스와 DB 스키마 간 차이점 사전 확인

### 3. 중복 생성 방지 로직 누락

**실수**: 초기 스크립트에서 기존 데이터 존재 여부 확인 없이 생성 시도
```python
# ❌ 잘못된 방법
await self.room_repo.create(gate_room.to_dict())  # UNIQUE constraint 오류 발생
```

**해결**:
```python
# ✅ 올바른 방법
existing_gate = await self.room_repo.get_by_id("room_gate_west")
if existing_gate:
    print("서쪽 성문이 이미 존재합니다.")
else:
    await self.room_repo.create(gate_room.to_dict())
```

**교훈**:
- 데이터 생성 스크립트는 항상 멱등성(idempotent) 보장
- 기존 데이터 존재 여부 확인 후 생성
- 생성된 항목 수를 카운트하여 사용자에게 피드백 제공

### 4. 리포지토리 클래스명 혼동

**실수**: `ObjectRepository`와 `GameObjectRepository` 클래스명 혼동
```python
# ❌ 잘못된 방법
from src.mud_engine.game.repositories import RoomRepository, ObjectRepository
```

**해결**:
```python
# ✅ 올바른 방법
from src.mud_engine.game.repositories import RoomRepository, GameObjectRepository
```

**교훈**:
- 클래스명 가정하지 말고 실제 파일에서 확인
- `grepSearch`로 클래스 정의 검색하여 정확한 이름 파악
- IDE 자동완성에 의존하지 말고 수동으로 검증

### 5. 데이터 구조 변환 로직 미흡

**실수**: Room 모델의 exits 필드 처리 시 타입 확인 부족
```python
# ❌ 문제가 될 수 있는 방법
exits = json.loads(town_square.get('exits', '{}'))
```

**해결**:
```python
# ✅ 안전한 방법
exits = town_square.exits if isinstance(town_square.exits, dict) else json.loads(town_square.exits)
```

**교훈**:
- 데이터베이스에서 가져온 데이터의 타입 확인 필수
- JSON 문자열과 딕셔너리 객체 구분하여 처리
- 방어적 프로그래밍으로 타입 안전성 확보

## 권장 개발 패턴

### 1. 월드 생성 스크립트 구조

```python
class WorldCreator:
    def __init__(self):
        self.db_manager = None
        self.room_repo = None
        self.object_repo = None

    async def initialize(self):
        """의존성 초기화"""
        self.db_manager = DatabaseManager()
        await self.db_manager.initialize()
        self.room_repo = RoomRepository(self.db_manager)
        self.object_repo = GameObjectRepository(self.db_manager)

    async def create_with_duplicate_check(self, repo, data, item_type):
        """중복 확인 후 생성"""
        existing = await repo.get_by_id(data["id"])
        if existing:
            return False  # 이미 존재

        await repo.create(data)
        return True  # 새로 생성됨
```

### 2. 데이터베이스 스키마 확인 패턴

```python
async def verify_schema(self):
    """스키마 구조 확인"""
    # 테이블 구조 확인
    room_columns = await self.db_manager.get_table_info("rooms")
    object_columns = await self.db_manager.get_table_info("game_objects")

    # 필요한 컬럼 존재 여부 확인
    required_room_cols = ["id", "name_en", "name_ko", "exits"]
    required_object_cols = ["id", "name_en", "name_ko", "location_type", "location_id"]

    # 검증 로직...
```

### 3. 안전한 데이터 생성 패턴

```python
async def create_rooms_safely(self, room_data_list):
    """안전한 방 생성"""
    created_count = 0

    for room_data in room_data_list:
        try:
            # 기존 확인
            existing = await self.room_repo.get_by_id(room_data["id"])
            if existing:
                continue

            # 데이터 검증
            self.validate_room_data(room_data)

            # 생성
            await self.room_repo.create(room_data)
            created_count += 1

        except Exception as e:
            logger.error(f"방 생성 실패 {room_data['id']}: {e}")
            continue

    return created_count
```

### 4. 검증 및 피드백 패턴

```python
async def verify_world_creation(self):
    """생성 결과 검증"""
    results = {
        "gates_created": 0,
        "rooms_created": 0,
        "objects_created": 0,
        "errors": []
    }

    # 각 항목별 검증
    try:
        gate = await self.room_repo.get_by_id("room_gate_west")
        results["gates_created"] = 1 if gate else 0
    except Exception as e:
        results["errors"].append(f"성문 검증 실패: {e}")

    # 결과 출력
    self.print_verification_results(results)
    return results
```

## 체크리스트

### 스크립트 작성 전
- [ ] 프로젝트 구조 확인 (`listDirectory` 사용)
- [ ] 필요한 클래스/모듈 위치 확인 (`grepSearch` 사용)
- [ ] 데이터베이스 스키마 확인 (`PRAGMA table_info` 사용)
- [ ] 기존 데이터 상태 확인

### 스크립트 작성 중
- [ ] 정확한 import 경로 사용
- [ ] 데이터베이스 스키마에 맞는 데이터 구조 사용
- [ ] 중복 생성 방지 로직 포함
- [ ] 예외 처리 및 로깅 추가
- [ ] 타입 안전성 확보 (isinstance 사용)

### 스크립트 실행 후
- [ ] 생성 결과 검증
- [ ] 데이터베이스 실제 저장 확인
- [ ] 게임에서 실제 동작 테스트
- [ ] 오류 로그 확인 및 수정

## 월드 생성 특화 가이드

### 1. 방 연결 시스템
- 8x8 격자에서 경계 처리 로직 필수
- 양방향 연결 확인 (A->B 연결 시 B->A도 확인)
- 특수 연결점 (성문 등) 별도 처리

### 2. 객체 배치 전략
- 방별 객체 밀도 고려 (너무 많거나 적지 않게)
- 객체 타입별 적절한 위치 선택
- 플레이어 탐험 동기 부여할 수 있는 배치

### 3. 확장성 고려
- 좌표 기반 방 ID 시스템 (`forest_x_y`)
- 설명 템플릿 시스템으로 다양성 확보
- 추후 NPC, 퀘스트 추가 고려한 구조

## 결론

월드 생성 스크립트는 게임의 기반이 되는 중요한 작업입니다. 데이터 일관성, 중복 방지, 안전한 생성 로직을 통해 안정적인 게임 월드를 구축할 수 있습니다. 특히 데이터베이스 스키마와 코드 모델 간의 차이점을 사전에 파악하고, 멱등성을 보장하는 스크립트 작성이 핵심입니다.