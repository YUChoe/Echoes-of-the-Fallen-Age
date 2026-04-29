# 구현 계획

- [ ] 1. 버그 조건 탐색 테스트 작성
  - **Property 1: Bug Condition** - get_help() locale 무시 버그
  - **CRITICAL**: 이 테스트는 수정 전 코드에서 반드시 FAIL해야 함 — 실패가 버그 존재를 확인함
  - **DO NOT**: 테스트가 실패할 때 테스트나 코드를 수정하지 말 것
  - **NOTE**: 이 테스트는 기대 동작을 인코딩함 — 수정 후 PASS하면 버그가 해결된 것
  - **GOAL**: 버그를 재현하는 counterexample을 확인
  - **Scoped PBT Approach**: locale="en"에서 get_help() 호출 시 한국어 문자열이 반환되는 구체적 케이스에 집중
  - Bug Condition: `isBugCondition(input)` where input.method == "get_help" AND input.locale != "ko" AND command.description IS hardcoded Korean string
  - 테스트 내용:
    - BaseCommand.get_help() 호출 시 locale 파라미터가 없어 항상 한국어 description/usage 반환 확인
    - locale="en"에서 get_help() 호출 시 "사용법:" 한국어 레이블 포함 확인
    - get_help_text(command_name="attack", locale="en") 호출 시 command.get_help()가 한국어 반환 확인
    - attack_command에서 self.usage가 한국어 "attack <몹id>" 문자열인 것 확인
  - Expected Behavior (수정 후 PASS 조건):
    - get_help("en") 호출 시 영어 description/usage 반환
    - "Usage:" 영어 레이블 사용
    - get_help_text(command_name="attack", locale="en") 호출 시 영어 도움말 반환
  - 수정 전 코드에서 테스트 실행 → FAIL 예상 (버그 존재 확인)
  - counterexample 문서화: "get_help() returns '공격합니다' instead of 'Attack a monster' for locale=en"
  - 테스트 완료 후 태스크 완료 처리 (실패 문서화 포함)
  - _Requirements: 1.1, 1.4, 2.1, 2.4_

- [ ] 2. 보존 속성 테스트 작성 (수정 전)
  - **Property 2: Preservation** - 한국어 locale 및 비locale 메서드 동작 보존
  - **IMPORTANT**: observation-first 방법론 준수
  - 수정 전 코드에서 관찰:
    - locale="ko"에서 get_help() 결과 관찰 및 기록
    - matches(), validate_args() 메서드 동작 관찰
    - create_error_result(), create_success_result() 메서드 동작 관찰
    - get_help_text(is_admin=False, locale="ko") 전체 목록에서 cmd.*.desc 번역 키 우선 사용 확인
  - Property-based 테스트 작성:
    - 임의의 명령어에서 locale="ko" 시 get_help("ko") 결과가 기존 get_help() 결과와 동일
    - matches(name) 결과가 수정 전후 동일
    - validate_args(args, min_args, max_args) 결과가 수정 전후 동일
    - get_help_text(locale="ko") 전체 목록에서 기존 번역 키 우선 사용 동작 유지
  - 수정 전 코드에서 테스트 실행 → PASS 예상 (기존 동작 확인)
  - 테스트 완료 후 태스크 완료 처리 (통과 확인)
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 3. Command I18N Description 버그 수정

  - [x] 3.1 BaseCommand.get_help(locale) 시그니처 변경 및 get_localized_usage(locale) 추가
    - `get_help()` → `get_help(locale: str = "ko")` 시그니처 변경
    - LocalizationManager를 통해 `cmd.{self.name}.desc` 키로 description 조회, 없으면 self.description 폴백
    - `cmd.{self.name}.usage` 키로 usage 조회, 없으면 self.usage 폴백
    - "사용법:"/"Usage:" 레이블을 locale에 따라 분기
    - "별칭:"/"Aliases:" 레이블을 locale에 따라 분기
    - `get_localized_usage(locale: str = "ko")` 헬퍼 메서드 추가: cmd.{self.name}.usage 번역 키 조회, 없으면 self.usage 폴백
    - _Bug_Condition: isBugCondition(input) where input.method == "get_help" AND input.locale != "ko"_
    - _Expected_Behavior: get_help(locale) returns localized description/usage/labels_
    - _Preservation: locale="ko" 시 기존과 동일한 한국어 결과 반환_
    - _Requirements: 1.1, 1.4, 2.1, 2.4, 3.1_

  - [x] 3.2 CommandProcessor.get_help_text()에서 command.get_help(locale) 호출로 변경
    - `command.get_help()` → `command.get_help(locale)` 변경
    - _Bug_Condition: isBugCondition(input) where input.method == "get_help_text" AND command_name IS specified_
    - _Expected_Behavior: 개별 명령어 조회 시 locale에 맞는 도움말 반환_
    - _Preservation: 관리자 전용 명령어 필터링 로직 변경 없음_
    - _Requirements: 1.2, 2.2, 3.5_

  - [x] 3.3 attack_command.py, talk_command.py에서 self.usage → self.get_localized_usage(locale) 변경
    - attack_command.py: `self.I18N.get_message("combat.target_not_found_usage", locale, usage=self.usage)` → `usage=self.get_localized_usage(locale)`
    - talk_command.py: 동일 패턴 적용
    - _Bug_Condition: isBugCondition(input) where input.method == "execute" AND error_message CONTAINS command.usage_
    - _Expected_Behavior: 에러 메시지에 locale에 맞는 usage 문자열 포함_
    - _Preservation: execute() 결과의 result_type, data 필드 변경 없음_
    - _Requirements: 1.3, 2.3, 3.3_

  - [x] 3.4 data/translations/command.json에 usage 번역 키 추가
    - `cmd.attack.usage`: `{"en": "attack <mob_id>", "ko": "attack <몹id>"}`
    - `cmd.talk.usage`: `{"en": "talk <mob_id>", "ko": "talk <Mob id>"}`
    - _Requirements: 2.1, 2.3_

  - [x] 3.5 정적 검사 통과 확인
    - mypy src/ 통과 확인
    - ruff check src/ 통과 확인
    - _Requirements: 전체_

  - [x] 3.6 버그 조건 탐색 테스트 통과 확인
    - **Property 1: Expected Behavior** - get_help(locale) 다국어 반환
    - **IMPORTANT**: 태스크 1에서 작성한 동일 테스트를 재실행 — 새 테스트 작성 금지
    - 수정 후 코드에서 버그 조건 탐색 테스트 실행
    - **EXPECTED OUTCOME**: 테스트 PASS (버그 수정 확인)
    - _Requirements: 2.1, 2.4_

  - [x] 3.7 보존 속성 테스트 통과 확인
    - **Property 2: Preservation** - 한국어 locale 및 비locale 메서드 동작 보존
    - **IMPORTANT**: 태스크 2에서 작성한 동일 테스트를 재실행 — 새 테스트 작성 금지
    - 수정 후 코드에서 보존 속성 테스트 실행
    - **EXPECTED OUTCOME**: 테스트 PASS (회귀 없음 확인)
    - 모든 테스트가 수정 후에도 통과하는지 확인
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 4. Checkpoint - 모든 테스트 통과 확인
  - 전체 테스트 스위트 실행하여 모든 테스트 통과 확인
  - mypy + ruff 정적 검사 최종 통과 확인
  - 문제 발생 시 사용자에게 질문
