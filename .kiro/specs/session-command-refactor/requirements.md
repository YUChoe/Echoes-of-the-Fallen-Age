# Requirements Document

## Introduction

이 스펙은 Python MUD 엔진(Echoes of the Fallen Age)의 세션 계층(`server/telnet_session.py` 등)과 명령어 시스템(`commands/`)을 리팩토링하기 위한 요구사항을 정의한다.

이 리팩토링은 두 가지 핵심 목적을 가진다.

- 1차 목적 — 유지보수 용이성(Maintainability): 명령어를 가능한 한 분리(한 명령어 = 한 Command_Module/클래스, Command_Category 하위 디렉토리)하고, 세션 클래스의 책임을 분리하며, 실행 인터페이스와 등록 방식을 일관화하여 내부 구조의 이해·수정·확장 비용을 낮춘다. 이것이 본 리팩토링의 명시적 1차 목적이다.
- 2차 목적 — 즉시(증분) 메시지 전달(Incremental_Delivery): 플레이어에게 보내는 메시지를 각 상황이 발생하는 시점에 즉시 세션으로 전달하도록 메시지 전달 모델을 변경한다. 현재 구조는 명령어가 `CommandResult.message`에 출력 텍스트를 담아 반환하고 `CommandManager._send_command_result`가 명령 처리 종료 후 한 번에 전송한다. 변경 후에는 명령어가 Output_Port를 통해 각 출력을 발생 시점에 직접·즉시 전송하고, 반환값은 제어 흐름(성공/실패, 브로드캐스트 지시, 연결 종료 등)에 집중한다.

대부분의 변경은 외부에서 관찰 가능한 출력(Telnet 응답 텍스트, ANSI 색상, 메시지 내용·순서, 에러 메시지)을 보존하는 동작 보존(behaviour-preserving) 방식으로 수행한다. 단, 메시지 전달 모델 변경(2차 목적)은 의도된 아키텍처 변경이며, 메시지의 내용·의미·상대 순서는 보존하되 전달 타이밍이 "명령 종료 후 일괄"에서 "각 상황 즉시"로 바뀌는 것은 허용·요구된다.

코드 분석으로 다음 문제가 확인되었으며 본 문서의 근거로 사용한다.

- 세션 계층: "Session" 개념이 3중으로 혼재(`game/models/session.py`의 레거시 `Session`, `server/telnet_session.py`의 `TelnetSession`, `core/types.py`의 `SessionType`), `TelnetSession`이 전송·프로토콜·표현·도메인 상태 4책임을 혼재한 god object(~700줄), 표현 로직과 팩션 판정의 하드코딩 중복, 반복 보일러플레이트와 로깅 스팸.
- 명령어 계층: 디렉토리 구성 불일치(하위 디렉토리 vs 평면 파일 vs 집합 파일 혼재, 중복/사문화 모듈), 실행 패턴 이원화(`BaseCommand.execute` vs 전투 명령어의 생성자 주입 + processor 직접 인스턴스화), 매직넘버 기반 숫자 입력 매핑, processor의 라우팅 외 정책 과다, 자동 발견 없는 거대 수동 등록 메서드.

이 리팩토링은 유지보수 용이성을 1차 목적으로, 즉시 메시지 전달 모델 도입을 2차 목적으로 한다. 메시지 전달 타이밍 변경을 제외한 모든 변경은 동작 보존을 제약으로 하며, 모든 변경은 정적 검사(mypy + ruff) 통과와 telnet-mcp 기반 회귀 검증으로 확인 가능해야 한다.

## Glossary

- **Codebase**: 본 리팩토링 대상이 되는 MUD 엔진 소스 트리(`src/mud_engine/`).
- **Maintainer**: 본 리팩토링을 수행하고 검증하는 개발자.
- **Session_Layer**: 클라이언트 연결당 상태와 입출력을 담당하는 코드 영역(현재 `server/telnet_session.py`).
- **Telnet_Session**: 실제 런타임에서 사용되는 세션 클래스(`TelnetSession`).
- **Legacy_Session**: `game/models/session.py`에 정의된 WebSocket 시절의 미사용 추정 `Session` dataclass.
- **Session_Type_Alias**: `core/types.py`의 `SessionType` 타입 별칭.
- **Transport_Component**: 바이트 단위 입출력(reader/writer, send_text, read_line, echo, close)을 담당하는 분리된 구성 요소.
- **Telnet_Protocol_Component**: Telnet IAC 협상 및 명령어 필터링(`_filter_telnet_commands`)을 담당하는 분리된 구성 요소.
- **View_Component**: 메시지 딕셔너리를 Telnet 텍스트로 변환하는 표현 로직(`_format_message`, `_format_room_info`, ANSI 적용)을 담당하는 분리된 구성 요소.
- **Session_State**: 도메인 상태(player, current_room_id, 전투/대화 상태, stamina, following_player, locale 등)를 담는 구성 요소.
- **Faction_Manager**: 팩션 간 우호/중립/적대 관계를 판정하는 기존 매니저.
- **Command_System**: 명령어 정의·등록·실행을 담당하는 코드 영역(`commands/`).
- **Base_Command**: 모든 명령어의 추상 기반 클래스(`BaseCommand`).
- **Command_Processor**: 명령어 파싱·라우팅·실행을 담당하는 클래스(`CommandProcessor`).
- **Command_Registry**: 명령어 인스턴스를 등록·조회하는 책임(현재 `CommandManager._setup_commands` + `CommandProcessor.commands`).
- **Command_Module**: 단일 명령어 클래스를 담는 소스 파일.
- **Command_Category**: 명령어가 속하는 분류(basic, admin, combat, dialogue, interaction, object 등).
- **Numeric_Input_Map**: 전투/대화 중 숫자 입력을 명령어 이름으로 변환하는 매핑 데이터.
- **Command_Result**: 명령어 실행의 제어 흐름 결과를 표현하는 반환값(현재 `CommandResult` dataclass). 메시지 전달 모델 변경 후에는 출력 텍스트 누적 책임을 제거하고 성공/실패, 브로드캐스트 지시, 연결 종료 등 제어 신호에 집중한다.
- **Output_Port**: 명령어가 플레이어에게 보낼 메시지를 발생 시점에 직접·즉시 전송하기 위해 사용하는 즉시 출력 채널(세션의 send 계열 인터페이스 또는 이를 추상화한 포트).
- **Message_Delivery_Model**: 명령어 출력이 플레이어 세션으로 전달되는 방식. 현재는 명령 종료 후 `CommandResult.message`를 일괄 전송하는 모델이며, 변경 후에는 각 출력을 발생 시점에 즉시 전송하는 Incremental_Delivery 모델이다.
- **Incremental_Delivery**: 명령어 실행 도중 발생하는 각 출력(여러 줄/여러 이벤트)을 발생 시점에 순차적으로 즉시 Output_Port로 전송하고, 명령 종료 시점에 누적 일괄 전송하지 않는 전달 방식.
- **Observable_Behaviour**: Telnet 클라이언트가 관찰 가능한 출력(응답 텍스트, ANSI 색상 코드, 메시지의 내용과 상대 순서, 에러 메시지, 명령어 인식 결과). 메시지의 전달 타이밍(일괄 vs 즉시)은 Observable_Behaviour의 보존 대상에서 제외하며 Message_Delivery_Model 요구사항이 별도로 규율한다.
- **Regression_Suite**: telnet-mcp를 사용해 대표 시나리오(look, 방 정보, 전투, 대화, 권한, 미인증, 알 수 없는 명령어)를 실행하는 회귀 검증 절차.
- **Static_Check**: mypy 타입 검사와 ruff 린트 검사.

## Requirements

### Requirement 1: 동작 보존 (최상위 제약, 전달 타이밍 예외)

**User Story:** 운영자로서, 나는 리팩토링 전후로 게임 동작이 동일하게 유지되기를 원한다. 그래야 사용자에게 회귀 없이 내부 구조를 개선하고 메시지 전달 모델만 의도적으로 변경할 수 있다.

#### Acceptance Criteria

1. THE Codebase SHALL 리팩토링 전후로 동일한 입력에 대해 동일한 메시지 내용과 메시지 간 상대 순서를 동일한 ANSI 색상으로 산출한다.
2. WHEN Regression_Suite가 look, 방 정보 표시, 전투, 대화, 관리자 권한, 미인증 접근, 알 수 없는 명령어 시나리오에 대해 실행되면, THE Codebase SHALL 리팩토링 이전과 동일한 응답 텍스트 집합과 메시지 간 상대 순서를 산출한다.
3. THE Codebase SHALL 메시지의 전달 타이밍을 "명령 종료 후 일괄 전송"에서 "각 상황 발생 시점 즉시 전송"으로 변경하며, 이 타이밍 변경은 의도된 변경으로서 동작 보존 위반으로 간주하지 않는다.
4. THE Codebase SHALL 리팩토링 과정에서 게임 규칙, 밸런스, 데이터 스키마, 번역 키를 변경하지 않는다.
5. THE Codebase SHALL 리팩토링 과정에서 신규 게임 기능을 추가하지 않는다.
6. THE Codebase SHALL 리팩토링 과정에서 WebSocket 전송 경로를 재도입하지 않는다.

### Requirement 2: 세션 책임 분리

**User Story:** Maintainer로서, 나는 세션 클래스의 책임이 분리되기를 원한다. 그래야 각 관심사를 독립적으로 이해하고 수정할 수 있다.

#### Acceptance Criteria

1. THE Session_Layer SHALL 전송 책임을 Transport_Component로 분리한다.
2. THE Session_Layer SHALL Telnet 프로토콜 협상 및 필터링 책임을 Telnet_Protocol_Component로 분리한다.
3. THE Session_Layer SHALL 메시지를 텍스트로 변환하는 표현 책임을 View_Component로 분리한다.
4. THE Session_Layer SHALL 도메인 상태 보유 책임을 Session_State로 분리한다.
5. WHILE 책임 분리가 부분적으로 진행 중인 모든 중간 상태에서, THE Session_Layer SHALL 분리 이전과 동일한 Observable_Behaviour를 유지한다.
6. THE View_Component SHALL 팩션 우호/중립/적대 판정을 Faction_Manager에 위임한다.

### Requirement 3: 세션 타입 단일화 및 깨진 타입 임포트 정리

**User Story:** Maintainer로서, 나는 세션 타입이 하나로 통일되고 깨진 타입 임포트가 정리되기를 원한다. 그래야 타입 정의가 명확하고 정적 검사가 신뢰할 수 있다.

#### Acceptance Criteria

1. THE Session_Type_Alias SHALL 존재하지 않는 모듈 경로(`..server.session`)에 대한 임포트를 포함하지 않는다.
2. THE Session_Type_Alias SHALL 런타임에서 실제 사용되는 단일 세션 타입(Telnet_Session)을 가리킨다.
3. THE Maintainer SHALL Legacy_Session의 미사용 여부를 grep 기반 전체 소스 검색과 Static_Check(import 미사용 보고)로 확인한다.
4. IF grep 검색과 Static_Check가 Legacy_Session이 런타임 코드에서 사용되지 않음을 보이면, THEN THE Codebase SHALL Legacy_Session 정의와 그 export를 제거한다.
5. WHEN Legacy_Session이 제거되면, THE Codebase SHALL Legacy_Session을 참조하던 테스트 임포트를 유효한 세션 타입 참조로 갱신한다.
6. WHILE 세션 타입 정리가 진행 중인 모든 중간 상태에서, THE Static_Check SHALL 오류 없이 통과한다.

### Requirement 4: 세션 보일러플레이트 및 로깅 정리

**User Story:** Maintainer로서, 나는 세션 코드의 반복 보일러플레이트와 로깅 스팸이 정리되기를 원한다. 그래야 코드 중복이 줄고 로그 신호 대 잡음 비율이 개선된다.

#### Acceptance Criteria

1. THE Session_Layer SHALL 짧은 세션 식별자(short session id) 산출 로직을 단일 정의로 통합한다.
2. THE View_Component SHALL localization 매니저 접근을 인라인 반복 임포트 없이 단일 경로로 수행한다.
3. THE Session_Layer SHALL 메시지 전송 시 INFO 레벨 로깅을 매 호출마다 발생시키지 않는다.
4. THE Maintainer SHALL 모든 보일러플레이트 통합 작업이 성공적으로 완료되고 동작이 보존된 경우에만 정리를 완료로 표시한다.
5. WHILE 보일러플레이트 정리가 진행 중인 모든 중간 상태에서, THE Session_Layer SHALL 정리 이전과 동일한 Observable_Behaviour를 유지한다.

### Requirement 5: 명령어 디렉토리 표준화

**User Story:** Maintainer로서, 나는 명령어 파일 구성이 일관되기를 원한다. 그래야 명령어를 예측 가능한 위치에서 찾고 추가·수정할 수 있어 유지보수 비용이 낮아진다. 명령어 분리(한 명령어 = 한 Command_Module/클래스)는 본 리팩토링의 1차 목적인 유지보수 용이성을 달성하는 핵심 수단이다.

#### Acceptance Criteria

1. THE Command_System SHALL 하나의 Command_Module이 하나의 명령어 클래스를 정의하도록 구성한다.
2. THE Command_System SHALL 각 Command_Module을 해당 Command_Category 하위 디렉토리에 배치한다.
3. THE Command_System SHALL 카테고리 하위 디렉토리 이름에 일관된 명명 규칙(소문자)을 적용한다.
4. WHEN 디렉토리 표준화가 완료되면, THE Command_System SHALL 표준화 이전과 동일한 명령어 집합과 별칭을 등록한다.

### Requirement 6: 중복 및 사문화 모듈 제거

**User Story:** Maintainer로서, 나는 중복되거나 사용되지 않는 명령어 모듈이 제거되기를 원한다. 그래야 혼동과 유지보수 부담이 줄어든다.

#### Acceptance Criteria

1. WHERE 동일한 명령어가 집합 파일과 카테고리 하위 디렉토리에 중복 정의되어 있으면, THE Command_System SHALL 단일 정의만 유지한다.
2. IF 명령어 모듈이 어디에서도 등록되지 않는 것으로 확인되면, THEN THE Command_System SHALL 해당 모듈을 제거한다.
3. WHEN 중복 및 사문화 모듈 제거가 완료되면, THE Command_System SHALL 런타임에서 사용 가능한 명령어 집합을 변경하지 않는다.
4. WHEN 모듈 제거가 완료되면, THE Static_Check SHALL 오류 없이 통과한다.

### Requirement 7: 단일 실행 인터페이스 및 일관된 등록

**User Story:** Maintainer로서, 나는 모든 명령어가 동일한 실행 인터페이스를 따르고 일관되게 등록되기를 원한다. 그래야 실행 경로가 예측 가능하고 등록 누락이 발생하지 않으며, 유지보수 비용이 낮아진다.

#### Acceptance Criteria

1. THE Command_System SHALL 모든 명령어가 Base_Command가 정의하는 단일 실행 인터페이스를 통해 실행되도록 한다.
2. THE Base_Command SHALL 단일 실행 인터페이스가 Output_Port를 통한 즉시 메시지 전송을 지원하고 Command_Result로 제어 흐름을 반환하는 단일 계약을 정의한다.
3. THE Command_Processor SHALL 전투 전용 명령어를 처리 시점에 직접 인스턴스화하지 않고 Command_Registry에서 조회한다.
4. THE Command_Registry SHALL 명령어를 자동 발견(automatic discovery) 방식으로 등록한다.
5. WHEN 자동 발견 등록이 완료되면, THE Command_Registry SHALL 기존 수동 등록의 모든 커스터마이징(커스텀 별칭, 명령어 이름 변경 포함)을 동일하게 재현한다.
6. WHEN 등록 방식이 변경되면, THE Command_System SHALL 변경 이전과 동일한 메시지 내용과 상대 순서를 유지한다.

### Requirement 8: 전투 및 대화 숫자 입력 매핑 데이터화

**User Story:** Maintainer로서, 나는 전투/대화 중 숫자 입력 매핑이 매직넘버가 아닌 데이터로 표현되기를 원한다. 그래야 매핑을 한 곳에서 확인하고 변경할 수 있다.

#### Acceptance Criteria

1. THE Command_Processor SHALL 전투 중 숫자 입력을 명령어로 변환할 때 Numeric_Input_Map을 사용한다.
2. THE Command_Processor SHALL 대화 중 숫자 입력을 명령어로 변환할 때 Numeric_Input_Map을 사용한다.
3. THE Command_Processor SHALL 숫자 입력 변환 규칙을 처리 로직에 하드코딩된 리터럴로 분산시키지 않는다.
4. WHEN 숫자 입력 매핑이 데이터화되면, THE Command_Processor SHALL 데이터화 이전과 동일한 변환 결과를 산출한다.

### Requirement 9: Processor 정책 정리

**User Story:** Maintainer로서, 나는 Command_Processor가 라우팅 외 정책을 중복 보유하지 않기를 원한다. 그래야 책임 경계가 명확해진다.

#### Acceptance Criteria

1. THE Command_Processor SHALL 관리자 권한 검사를 명령어 계층과 중복하여 수행하지 않는다.
2. WHEN 관리자 전용 명령어가 비관리자에 의해 실행되면, THE Command_System SHALL 정리 이전과 동일한 권한 거부 응답을 산출한다.
3. WHEN Processor 정책 정리가 완료되면, THE Command_System SHALL 인증, 명령어 반복, 모드 변환, 전투 게이팅, 이벤트 발행, 마지막 명령어 저장에 대해 정리 이전과 동일한 Observable_Behaviour를 유지한다.

### Requirement 10: 검증 가능성

**User Story:** Maintainer로서, 나는 모든 리팩토링 단계가 자동으로 검증되기를 원한다. 그래야 회귀 없이 변경을 확신할 수 있다.

#### Acceptance Criteria

1. THE Maintainer SHALL 어떤 리팩토링 변경을 적용하기 전에 Static_Check가 오류 없이 통과하는 상태를 유지한다.
2. WHILE 리팩토링이 진행 중인 모든 중간 상태에서, THE Static_Check SHALL 오류 없이 통과한다.
3. THE Regression_Suite SHALL look, 방 정보, 전투, 대화, 관리자 권한, 미인증 접근, 알 수 없는 명령어 시나리오를 포함한다.
4. WHEN Regression_Suite가 실행되면, THE Codebase SHALL 리팩토링 이전 기준선과 동일한 메시지 내용과 상대 순서를 산출한다.

### Requirement 11: 플레이어 메시지 즉시 전달 (Incremental_Delivery)

**User Story:** 플레이어로서, 나는 명령어 실행 중 발생하는 출력을 발생하는 순간 바로 받기를 원한다. 그래야 여러 단계로 진행되는 명령(전투, 대화, 다중 줄 출력)에서 진행 상황을 실시간으로 확인할 수 있다.

#### Acceptance Criteria

1. WHEN 명령어 실행 중 플레이어에게 보낼 출력이 발생하면, THE Command_System SHALL 해당 출력을 발생 시점에 즉시 Output_Port를 통해 세션으로 전송한다.
2. WHEN 하나의 명령어 실행이 여러 개의 플레이어 메시지를 생성하면, THE Command_System SHALL 각 메시지를 생성 순서대로 각각 발생 시점에 즉시 전송한다.
3. THE Command_System SHALL 플레이어 출력 텍스트를 명령 종료 시점까지 누적하여 단일 반환값으로 일괄 전송하지 않는다.
4. THE Command_Result SHALL 플레이어 출력 텍스트 누적 책임을 보유하지 않고 제어 흐름(성공/실패, 브로드캐스트 지시, 연결 종료 등)만 표현한다.
5. WHEN 명령어가 Output_Port로 전송하는 각 메시지가 전송되면, THE Output_Port SHALL 해당 메시지의 ANSI 색상과 텍스트 내용을 변경 이전과 동일하게 유지한다.
6. IF 명령어 실행이 처리 도중 오류로 중단되면, THEN THE Command_System SHALL 중단 시점까지 이미 즉시 전송된 메시지를 회수하거나 취소하지 않는다.
