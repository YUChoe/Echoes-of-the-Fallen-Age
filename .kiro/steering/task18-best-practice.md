# 18번 태스크 (고급 인벤토리 시스템) 구현 베스트 프랙티스

## 개요
이 문서는 Python MUD Engine의 18번 태스크 "고급 인벤토리 시스템 구현" 과정에서 발생한 실수들을 분석하고, 향후 유사한 문제를 방지하기 위한 베스트 프랙티스를 정리한 것입니다.

## 🚨 주요 실수 분석

### 1. 타입 불일치 오류 (StatType enum vs 문자열)
**문제**: `'str' object has no attribute 'value'` 오류 발생
**원인**:
- Player 모델의 `get_max_carry_weight()` 메서드에서 `get_primary_stat('strength')` 호출
- `get_primary_stat()` 메서드는 `StatType` enum을 기대하지만 문자열을 전달받음
- `stat_type.value` 접근 시 문자열에는 `value` 속성이 없어 오류 발생

**해결책**:
```python
# ❌ 잘못된 방법
base_strength = self.stats.get_primary_stat('strength')

# ✅ 올바른 방법
from .stats import StatType
base_strength = self.stats.get_primary_stat(StatType.STR)
```

**교훈**:
- 메서드 시그니처와 타입 힌트를 정확히 확인하고 사용
- enum 타입을 사용하는 메서드에는 반드시 enum 값을 전달
- 타입 불일치 오류는 런타임에 발생하므로 사전 검증 필요

### 2. 이벤트 데이터 필드명 불일치
**문제**: 클라이언트에서 플레이어 이름이 `None`으로 표시
**원인**:
- pick/drop 명령어에서 이벤트 데이터를 `player_name` 필드로 전송
- 이벤트 핸들러에서는 `username` 필드로 데이터 조회
- 필드명 불일치로 인해 `data.get('username')`이 `None` 반환

**해결책**:
```python
# 명령어에서 전송하는 데이터
data = {
    "player_name": session.player.username,  # 이 필드명 사용
    "object_name": target_object.get_localized_name(session.locale)
}

# 이벤트 핸들러에서 조회
player_name = data.get('player_name')  # 동일한 필드명 사용
```

**교훈**:
- 이벤트 데이터 스키마의 일관성 유지 필수
- 송신자와 수신자 간 필드명 통일
- 이벤트 데이터 구조 문서화 필요

### 3. 디버깅 로그 레벨 설정 미흡
**문제**: 초기에 INFO 로그 레벨로 인해 DEBUG 로그가 출력되지 않음
**원인**:
- `.env` 파일에서 `LOG_LEVEL=INFO`로 설정
- 디버깅에 필요한 `logger.debug()` 메시지들이 출력되지 않음
- 문제 진단에 필요한 정보 부족

**해결책**:
```env
# 개발 중에는 DEBUG 레벨 사용
LOG_LEVEL=DEBUG
```

**교훈**:
- 개발 단계에서는 DEBUG 로그 레벨 사용
- 문제 발생 시 즉시 로그 레벨 조정
- 중요한 디버깅 정보는 적절한 로그 레벨로 기록

### 4. 스택 트레이스 정보 부족
**문제**: 초기 오류 메시지만으로는 정확한 오류 위치 파악 어려움
**원인**:
- `logger.error(f"오류: {e}", exc_info=True)` 대신 단순 메시지만 로깅
- 스택 트레이스 정보 없이는 오류 발생 지점 추적 곤란

**해결책**:
```python
# ❌ 불충분한 오류 로깅
except Exception as e:
    logger.error(f"객체 획득 명령어 실행 중 오류: {e}")

# ✅ 완전한 오류 로깅
except Exception as e:
    import traceback
    logger.error(f"객체 획득 명령어 실행 중 오류: {e}")
    logger.error(f"스택 트레이스: {traceback.format_exc()}")
```

**교훈**:
- 예외 처리 시 항상 스택 트레이스 포함
- `traceback.format_exc()` 또는 `exc_info=True` 사용
- 디버깅에 필요한 충분한 컨텍스트 정보 제공

## 📋 베스트 프랙티스 체크리스트

### 구현 전 확인사항
- [ ] 메서드 시그니처와 매개변수 타입 확인
- [ ] 이벤트 데이터 스키마 설계 및 문서화
- [ ] 로그 레벨을 DEBUG로 설정
- [ ] 타입 힌트 및 enum 사용법 확인

### 구현 중 확인사항
- [ ] enum 타입 메서드에는 enum 값 전달
- [ ] 이벤트 송신/수신 간 필드명 일치성 확인
- [ ] 충분한 디버깅 로그 추가
- [ ] 예외 처리 시 스택 트레이스 포함

### 구현 후 확인사항
- [ ] End-to-End 테스트 수행
- [ ] 클라이언트에서 실제 동작 확인
- [ ] 로그를 통한 전체 플로우 검증
- [ ] 오류 시나리오 테스트

## 🔧 권장 개발 패턴

### 1. 타입 안전성 보장 패턴
```python
# enum 사용 시 명시적 import 및 타입 확인
from .stats import StatType

def get_stat_value(self, stat_name: str) -> int:
    # 문자열을 enum으로 변환
    try:
        stat_type = StatType(stat_name)
        return self.stats.get_primary_stat(stat_type)
    except ValueError:
        logger.warning(f"Unknown stat type: {stat_name}")
        return 0
```

### 2. 이벤트 데이터 일관성 패턴
```python
# 이벤트 데이터 스키마 정의
OBJECT_PICKED_UP_SCHEMA = {
    "player_id": str,
    "player_name": str,
    "object_id": str,
    "object_name": str,
    "room_id": str
}

# 송신 시
event_data = {
    "player_id": session.player.id,
    "player_name": session.player.username,  # 일관된 필드명
    "object_id": target_object.id,
    "object_name": target_object.get_localized_name(session.locale),
    "room_id": current_room_id
}

# 수신 시
player_name = data.get('player_name')  # 동일한 필드명 사용
```

### 3. 포괄적 오류 처리 패턴
```python
def execute_command(self, session, args):
    try:
        # 메인 로직
        result = self.process_command(session, args)
        logger.debug(f"명령어 실행 성공: {result}")
        return result

    except SpecificException as e:
        logger.error(f"특정 오류 발생: {e}", exc_info=True)
        return self.create_error_result("특정 오류 메시지")

    except Exception as e:
        logger.error(f"예상치 못한 오류: {e}", exc_info=True)
        return self.create_error_result("일반적인 오류 메시지")
```

### 4. 디버깅 친화적 로깅 패턴
```python
def pick_object(self, session, object_name):
    logger.debug(f"객체 획득 시작: player={session.player.username}, object={object_name}")

    try:
        # 각 단계별 로깅
        logger.debug(f"현재 방 객체 조회: room_id={current_room_id}")
        room_objects = await self.get_room_objects(current_room_id)
        logger.debug(f"방 객체 개수: {len(room_objects)}")

        # 중요한 상태 변화 로깅
        logger.debug(f"객체 이동 시작: {object_id} -> inventory")
        success = await self.move_object(object_id, session.player.id)
        logger.debug(f"객체 이동 결과: {success}")

        return self.create_success_result("성공")

    except Exception as e:
        logger.error(f"객체 획득 실패: {e}", exc_info=True)
        raise
```

## 🎯 향후 개발 시 주의사항

### 핵심 원칙
1. **타입 안전성 우선**: enum, 타입 힌트 적극 활용
2. **데이터 일관성 유지**: 이벤트 스키마 표준화
3. **충분한 로깅**: 디버깅에 필요한 모든 정보 기록
4. **점진적 테스트**: 각 단계마다 실제 동작 확인

### 구현 전략
5. **문서화 우선**: 이벤트 스키마, API 시그니처 사전 정의
6. **타입 검증**: 런타임 타입 체크 로직 추가
7. **오류 처리**: 예상 가능한 모든 오류 시나리오 고려
8. **로그 활용**: 문제 진단을 위한 충분한 컨텍스트 제공

### 품질 보증
9. **End-to-End 검증**: 서버-클라이언트 전체 플로우 테스트
10. **오류 시나리오**: 정상 케이스뿐만 아니라 예외 상황도 테스트
11. **성능 고려**: 로깅이 성능에 미치는 영향 최소화
12. **유지보수성**: 코드 가독성과 확장성 고려

## 📚 실수 패턴 요약

### 가장 빈번한 실수 유형
1. **타입 불일치** (enum vs 문자열)
2. **데이터 스키마 불일치** (필드명 차이)
3. **로깅 설정 미흡** (DEBUG 레벨 미사용)
4. **오류 정보 부족** (스택 트레이스 누락)

### 해결 우선순위
1. **타입 확인**: 메서드 시그니처와 매개변수 타입 일치
2. **스키마 통일**: 이벤트 데이터 필드명 표준화
3. **로그 레벨**: 개발 시 DEBUG 레벨 사용
4. **오류 추적**: 스택 트레이스 포함한 오류 로깅

## 🔍 디버깅 가이드

### 문제 발생 시 확인 순서
1. **로그 레벨 확인**: DEBUG 레벨로 설정되어 있는지 확인
2. **타입 검증**: enum 사용 메서드의 매개변수 타입 확인
3. **데이터 스키마**: 이벤트 송신/수신 간 필드명 일치성 확인
4. **스택 트레이스**: 오류 발생 지점 정확히 파악

### 효과적인 디버깅 방법
```python
# 타입 정보 로깅
logger.debug(f"매개변수 타입: {type(stat_type)}, 값: {stat_type}")

# 데이터 구조 로깅
logger.debug(f"이벤트 데이터: {json.dumps(event_data, indent=2)}")

# 상태 변화 추적
logger.debug(f"변경 전: {before_state}")
logger.debug(f"변경 후: {after_state}")
```

## 📖 참고 자료

- [admin-best-practice.md](.kiro/steering/admin-best-practice.md) - 관리자 기능 구현 경험
- [playerinteract2-best-practice.md](.kiro/steering/playerinteract2-best-practice.md) - 플레이어 상호작용 시스템 경험
- [clientrefactoring-best-practice.md](.kiro/steering/clientrefactoring-best-practice.md) - 클라이언트 리팩토링 경험
- Python 타입 힌트 베스트 프랙티스
- 이벤트 기반 아키텍처 설계 원칙
- 효과적인 로깅 전략

---

**이 문서는 18번 태스크 구현 과정에서 발생한 실제 문제들을 바탕으로 작성된 실무 가이드입니다.**