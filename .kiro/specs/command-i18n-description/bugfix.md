# Bugfix Requirements Document

## Introduction

BaseCommand 클래스의 `description`과 `usage` 필드가 단일 문자열(주로 한국어)로 하드코딩되어 있어, 플레이어의 locale 설정(en/ko)에 따라 적절한 언어로 표시되지 않는 문제를 수정한다.

현재 `data/translations/command.json`에 `cmd.*.desc` 키로 en/ko 번역이 이미 존재하지만, BaseCommand 자체의 `description`/`usage` 필드는 단일 문자열이다. `processor.py`의 `get_help_text()`에서는 번역 키를 먼저 시도하고 폴백으로 `command.description`을 사용하지만, `base.py`의 `get_help()` 메서드는 locale 파라미터 없이 단일 문자열만 반환하며, 개별 명령어에서 `self.usage`를 직접 참조하는 곳도 locale 구분 없이 사용된다.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN 플레이어의 locale이 "en"이고 `get_help()` 메서드가 호출될 THEN 시스템은 한국어로 하드코딩된 description과 usage를 반환한다

1.2 WHEN 플레이어의 locale이 "en"이고 `processor.py`의 `get_help_text()`에서 `cmd.*.desc` 번역 키가 존재하지 않는 명령어의 설명을 표시할 THEN 시스템은 한국어 `command.description` 폴백 값을 영어 사용자에게 표시한다

1.3 WHEN 개별 명령어(예: attack_command, talk_command)에서 `self.usage`를 에러 메시지에 포함하여 반환할 THEN 시스템은 locale과 무관하게 한국어 usage 문자열을 표시한다

1.4 WHEN `base.py`의 `get_help()` 메서드가 호출될 THEN 시스템은 locale 파라미터를 받지 않아 항상 "사용법:" 이라는 한국어 레이블과 함께 단일 언어 문자열을 반환한다

### Expected Behavior (Correct)

2.1 WHEN 플레이어의 locale이 "en"이고 `get_help()` 메서드가 호출될 THEN 시스템 SHALL 영어 description과 usage를 반환한다

2.2 WHEN 플레이어의 locale이 "en"이고 `processor.py`의 `get_help_text()`에서 명령어 설명을 표시할 THEN 시스템 SHALL 번역 키 또는 명령어 자체의 영어 description을 표시한다

2.3 WHEN 개별 명령어에서 `self.usage`를 에러 메시지에 포함하여 반환할 THEN 시스템 SHALL 세션의 locale에 맞는 usage 문자열을 표시한다

2.4 WHEN `get_help()` 메서드가 호출될 THEN 시스템 SHALL locale 파라미터를 받아 해당 언어의 description, usage, 레이블("사용법:"/"Usage:")을 반환한다

### Unchanged Behavior (Regression Prevention)

3.1 WHEN 플레이어의 locale이 "ko"일 THEN 시스템 SHALL CONTINUE TO 기존과 동일한 한국어 description과 usage를 표시한다

3.2 WHEN `data/translations/command.json`에 `cmd.*.desc` 번역 키가 존재하는 명령어의 도움말을 표시할 THEN 시스템 SHALL CONTINUE TO 해당 번역 키의 값을 우선 사용한다

3.3 WHEN 명령어의 `execute()` 메서드가 호출될 THEN 시스템 SHALL CONTINUE TO 기존과 동일한 CommandResult를 반환한다

3.4 WHEN 명령어의 `matches()`, `validate_args()`, `create_error_result()`, `create_success_result()` 메서드가 호출될 THEN 시스템 SHALL CONTINUE TO 기존과 동일하게 동작한다

3.5 WHEN `processor.py`의 `get_help_text()`에서 관리자 전용 명령어 필터링이 수행될 THEN 시스템 SHALL CONTINUE TO 기존과 동일하게 권한에 따라 필터링한다
