# Implementation Plan: Lua 스크립트 기반 NPC 대화 시스템

## Overview

lupa 라이브러리를 통해 NPC별 Lua 대화 스크립트를 로드/실행하는 시스템을 기존 DialogueInstance/DialogueManager에 통합한다. 컴포넌트 순서대로 점진적으로 구현하며, 각 단계가 이전 단계 위에 빌드된다.

## Tasks

- [ ] 1. lupa 라이브러리 설치 및 프로젝트 의존성 추가
  - [ ] 1.1 requirements.txt에 `lupa>=2.0` 추가 및 pip install 실행
    - requirements.txt의 Core runtime packages 섹션에 lupa 추가
    - 가상환경에서 `pip install lupa` 실행하여 설치 확인
    - _Requirements: 1.1, 1.2_

- [ ] 2. LuaScriptLoader 클래스 구현
  - [ ] 2.1 `src/mud_engine/game/lua_script_loader.py` 파일 생성
    - `LuaScriptLoader` 클래스 구현: `__init__`, `is_available`, `load_script`, `execute_get_dialogue`, `execute_on_choice`, `_build_lua_context`, `_convert_lua_result`
    - `__init__`에서 `import lupa` try/except로 `_available` 플래그 설정
    - `LuaRuntime(register_eval=False, attribute_filter=...)` 로 샌드박스 초기화
    - `load_script`: `configs/dialogues/{npc_id}.lua` 파일 읽기, 미존재 시 None 반환
    - `execute_get_dialogue`: Lua 스크립트 로드 → `get_dialogue(ctx)` 호출 → 결과 변환
    - `execute_on_choice`: Lua 스크립트 로드 → `on_choice(choice_number, ctx)` 호출 → 결과 변환
    - `_build_lua_context`: Python dict → Lua 테이블 변환
    - `_convert_lua_result`: Lua 테이블 → Python (list[dict], OrderedDict) 변환
    - lupa 미설치/스크립트 미존재/실행 오류 시 None 반환 + 로깅
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.4, 3.4_

  - [ ]* 2.2 LuaScriptLoader 단위 테스트 작성
    - is_available() 확인
    - load_script() 파일 존재/미존재 케이스
    - Lua 스크립트 구문 오류 시 폴백 동작
    - 샌드박스: Lua에서 Python 내부 접근 차단 확인
    - _Requirements: 1.1, 1.2, 1.3, 2.4_

  - [ ]* 2.3 Property 1 속성 테스트: Lua 결과 변환 보존 (Round-trip)
    - **Property 1: Lua 결과 변환 보존**
    - hypothesis로 임의의 text 배열 + choices 테이블 생성 → `_convert_lua_result()` 변환 후 원본 데이터 보존 검증
    - **Validates: Requirements 1.2, 4.1, 4.2**

- [ ] 3. DialogueContext 클래스 구현
  - [ ] 3.1 `src/mud_engine/game/dialogue_context.py` 파일 생성
    - `DialogueContext` 클래스의 `build()` 정적 메서드 구현
    - Player → `username`, `display_name`, `preferred_locale`, `completed_quests`, `quest_progress`
    - Session → `session_id`, `locale`, `current_room_id`, `stamina`
    - Monster → `id`, `name` (dict), `properties`
    - DialogueInstance → `id`, `is_active`, `choice_entity`, `started_at` (ISO format)
    - 모든 값을 순수 dict로 변환 (Python 객체 참조 차단)
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [ ]* 3.2 Property 2 속성 테스트: 컨텍스트 빌드 완전성
    - **Property 2: 컨텍스트 빌드 완전성**
    - hypothesis로 임의의 Player/Session/Monster/DialogueInstance 조합 생성 → `build()` 결과에 모든 필수 키 존재 검증
    - **Validates: Requirements 3.1, 3.2, 3.3**

- [ ] 4. Checkpoint - 기반 컴포넌트 검증
  - mypy + ruff 정적 검사 통과 확인
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. DialogueInstance 수정 (Lua 연동)
  - [ ] 5.1 `src/mud_engine/game/dialogue.py` 수정
    - `lua_loader` 필드 추가 (외부에서 주입, Optional)
    - `get_new_dialogue()` 수정: LuaScriptLoader가 있으면 `execute_get_dialogue(npc_id, context)` 호출, 결과가 있으면 `(dialogue_texts, choice_entity)` 반환, 실패 시 기존 `["..."]` 폴백 유지
    - `get_dialogueby_choice()` 수정: LuaScriptLoader가 있으면 `execute_on_choice(npc_id, choice, context)` 호출, `on_choice`가 nil 반환 시 대화 종료 처리, 기존 Bye 판별 로직도 유지
    - DialogueContext.build()를 호출하여 ctx dict 생성
    - _Requirements: 2.2, 2.3, 4.1, 4.2, 4.3_

  - [ ]* 5.2 Property 3 속성 테스트: 모든 선택지 마지막에 자동 Bye 추가
    - **Property 3: 자동 Bye 추가**
    - hypothesis로 임의의 choices dict 생성 → DialogueInstance가 항상 마지막에 Bye 선택지를 추가하는지 검증
    - choices가 빈 경우에도 `{1: {"en": "Bye.", "ko": "안녕히."}}` 추가 검증
    - **Validates: Requirements 4.3**

- [ ] 6. DialogueManager 수정 (다국어 + LuaScriptLoader 초기화)
  - [ ] 6.1 `src/mud_engine/game/managers/dialogue_manager.py` 수정
    - `__init__`에서 `LuaScriptLoader` 인스턴스 생성 및 보유
    - `create_dialogue()`에서 DialogueInstance에 `lua_loader` 참조 전달
    - `send_dialogue_message()` 수정: choice_entity 값이 dict인 경우 `locale` 기반 텍스트 선택, 기존 str 값도 하위 호환성 유지
    - dialogue_texts(list[dict])에서도 locale 기반 텍스트 선택
    - 자동 Bye 선택지 추가 로직: choices 마지막 번호 + 1에 `{"en": "Bye.", "ko": "안녕히."}` 추가
    - _Requirements: 4.3, 4.4, 5.5_

- [ ] 7. Checkpoint - 핵심 로직 검증
  - mypy + ruff 정적 검사 통과 확인
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. 샘플 Veteran Guard Lua 스크립트 작성
  - [ ] 8.1 `configs/dialogues/3914fbe8-c8a9-493a-b451-1084ee4d6d2a.lua` 파일 생성
    - `get_dialogue(ctx)`: 초기 인사말 (display_name 포함) + "Who are you?" 선택지
    - `on_choice(choice_number, ctx)`: choice 1 → 자기소개 텍스트 (choices 없음 → 자동 Bye), 그 외 → nil (대화 종료)
    - 모든 텍스트는 다국어 dict `{en = "...", ko = "..."}` 형식
    - Bye 선택지는 스크립트에서 명시하지 않음 (자동 추가)
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [ ]* 8.2 Property 4 속성 테스트: 컨텍스트 변수의 대화 텍스트 반영
    - **Property 4: 컨텍스트 변수의 대화 텍스트 반영**
    - hypothesis로 임의의 display_name 생성 → Veteran Guard 스크립트의 `get_dialogue(ctx)` 실행 → 반환 텍스트에 display_name 포함 검증
    - **Validates: Requirements 5.4**

- [ ] 9. Telnet MCP E2E 테스트
  - [ ] 9.1 서버 실행 후 Telnet MCP로 Veteran Guard 대화 전체 흐름 테스트
    - 로그인 (player5426/test1234) → Veteran Guard가 있는 방으로 이동
    - `talk <npc_number>` → 초기 인사말 + 선택지 표시 확인
    - `talk 1` (Who are you?) → 후속 대화 텍스트 + [1] Bye 선택지 확인
    - `talk 1` (Bye) → 대화 종료 + 세션 원래 상태 복원 확인
    - Lua 스크립트 미존재 NPC에게 talk → silent_stare 폴백 확인
    - _Requirements: 2.2, 2.3, 4.1, 4.2, 4.3, 4.4, 5.2, 5.3_

- [ ] 10. Final checkpoint - 전체 검증
  - mypy + ruff 정적 검사 통과 확인
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- 설계 문서의 Python 코드를 사용하므로 구현 언어는 Python
- lupa 미설치/스크립트 미존재/실행 오류 시 기존 silent_stare 폴백 유지
- 모든 선택지 마지막에 자동 Bye 추가 (Lua 스크립트에서 Bye 명시 불필요)
- 다국어 dict `{en: "...", ko: "..."}` 형식, DialogueManager에서 locale 선택
- Property 테스트는 hypothesis 라이브러리 사용
