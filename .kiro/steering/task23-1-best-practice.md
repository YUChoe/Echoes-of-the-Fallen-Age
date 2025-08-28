# Task 23-1 베스트 프랙티스: 몬스터 데이터 모델 구현 실수 분석

## 발생한 실수 분석

### 1. 순환 Import 문제 - 패키지 구조 설계 미흡
**실수**: 새로운 repositories 디렉토리를 만들면서 기존 repositories.py와 충돌 발생
**문제점**:
- `src/mud_engine/game/repositories/` 디렉토리와 `src/mud_engine/game/repositories.py` 파일이 동시 존재
- game/__init__.py에서 repositories 패키지를 import하려 했지만 실제로는 repositories.py 파일에서 import해야 함
- 순환 import로 인한 모듈 로딩 실패

```python
# ❌ 잘못된 접근 - 새 디렉토리 생성으로 인한 충돌
from .repositories import (  # repositories.py 파일을 의도했지만
    PlayerRepository,        # repositories/ 디렉토리를 찾음
    # ...
)

# ✅ 올바른 해결 - 기존 구조 파악 후 확장
# repositories.py 파일에 MonsterRepository 추가
class MonsterRepository(BaseRepository):
    def get_table_name(self) -> str:
        return "monsters"
```

### 2. JSON 직렬화 문제 - 복합 객체 처리 미흡
**실수**: DropItem 객체가 포함된 리스트를 BaseModel.to_dict()에서 JSON 직렬화 시도
**문제점**:
- BaseModel.to_dict()가 list/dict를 자동으로 JSON 변환하는데 DropItem 객체는 직렬화 불가
- Monster.to_dict()에서 super().to_dict() 호출 순서 문제
- 복합 객체의 직렬화 순서를 고려하지 않음

```python
# ❌ 문제 상황
def to_dict(self) -> Dict[str, Any]:
    data = super().to_dict()  # BaseModel이 drop_items 리스트를 JSON 변환 시도
    # DropItem 객체들이 JSON 직렬화되지 않아 에러 발생

# ✅ 올바른 해결
def to_dict(self) -> Dict[str, Any]:
    # BaseModel.to_dict() 호출 전에 복합 객체를 딕셔너리로 변환
    original_drop_items = self.drop_items
    if isinstance(self.drop_items, list):
        self.drop_items = [item.to_dict() if isinstance(item, DropItem) else item
                          for item in self.drop_items]

    data = super().to_dict()  # 이제 안전하게 JSON 직렬화 가능
    self.drop_items = original_drop_items  # 원본 복원
```

### 3. 데이터베이스 마이그레이션 순서 문제
**실수**: 새로운 테이블 생성을 기존 마이그레이션 로직에 추가하지 않음
**문제점**:
- schema.py에 Monster 테이블 정의는 추가했지만 migrate_database()에는 추가하지 않음
- 기존 데이터베이스에서 새 테이블이 자동 생성되지 않을 수 있음

```python
# ✅ 올바른 마이그레이션 추가
async def migrate_database(db_manager) -> None:
    # ... 기존 마이그레이션 코드 ...

    # Monster 테이블 생성 확인 및 생성
    cursor = await db_manager.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='monsters'")
    monster_table_exists = await cursor.fetchone()

    if not monster_table_exists:
        logger.info("Monster 테이블 생성 중...")
        # 테이블 생성 SQL 실행
```

### 4. 타입 힌트 불일치 - Generic 타입 처리 미흡
**실수**: MonsterRepository에서 BaseRepository[Monster] 대신 BaseRepository 사용
**문제점**:
- 타입 안전성 저하
- IDE 자동완성 및 타입 검사 기능 제한
- mypy 검사에서 타입 관련 경고 발생

```python
# ❌ 타입 힌트 누락
class MonsterRepository(BaseRepository):
    """몬스터 리포지토리"""

# ✅ 올바른 타입 힌트
class MonsterRepository(BaseRepository[Monster]):
    """몬스터 리포지토리"""
```

## 베스트 프랙티스 규칙

### 1. 패키지 구조 설계 원칙
- **기존 구조 파악 우선**: 새로운 컴포넌트 추가 전 기존 패키지 구조 완전 이해
- **점진적 확장**: 기존 파일에 추가 vs 새 디렉토리 생성의 장단점 비교
- **Import 경로 일관성**: 프로젝트 전체에서 일관된 import 패턴 유지
- **순환 Import 방지**: 모듈 간 의존성 그래프 사전 설계

### 2. 복합 객체 직렬화 패턴
```python
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

        # 4단계: 추가 변환 작업 (DB 스키마 맞춤 등)
        # ...

        return data
```

### 3. 데이터베이스 스키마 관리
- **스키마 정의와 마이그레이션 동기화**: 새 테이블 추가 시 두 곳 모두 업데이트
- **테이블 존재 여부 확인**: 마이그레이션에서 테이블 생성 전 존재 여부 체크
- **인덱스 생성 포함**: 성능을 위한 인덱스도 마이그레이션에 포함
- **외래키 제약조건 고려**: 테이블 간 관계 설정 시 참조 무결성 보장

### 4. 타입 안전성 확보
```python
# Generic 타입 매개변수 명시
class Repository(BaseRepository[ModelType]):
    def get_model_class(self) -> Type[ModelType]:
        return ModelType

# 반환 타입 명시
async def get_items(self) -> List[ModelType]:
    # ...

# 타입 가드 사용
def is_valid_item(item: Any) -> bool:
    return isinstance(item, ExpectedType)
```

## 구현 체크리스트

### 새로운 데이터 모델 추가 시
- [ ] 기존 패키지 구조 분석 및 적절한 위치 선정
- [ ] 복합 객체 포함 시 직렬화 순서 고려
- [ ] 데이터베이스 스키마 정의 및 마이그레이션 추가
- [ ] 타입 힌트 완전성 확보
- [ ] Repository 클래스에 Generic 타입 매개변수 명시

### JSON 직렬화 구현 시
- [ ] BaseModel.to_dict() 호출 전 복합 객체 전처리
- [ ] 원본 객체 상태 보존을 위한 백업/복원 로직
- [ ] 직렬화 불가능한 객체 타입 사전 확인
- [ ] 에러 발생 시 명확한 디버깅 정보 제공

### 데이터베이스 작업 시
- [ ] 스키마 정의와 마이그레이션 스크립트 동시 작성
- [ ] 테이블 존재 여부 확인 후 생성
- [ ] 필요한 인덱스 및 제약조건 포함
- [ ] 기존 데이터와의 호환성 고려

## 코드 품질 향상 방안

### 1. 사전 설계 강화
```python
# 모듈 의존성 다이어그램 작성
# A -> B -> C (순환 없음)
# 새 모듈 D 추가 시 의존성 경로 사전 계획

# 직렬화 전략 문서화
class SerializationStrategy:
    """
    복합 객체 직렬화 전략:
    1. 임시 변환 (복합 -> 단순)
    2. BaseModel 직렬화 호출
    3. 원본 복원
    4. 추가 변환
    """
```

### 2. 테스트 주도 개발
```python
def test_monster_serialization():
    """몬스터 객체 직렬화 테스트"""
    monster = Monster(
        name={'en': 'Test', 'ko': '테스트'},
        drop_items=[DropItem('item1', 0.5)]
    )

    # 직렬화 가능한지 확인
    data = monster.to_dict()
    assert isinstance(data['drop_items'], str)  # JSON 문자열

    # 역직렬화 가능한지 확인
    restored = Monster.from_dict(data)
    assert len(restored.drop_items) == 1
    assert isinstance(restored.drop_items[0], DropItem)
```

### 3. 점진적 검증
- 각 단계별 즉시 테스트 실행
- mypy 정적 검사 통과 확인
- 실제 데이터베이스 작업 검증
- 에러 발생 시 단계별 롤백 가능한 구조

## 주의사항

### 피해야 할 패턴
- 기존 구조 파악 없이 새 디렉토리/파일 생성
- 복합 객체 직렬화 순서 무시
- 스키마 정의와 마이그레이션 불일치
- Generic 타입 매개변수 생략

### 권장 패턴
- 기존 코드 분석 후 일관된 확장
- 단계별 객체 변환으로 안전한 직렬화
- 스키마와 마이그레이션 동시 관리
- 완전한 타입 힌트로 안전성 확보

## 결론

**핵심 교훈**:
1. **구조 파악 우선**: 새 기능 추가 전 기존 아키텍처 완전 이해
2. **직렬화 순서 중요**: 복합 객체는 단계별 변환으로 안전하게 처리
3. **스키마 일관성**: 정의와 마이그레이션을 항상 함께 관리
4. **타입 안전성**: Generic과 타입 힌트로 컴파일 타임 에러 방지

이러한 원칙을 따르면 복잡한 데이터 모델도 안정적으로 구현할 수 있으며, 향후 확장 시에도 일관성을 유지할 수 있습니다.

## 추가 개선 방안

### 자동화된 검증 시스템
```python
def validate_model_serialization(model_class):
    """모델 직렬화 유효성 자동 검증"""
    instance = model_class()  # 기본 인스턴스 생성

    try:
        data = instance.to_dict()
        restored = model_class.from_dict(data)
        assert type(restored) == model_class
        return True
    except Exception as e:
        logger.error(f"{model_class.__name__} 직렬화 실패: {e}")
        return False
```

### 스키마 동기화 검증
```python
async def verify_schema_migration_sync():
    """스키마 정의와 마이그레이션 동기화 검증"""
    schema_tables = extract_tables_from_schema()
    migration_tables = extract_tables_from_migration()

    missing_in_migration = schema_tables - migration_tables
    if missing_in_migration:
        raise ValueError(f"마이그레이션에 누락된 테이블: {missing_in_migration}")
```