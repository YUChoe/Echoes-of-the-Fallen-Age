# 구현 계획: 아이템 Lua 콜백 시스템

## 개요

아이템 동사 명령어(use, read 등) 실행 시 `configs/items/{template_id}.lua` 스크립트의 콜백 함수를 호출하여 아이템별 커스텀 동작을 구현하는 시스템을 단계적으로 구현한다. 기존 `LuaScriptLoader`를 재사용하고, `ItemLuaCallbackHandler` 클래스를 신규 생성하며, UseCommand/ReadCommand에 Lua 콜백 우선 시도 로직을 삽입한다.

## Tasks

- [x] 1. ItemLuaCallbackHandler 핵심 클래스 구현
  - [x] 1.1 `src/mud_engine/game/item_lua_callback_handler.py` 파일 생성 및 클래스 골격 구현
    - `ItemLuaCallbackHandler` 클래스 정의
    - `__init__`에서 `LuaScriptLoader` 인스턴스를 주입받아 저장
    - `load_item_script(template_id)` 메서드 구현: `configs/items/{template_id}.lua` 파일 읽기, 파일 미존재 시 None 반환
    - `_convert_callback_result(lua_result, locale)` 메서드 구현: Lua 테이블 → Python dict 변환, message 다국어 dict → locale 선택, consume boolean 변환 (기본값 False)
    - `execute_verb_callback(template_id, verb, context)` 메서드 구현: template_id 유효성 확인, 스크립트 로드, `on_{verb}` 함수 동적 호출, 결과 변환 및 반환, 모든 오류 시 None 반환
    - 오류 처리: 설계 문서의 오류 유형별 처리 전략 테이블에 따라 로그 레벨 적용 (DEBUG/ERROR)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 2.6, 3.4, 5.1, 5.2, 5.3, 5.4, 6.1, 6.3, 7.1, 7.2, 7.3, 7.4, 7.5_

  - [ ]* 1.2 Property 1 속성 테스트 작성: 폴백 안전성
    - **Property 1: 폴백 안전성**
    - 임의의 template_id(None, 빈 문자열, 존재하지 않는 ID)와 임의의 동사에 대해 `execute_verb_callback`이 항상 None을 반환하는지 검증
    - hypothesis 라이브러리 사용, 최소 100회 반복
    - **Validates: Requirements 1.3, 1.4, 2.5, 3.3, 5.3**

  - [ ]* 1.3 Property 2 속성 테스트 작성: 범용 동사 콜백 호출
    - **Property 2: 범용 동사 콜백 호출**
    - 임의의 동사 이름과 해당 `on_{verb}` 함수가 정의된 유효한 Lua 스크립트에 대해 non-None 결과 반환 검증
    - hypothesis 라이브러리 사용, 최소 100회 반복
    - **Validates: Requirements 2.1, 3.1, 6.1, 6.3**

  - [ ]* 1.4 Property 3 속성 테스트 작성: 컨텍스트 필수 필드 완전성
    - **Property 3: 컨텍스트 필수 필드 완전성**
    - 임의의 플레이어/아이템/세션 정보에 대해 구성된 Callback_Context가 모든 필수 필드를 포함하는지 검증
    - hypothesis 라이브러리 사용, 최소 100회 반복
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.5**

  - [ ]* 1.5 Property 4 속성 테스트 작성: 콜백 결과 변환 정확성
    - **Property 4: 콜백 결과 변환 정확성**
    - 임의의 Lua 콜백 반환값(다국어 dict, 단일 문자열, consume true/false/nil)과 임의의 locale에 대해 `_convert_callback_result` 변환 정확성 검증
    - hypothesis 라이브러리 사용, 최소 100회 반복
    - **Validates: Requirements 2.2, 2.4, 3.2, 5.1, 5.2, 5.4**

  - [ ]* 1.6 Property 5 속성 테스트 작성: 오류 스크립트 안전 처리
    - **Property 5: 오류 스크립트 안전 처리**
    - 임의의 구문 오류 또는 런타임 오류를 포함하는 Lua 스크립트에 대해 `execute_verb_callback`이 예외를 전파하지 않고 None을 반환하는지 검증
    - hypothesis 라이브러리 사용, 최소 100회 반복
    - **Validates: Requirements 2.6, 3.4, 7.1, 7.2, 7.3**

- [x] 2. 체크포인트 - ItemLuaCallbackHandler 검증
  - mypy + ruff 정적 검사 통과 확인
  - 모든 테스트 통과 확인
  - 사용자에게 질문이 있으면 확인

- [x] 3. UseCommand에 Lua 콜백 통합
  - [x] 3.1 UseCommand 수정: Lua 콜백 우선 시도 로직 삽입
    - `execute` 메서드의 소모품 효과 처리 직전에 Lua 콜백 시도 로직 삽입
    - session에서 `ItemLuaCallbackHandler` 인스턴스 접근 (game_engine 경유)
    - 아이템의 `properties.template_id` 추출
    - Callback_Context 구성: player(id, display_name, locale), item(id, template_id, name, properties), session(locale)
    - `execute_verb_callback(template_id, "use", context)` 호출
    - 결과가 non-None이면: message 표시, consume=true 시 기존 소모 로직(after_use 변환 또는 삭제) 재사용
    - 결과가 None이면: 기존 하드코딩된 소모품 사용 로직(HP/스태미나 회복) 폴백 실행
    - 기존 `is_consumable` 체크 로직 앞에 Lua 콜백 시도를 배치하여, Lua 스크립트가 있는 아이템은 usable_keys 없이도 사용 가능하도록 처리
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 4.1, 4.2, 4.3, 4.5_

  - [ ]* 3.2 UseCommand 단위 테스트 작성
    - Lua 콜백 성공 시 결과 메시지 반환 확인
    - Lua 콜백 None 반환 시 기존 폴백 실행 확인
    - consume=true 시 아이템 소모 확인
    - consume=false 시 아이템 유지 확인
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 4. ReadCommand에 Lua 콜백 통합
  - [x] 4.1 ReadCommand 수정: Lua 콜백 우선 시도 로직 삽입
    - `execute` 메서드의 readable 텍스트 표시 직전에 Lua 콜백 시도 로직 삽입
    - session에서 `ItemLuaCallbackHandler` 인스턴스 접근 (game_engine 경유)
    - 아이템의 `properties.template_id` 추출
    - Callback_Context 구성: player(id, display_name, locale), item(id, template_id, name, properties), session(locale)
    - `execute_verb_callback(template_id, "read", context)` 호출
    - 결과가 non-None이면: message 표시
    - 결과가 None이면: 기존 readable 속성 기반 텍스트 표시 폴백 실행
    - 기존 `_is_readable` 체크 로직 앞에 Lua 콜백 시도를 배치하여, Lua 스크립트가 있는 아이템은 readable 속성 없이도 읽기 가능하도록 처리
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 4.1, 4.2, 4.3, 4.5_

  - [ ]* 4.2 ReadCommand 단위 테스트 작성
    - Lua 콜백 성공 시 결과 메시지 반환 확인
    - Lua 콜백 None 반환 시 기존 readable 텍스트 표시 확인
    - _Requirements: 3.1, 3.2, 3.3_

- [x] 5. 체크포인트 - Command 통합 검증
  - mypy + ruff 정적 검사 통과 확인
  - 모든 테스트 통과 확인
  - 사용자에게 질문이 있으면 확인

- [x] 6. GameEngine 배선 및 샘플 Lua 스크립트 작성
  - [x] 6.1 GameEngine 또는 WorldManager에서 ItemLuaCallbackHandler 인스턴스 생성 및 배선
    - 기존 `LuaScriptLoader` 인스턴스를 주입하여 `ItemLuaCallbackHandler` 생성
    - UseCommand, ReadCommand에서 game_engine 경유로 접근 가능하도록 속성 노출
    - _Requirements: 1.2, 1.5, 6.2_

  - [x] 6.2 샘플 Lua 스크립트 작성
    - `configs/items/health_potion.lua`: `on_use(ctx)` 콜백 정의 (다국어 메시지, consume=true)
    - `configs/items/forgotten_scripture.lua`: `on_read(ctx)` 콜백 정의 (다국어 메시지)
    - _Requirements: 2.1, 3.1_

- [x] 7. 최종 체크포인트 - 전체 시스템 검증
  - mypy + ruff 정적 검사 통과 확인
  - 모든 테스트 통과 확인
  - 사용자에게 질문이 있으면 확인

## Notes

- `*` 표시된 태스크는 선택적이며 빠른 MVP를 위해 건너뛸 수 있음
- 각 태스크는 특정 요구사항을 참조하여 추적 가능성 확보
- 체크포인트에서 점진적 검증 수행
- 속성 테스트는 hypothesis 라이브러리를 사용하여 정확성 속성 검증
- 단위 테스트는 pytest + pytest-mock 사용
- 정적 검사: mypy + ruff 필수 통과
