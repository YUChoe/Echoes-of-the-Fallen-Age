# 프로젝트 장기 메모리 문서

## 🚨 중요한 개발 규칙

### 가상 환경 사용 필수

**⚠️ 절대로 가상 환경만을 사용할 것!**

- 모든 Python 명령어는 반드시 가상 환경 내에서 실행
- 가상 환경 활성화: `source mud_engine_env/Scripts/activate`
- 패키지 설치, 테스트 실행, 서버 실행 등 모든 작업은 가상 환경에서만 수행
- 전역 Python 환경 사용 금지

### 실행 방법

- Command 에 `bash -c` 등을 사용하지 말 것
- **⚠️ PYTHONPATH 설정 필수**: 모든 Python 실행 시 PYTHONPATH를 프로젝트 루트로 설정
- 올바른 실행 예시: `PYTHONPATH=. python -m src.mud_engine.main`
- 테스트 실행 시: `PYTHONPATH=. pytest`
- **Git 커밋**: 가상 환경 불필요 - 직접 `git add`, `git commit` 사용 가능

### 가상 환경 확인 방법

```bash
# 가상 환경 활성화 후 패키지 목록 확인
source mud_engine_env/Scripts/activate && pip list

# 가상 환경 활성화 후 테스트 실행 (PYTHONPATH 포함)
source mud_engine_env/Scripts/activate && PYTHONPATH=. pytest

# 가상 환경 활성화 후 서버 실행 (PYTHONPATH 포함)
source mud_engine_env/Scripts/activate && PYTHONPATH=. python -m src.mud_engine.main
```

## 프로젝트 구조

### 현재 구현된 주요 컴포넌트

#### WorldManager (작업 10번 완료)

- **위치**: `src/mud_engine/game/managers.py`
- **기능**:
  - 방 생성, 수정, 조회, 삭제
  - 게임 객체 관리 및 위치 추적
  - 실시간 세계 편집 지원
  - 세계 무결성 검증 및 자동 수정
- **통합**: GameEngine에 완전 통합됨
- **테스트**: `tests/unit/test_world_manager.py` 작성 완료

#### 주요 모델

- **Room**: 다국어 지원, 출구 관리
- **GameObject**: 위치 추적, 속성 관리
- **Player, Character**: 플레이어 및 캐릭터 관리

#### 이벤트 시스템

- **EventBus**: 게임 이벤트 처리
- **새 이벤트 타입**: `WORLD_UPDATED` 추가됨

## 개발 진행 상황

### 완료된 작업

- [x] 작업 10: 게임 세계 관리 시스템 구현

  - WorldManager 클래스 구현
  - 방 관리 기능 (생성, 수정, 조회, 삭제)
  - 게임 객체 관리 및 위치 추적 시스템
  - GameEngine 통합
  - 단위 테스트 작성

- [x] 작업 11: 플레이어 이동 및 탐색 시스템 구현
  - 방향 명령어 처리 (north, south, east, west 등)
  - MoveCommand, GoCommand, ExitsCommand 구현
  - 방 설명 및 출구 정보 표시 로직
  - 이동 시 다른 플레이어들에게 알림 기능
  - move_player_to_room 메서드로 완전한 이동 처리
  - 단위 테스트 작성 및 검증

### 다음 작업 예정

- 작업 12: 객체 상호작용 시스템 구현 (tasks.md 참조)

## 기술 스택

- **Backend**: Python 3.10+, aiohttp, aiosqlite
- **Frontend**: HTML, CSS, JavaScript (WebSocket)
- **Database**: SQLite
- **Testing**: pytest, pytest-asyncio
- **Development**: black, flake8, mypy

## 주의사항

- 모든 비동기 함수는 `async/await` 패턴 사용
- 로깅은 Python logging 모듈 사용
- 다국어 지원을 위해 모든 텍스트는 딕셔너리 형태로 저장
- 데이터베이스 작업은 리포지토리 패턴 사용
- 이벤트 기반 아키텍처로 컴포넌트 간 결합도 최소화
