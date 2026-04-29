# 구현 계획: 플레이어별 세션 로그

## 개요

Python 표준 `logging` 모듈의 named logger 방식을 사용하여 플레이어별 세션 활동을 개별 로그 파일(`logs/players/{player_id}.log`)에 기록하는 기능을 구현한다. `PlayerSessionLogger` 클래스를 신규 생성하고, `TelnetServer`의 6개 지점에 호출 코드를 추가한다.

## Tasks

- [x] 1. PlayerSessionLogger 클래스 및 GzipRotatingFileHandler 구현
  - [x] 1.1 `src/mud_engine/server/player_session_logger.py` 파일 생성
    - `GzipRotatingFileHandler` 클래스 구현: `logging.handlers.RotatingFileHandler` 상속, `doRollover()` 오버라이드하여 백업 파일을 gzip 압축
    - `PlayerSessionLogger` 클래스 구현:
      - `__init__()`: `logs/players/` 디렉토리 생성, 내부 상태 초기화
      - `setup_player_logger()`: `player.{player_id}` named logger 생성, `GzipRotatingFileHandler` 부착 (maxBytes=10MB, backupCount=5, encoding=utf-8), `propagate=False` 설정, 세션 시작 로그 기록 (session_id, player_id, username, ip_address 포함)
      - `log_command()`: 플레이어 명령어 로그 기록, 미설정 player_id는 조용히 무시
      - `log_session_end()`: 세션 종료 로그 기록 (종료 사유 포함)
      - `cleanup_player_logger()`: 핸들러 제거 및 close
      - `cleanup_all()`: 모든 활성 플레이어 로거 핸들러 정리
    - MudEngineFormatter와 동일한 포맷 (`{HH:MM:SS.mmm} {LEVEL} [{module:line}] {message}`) 적용
    - 모든 메서드에 try/except 적용, 오류 시 Global_Logger에 기록하고 게임 로직에 영향 없도록 처리
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 3.1, 3.2, 5.1, 5.2, 5.3, 6.1, 6.2, 6.3, 7.1, 7.2_

  - [ ]* 1.2 Property 1에 대한 속성 기반 테스트 작성
    - **Property 1: 세션 시작 로그에 필수 필드 포함**
    - hypothesis를 사용하여 임의의 player_id, username, session_id, ip_address 조합으로 `setup_player_logger` 호출 후 로그 파일에 4개 필드가 모두 포함되는지 검증
    - **Validates: Requirements 1.1, 2.1**

  - [ ]* 1.3 Property 2에 대한 속성 기반 테스트 작성
    - **Property 2: 로그 포맷 패턴 일치**
    - hypothesis를 사용하여 임의의 로그 레코드에 대해 포맷터 출력이 `{HH:MM:SS.mmm} {LEVEL} [{module:line}] {message}` 패턴과 일치하는지 검증
    - **Validates: Requirements 1.4**

  - [ ]* 1.4 Property 3에 대한 속성 기반 테스트 작성
    - **Property 3: 명령어 로그 기록**
    - hypothesis를 사용하여 임의의 player_id와 명령어 문자열로 `log_command` 호출 후 로그 파일에 원본 명령어가 포함되는지 검증
    - **Validates: Requirements 3.1, 3.2**

  - [ ]* 1.5 Property 4에 대한 속성 기반 테스트 작성
    - **Property 4: 세션 종료 로그에 사유 포함**
    - hypothesis를 사용하여 임의의 player_id와 종료 사유로 `log_session_end` 호출 후 로그 파일에 사유가 포함되는지 검증
    - **Validates: Requirements 2.2**

  - [ ]* 1.6 Property 5에 대한 속성 기반 테스트 작성
    - **Property 5: 핸들러 정리 후 리소스 해제**
    - hypothesis를 사용하여 임의의 player_id로 `setup_player_logger` 후 `cleanup_player_logger` 호출 시 핸들러 리스트가 비어있는지 검증
    - **Validates: Requirements 2.3, 6.1**

  - [ ]* 1.7 Property 6에 대한 속성 기반 테스트 작성
    - **Property 6: cleanup_all이 모든 로거 정리**
    - hypothesis를 사용하여 1~10개의 임의 player_id 집합에 대해 각각 `setup_player_logger` 후 `cleanup_all` 호출 시 모든 핸들러가 비어있는지 검증
    - **Validates: Requirements 6.2**

  - [ ]* 1.8 Property 7에 대한 속성 기반 테스트 작성
    - **Property 7: 플레이어 로거 격리성**
    - hypothesis를 사용하여 임의의 player_id로 플레이어 로거에 메시지 기록 시 루트 로거 핸들러로 전파되지 않는지 검증 (propagate=False 보장)
    - **Validates: Requirements 4.1, 4.2**

- [x] 2. Checkpoint - 중간 검증
  - PlayerSessionLogger 단위 테스트 및 속성 기반 테스트 통과 확인
  - mypy + ruff 정적 검사 통과 확인
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. TelnetServer에 PlayerSessionLogger 통합
  - [x] 3.1 `TelnetServer.__init__()`에 `PlayerSessionLogger` 인스턴스 생성 코드 추가
    - `from .player_session_logger import PlayerSessionLogger` import 추가
    - `self.player_session_logger = PlayerSessionLogger()` 인스턴스 생성
    - _Requirements: 1.1, 1.3_

  - [x] 3.2 `TelnetServer.handle_login()`에 `setup_player_logger()` 호출 추가
    - 인증 성공 후 (`session.authenticate(player)` 이후) `self.player_session_logger.setup_player_logger()` 호출
    - player.id, player.username, session.session_id, session.ip_address 전달
    - _Requirements: 2.1, 7.2_

  - [x] 3.3 `TelnetServer.handle_register()`에 `setup_player_logger()` 호출 추가
    - 회원가입 + 자동 로그인 후 (`session.authenticate(player)` 이후) `self.player_session_logger.setup_player_logger()` 호출
    - player.id, player.username, session.session_id, session.ip_address 전달
    - _Requirements: 2.1, 7.2_

  - [x] 3.4 `TelnetServer.handle_game_command()`에 `log_command()` 호출 추가
    - 명령어 처리 전 `self.player_session_logger.log_command(session.player.id, command)` 호출
    - session.player가 None이 아닌 경우에만 호출
    - _Requirements: 3.1, 3.2_

  - [x] 3.5 `TelnetServer.remove_session()`에 `log_session_end()` + `cleanup_player_logger()` 호출 추가
    - 세션 제거 시 `self.player_session_logger.log_session_end(session.player.id, reason)` 호출
    - 이후 `self.player_session_logger.cleanup_player_logger(session.player.id)` 호출
    - session.player가 None이 아닌 경우에만 호출
    - _Requirements: 2.2, 2.3, 6.1_

  - [x] 3.6 `TelnetServer.stop()`에 `cleanup_all()` 호출 추가
    - 서버 종료 시 세션 정리 후 `self.player_session_logger.cleanup_all()` 호출
    - _Requirements: 6.2_

  - [ ]* 3.7 TelnetServer 통합 단위 테스트 작성
    - handle_login, handle_register 후 setup_player_logger 호출 확인
    - handle_game_command에서 log_command 호출 확인
    - remove_session에서 log_session_end + cleanup_player_logger 호출 확인
    - stop에서 cleanup_all 호출 확인
    - 기존 통합 로그(Global_Logger)가 영향받지 않는 것 확인
    - _Requirements: 4.1, 4.2_

- [x] 4. Final checkpoint - 최종 검증
  - mypy + ruff 정적 검사 통과 확인
  - 모든 테스트 통과 확인
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- `*` 표시된 태스크는 선택 사항이며 빠른 MVP를 위해 건너뛸 수 있습니다
- 각 태스크는 특정 요구사항을 참조하여 추적 가능합니다
- 속성 기반 테스트는 hypothesis 라이브러리를 사용합니다
- 체크포인트에서 증분 검증을 수행합니다
- 기존 코드(main.py의 MudEngineFormatter, TelnetServer, TelnetSession)는 최소한으로 수정합니다
