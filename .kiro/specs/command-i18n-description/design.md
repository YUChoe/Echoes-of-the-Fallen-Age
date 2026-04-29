# Command I18N Description 버그픽스 설계

## Overview

BaseCommand 클래스의 `description`과 `usage` 필드가 단일 문자열(주로 한국어)로 하드코딩되어 있어, 플레이어의 locale에 따라 적절한 언어로 표시되지 않는 문제를 수정한다.

기존 번역 시스템(`data/translations/command.json`의 `cmd.*.desc` 키)을 최대한 활용하는 방향으로 설계한다. 새로운 필드(`description_en`/`description_ko`)를 추가하는 대신, 기존 `LocalizationManager`를 통해 번역 키 기반으로 description과 usage를 조회하도록 `get_help(locale)` 시그니처를 변경하고, 개별 명령어에서 `self.usage`를 직접 에러 메시지에 포함하는 패턴을 번역 키 기반으로 전환한다.

## Glossary

- Bug_Condition (C): `get_help()` 또는 `self.usage`가 locale 없이 호출되어 단일 언어 문자열이 반환되는 조건
- Property (P): locale에 맞는 description/usage 문자열이 반환되는 동작
- Preservation: 기존 한국어 사용자 경험, `execute()` 결과, `matches()`/`validate_args()` 동작이 변경되지 않는 것
- `get_help()`: `BaseCommand.get_help()` — 명령어 도움말 텍스트를 반환하는 메서드 (`src/mud_engine/commands/base.py`)
- `get_help_text()`: `CommandProcessor.get_help_text()` — 전체 또는 개별 명령어 도움말을 생성하는 메서드 (`src/mud_engine/commands/processor.py`)
- `LocalizationManager`: `src/mud_engine/core/localization.py`의 다국어 메시지 관리 클래스
- `cmd.*.desc`: `data/translations/command.json`에 정의된 명령어 설명 번역 키 패턴
- `cmd.*.usage`: 신규 추가할 명령어 사용법 번역 키 패턴

## Bug Details

### Bug Condition

`get_help()` 메서드가 locale 파라미터 없이 호출되거나, 개별 명령어에서 `self.usage`를 에러 메시지에 직접 포함할 때, 플레이어의 locale과 무관하게 한국어 하드코딩 문자열이 반환된다.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type { method: str, locale: str }
  OUTPUT: boolean

  CASE 1 - get_help 호출:
    RETURN input.method == "get_help"
           AND input.locale != "ko"
           AND command.description IS hardcoded Korean string

  CASE 2 - self.usage 직접 참조:
    RETURN input.method == "execute"
           AND input.locale != "ko"
           AND command.usage IS hardcoded Korean string
           AND error_message CONTAINS command.usage

  CASE 3 - get_help_text 개별 명령어 조회:
    RETURN input.method == "get_help_text"
           AND input.locale != "ko"
           AND command_name IS specified
           AND command.get_help() returns Korean-only string
END FUNCTION
```

### Examples

- `get_help()` 호출 시 locale="en"인 플레이어에게 `"공격합니다"` (한국어 description)이 반환됨 → 기대값: `"Attack a monster"`
- `attack_command`에서 대상을 찾지 못했을 때 `self.usage`가 `"attack <몹id>"`로 에러 메시지에 포함됨 → locale="en"인 플레이어에게도 한국어 usage가 표시됨
- `get_help_text(command_name="attack", locale="en")` 호출 시 `command.get_help()`가 한국어 문자열을 반환 → 기대값: 영어 도움말
- `get_help()` 호출 시 "사용법:" 레이블이 항상 한국어로 표시됨 → locale="en"이면 "Usage:"로 표시되어야 함

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviours:**
- locale="ko"인 플레이어에게는 기존과 동일한 한국어 description/usage가 표시된다
- `data/translations/command.json`의 `cmd.*.desc` 번역 키가 존재하는 명령어는 `get_help_text()` 전체 목록에서 해당 번역 값이 우선 사용된다
- `execute()` 메서드의 CommandResult 반환값(result_type, data 등)은 변경되지 않는다
- `matches()`, `validate_args()`, `create_error_result()`, `create_success_result()` 메서드는 기존과 동일하게 동작한다
- `get_help_text()`의 관리자 전용 명령어 필터링 로직은 변경되지 않는다

**Scope:**
locale 파라미터가 관여하지 않는 모든 메서드 호출은 이 수정에 영향을 받지 않는다. 구체적으로:
- 명령어 등록/해제 (`register_command`, `unregister_command`)
- 명령어 매칭 (`matches`)
- 인수 검증 (`validate_args`)
- 전투/대화 숫자 변환 (`_convert_combat_number_to_command`, `_convert_dialogue_number_to_command`)

## Hypothesized Root Cause

1. `BaseCommand.get_help()` 시그니처에 locale 파라미터가 없음: 메서드가 `self.description`과 `self.usage`를 직접 반환하며, 이 값들은 `__init__`에서 단일 한국어 문자열로 설정됨

2. `CommandProcessor.get_help_text()`에서 개별 명령어 조회 시 `command.get_help()`를 locale 없이 호출: line 396에서 `return command.get_help()`로 호출하여 locale 정보가 전달되지 않음

3. 개별 명령어에서 `self.usage`를 에러 메시지에 직접 포함: `attack_command.py`(line 91)와 `talk_command.py`(line 96)에서 `self.I18N.get_message("combat.target_not_found_usage", locale, usage=self.usage)`로 호출하는데, `self.usage`가 한국어 하드코딩 문자열임

4. `get_help()` 내부의 "사용법:" 레이블이 한국어로 하드코딩: line 102에서 `help_text += f"\n사용법: {self.usage}"`로 항상 한국어 레이블 사용

## Correctness Properties

Property 1: Bug Condition - locale에 따른 get_help 다국어 반환

_For any_ 명령어와 locale 조합에서 `get_help(locale)` 호출 시, 해당 명령어의 번역 키(`cmd.{name}.desc`, `cmd.{name}.usage`)가 `command.json`에 존재하면 해당 locale의 번역 값을 반환하고, 존재하지 않으면 `self.description`/`self.usage` 폴백 값을 반환 SHALL.

**Validates: Requirements 2.1, 2.4**

Property 2: Bug Condition - self.usage 에러 메시지의 다국어 반환

_For any_ 명령어 실행에서 `self.usage`가 에러 메시지에 포함될 때, 세션의 locale에 맞는 usage 문자열이 사용 SHALL.

**Validates: Requirements 2.3**

Property 3: Preservation - 한국어 locale 동작 유지

_For any_ locale="ko"인 입력에서, 수정된 `get_help("ko")`와 에러 메시지의 usage 문자열은 기존 하드코딩된 한국어 값과 동일한 결과를 반환 SHALL.

**Validates: Requirements 3.1, 3.2**

Property 4: Preservation - execute 결과 및 비locale 메서드 동작 유지

_For any_ 명령어 호출에서 `matches()`, `validate_args()`, `create_error_result()`, `create_success_result()` 메서드는 수정 전과 동일한 결과를 반환 SHALL.

**Validates: Requirements 3.3, 3.4, 3.5**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File**: `src/mud_engine/commands/base.py`

**Function**: `get_help()`

**Specific Changes**:
1. `get_help()` 시그니처에 `locale: str = "ko"` 파라미터 추가
2. `LocalizationManager`를 통해 `cmd.{self.name}.desc` 키로 description 조회, 없으면 `self.description` 폴백
3. `cmd.{self.name}.usage` 키로 usage 조회, 없으면 `self.usage` 폴백
4. "사용법:"/"Usage:" 레이블을 locale에 따라 분기
5. "별칭:"/"Aliases:" 레이블을 locale에 따라 분기

**File**: `src/mud_engine/commands/base.py`

**Function**: `get_localized_usage()` (신규 추가)

**Specific Changes**:
1. locale을 받아 `cmd.{self.name}.usage` 번역 키로 usage 조회하는 헬퍼 메서드 추가
2. 번역 키가 없으면 `self.usage` 폴백
3. 개별 명령어에서 `self.usage` 대신 `self.get_localized_usage(locale)` 호출

**File**: `src/mud_engine/commands/processor.py`

**Function**: `get_help_text()`

**Specific Changes**:
1. line 396의 `command.get_help()` 호출을 `command.get_help(locale)` 로 변경

**File**: `data/translations/command.json`

**Specific Changes**:
1. `self.usage`를 직접 에러 메시지에 포함하는 명령어들(`attack`, `talk`)의 usage 번역 키 추가
   - `cmd.attack.usage`: `{"en": "Usage: attack <mob_id>", "ko": "사용법: attack <몹id>"}`
   - `cmd.talk.usage`: `{"en": "Usage: talk <mob_id>", "ko": "사용법: talk <Mob id>"}`

**File**: `src/mud_engine/commands/combat/attack_command.py`

**Specific Changes**:
1. `self.usage` 직접 참조를 `self.get_localized_usage(locale)`로 변경 (line 91)

**File**: `src/mud_engine/commands/dialogue/talk_command.py`

**Specific Changes**:
1. `self.usage` 직접 참조를 `self.get_localized_usage(locale)`로 변경 (line 96)

## Testing Strategy

### Validation Approach

테스트 전략은 두 단계로 진행한다: 먼저 수정 전 코드에서 버그를 재현하는 counterexample을 확인하고, 수정 후 버그가 해결되었으며 기존 동작이 보존되는지 검증한다.

### Exploratory Bug Condition Checking

**Goal**: 수정 전 코드에서 버그를 재현하여 root cause를 확인/반박한다.

**Test Plan**: `get_help()` 메서드와 `self.usage` 참조 패턴을 locale="en" 조건에서 호출하여 한국어 문자열이 반환되는지 확인한다.

**Test Cases**:
1. `get_help()` 한국어 반환 테스트: AttackCommand의 `get_help()` 호출 시 한국어 description이 반환됨 (수정 전 코드에서 실패 예상)
2. `self.usage` 에러 메시지 테스트: locale="en"에서 attack 명령어의 에러 메시지에 한국어 usage가 포함됨 (수정 전 코드에서 실패 예상)
3. `get_help_text()` 개별 조회 테스트: locale="en"에서 `get_help_text("attack")` 호출 시 한국어 도움말 반환 (수정 전 코드에서 실패 예상)
4. "사용법:" 레이블 테스트: locale="en"에서 `get_help()` 호출 시 "사용법:" 한국어 레이블 포함 (수정 전 코드에서 실패 예상)

**Expected Counterexamples**:
- `get_help()` 반환값에 한국어 문자열 포함
- 에러 메시지의 `{usage}` 자리에 한국어 usage 문자열 삽입

### Fix Checking

**Goal**: 버그 조건이 성립하는 모든 입력에서 수정된 함수가 올바른 동작을 하는지 검증한다.

**Pseudocode:**
```
FOR ALL (command, locale) WHERE isBugCondition(command, locale) DO
  result := command.get_help(locale)
  ASSERT result CONTAINS localized_description(command.name, locale)
  ASSERT result CONTAINS localized_usage_label(locale)
  ASSERT result CONTAINS localized_usage(command.name, locale)
END FOR
```

### Preservation Checking

**Goal**: 버그 조건이 성립하지 않는 모든 입력에서 수정된 함수가 기존과 동일한 결과를 반환하는지 검증한다.

**Pseudocode:**
```
FOR ALL (command, locale) WHERE NOT isBugCondition(command, locale) DO
  ASSERT command.get_help(locale) == command.get_help_original()
END FOR
```

**Testing Approach**: Property-based testing을 통해 다양한 명령어/locale 조합에서 보존 속성을 검증한다.

**Test Cases**:
1. 한국어 locale 보존: locale="ko"에서 `get_help("ko")` 결과가 기존 `get_help()` 결과와 동일
2. execute 결과 보존: 명령어 실행 결과의 `result_type`, `data` 필드가 변경되지 않음
3. matches/validate_args 보존: 명령어 매칭과 인수 검증이 기존과 동일하게 동작
4. get_help_text 전체 목록 보존: locale="ko"에서 전체 명령어 목록의 description이 기존과 동일

### Unit Tests

- `get_help(locale)` 메서드의 locale별 반환값 검증
- `get_localized_usage(locale)` 메서드의 번역 키 조회 및 폴백 검증
- `get_help_text(command_name, locale)` 개별 명령어 조회의 locale 전달 검증
- 번역 키가 없는 명령어의 폴백 동작 검증

### Property-Based Tests

- 임의의 명령어 이름과 locale 조합에서 `get_help(locale)` 반환값이 해당 locale의 문자열을 포함하는지 검증
- 임의의 명령어에서 `get_localized_usage(locale)` 반환값이 번역 키 존재 시 번역 값, 미존재 시 `self.usage`와 동일한지 검증
- locale="ko"에서 모든 명령어의 `get_help("ko")` 결과가 기존 하드코딩 값과 동일한지 검증

### Integration Tests

- Telnet 세션에서 locale="en" 플레이어가 `help attack` 입력 시 영어 도움말 표시
- locale="en" 플레이어가 `attack` 명령어에서 대상 미지정 에러 시 영어 usage 표시
- locale="ko" 플레이어의 기존 도움말 경험이 변경되지 않음
