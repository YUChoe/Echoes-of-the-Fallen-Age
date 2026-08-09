# Requirements Document

## Introduction

이 스펙은 Python MUD 엔진(Echoes of the Fallen Age)의 클라이언트 인터페이스를 사람이 읽는 Telnet 텍스트에서 구조화된 JSON 라인 프로토콜로 전환하기 위한 요구사항을 정의한다.

페이즈2에서 플레이어 접속 경로가 Godot GUI 클라이언트로 바뀐다. 클라이언트가 번역과 프레젠테이션을 담당하고, 서버는 구조화 데이터만 내보낸다. UI는 완전 버튼 기반이므로 서버는 명령어 문자열을 파싱하지 않는다.

이 전환은 다음 네 가지를 동시에 달성한다.

- 프레젠테이션 책임 이전: 서버가 ANSI 색상과 완성된 문장을 만들지 않는다. 현재 `_format_room_info()`가 번역과 텍스트 조립을 수행하고 `get_message()` 호출이 483곳에 분산되어 있다.
- 대상 지정 방식 전환: 매 요청 재계산되는 순서 번호(idx)를 폐기하고 uuid를 유일한 대상 키로 사용한다. 엔티티는 이미 전부 uuid4를 보유하고 있으므로 데이터는 준비되어 있다.
- 입력 모델 전환: 문자열 명령 파싱을 구조화 액션 디스패치로 대체한다. 별칭 체계와 오타 교정이 불필요해진다.
- 어드민 이전: 별도 프로세스(Node webadmin)가 SQLite를 직접 조작하던 구조를 서버 내부 어드민 채널로 옮긴다.

이번 전환은 동작 보존 리팩토링이 아니다. 외부에서 관찰 가능한 출력 형식이 의도적으로 완전히 바뀐다. 보존해야 하는 것은 게임 규칙, 밸런스, 데이터 스키마, 번역 키다.

프로토콜 계약은 `docs/protocol/`에 정의되며 본 스펙은 그 계약의 서버측 구현을 규율한다.

#[[file:docs/protocol/README.md]]

## Glossary

- **Codebase**: 본 전환 대상 소스 트리(`src/mud_engine/`).
- **Maintainer**: 본 전환을 수행하고 검증하는 개발자.
- **JSON_Line**: 개행(`\n`)으로 종결되는 단일 JSON 오브젝트. 4000 포트 페이로드의 단위.
- **Game_Channel**: 플레이어 세션이 사용하는 TCP 4000 경로.
- **Admin_Channel**: 관리 기능이 사용하는 TCP 4001 경로. 게임 채널과 인증이 분리된다.
- **Presenter_Layer**: 메시지 딕셔너리를 Telnet 텍스트로 변환하는 현재 코드(`_format_message`, `_format_room_info`, `ansi_colors.py`).
- **Entity_Number_Map**: 방/인벤토리 엔티티에 순서 번호를 부여하는 현재 체계(`session.room_entity_map`, `session.inventory_entity_map`). 폐기 대상.
- **Entity_UUID**: 엔티티 인스턴스의 uuid4 문자열. 전환 후 유일한 대상 지정 키.
- **Action_Message**: 클라이언트가 보내는 `{type:"action", verb, target?, params?}` 메시지.
- **Action_Dispatcher**: verb를 핸들러로 라우팅하는 구성 요소. 현재 `CommandProcessor`의 문자열 파싱 라우팅을 대체한다.
- **Verb**: 액션 종류를 지정하는 문자열. `docs/protocol/client-to-server.md`에 목록이 정의된다.
- **Message_Key_Payload**: 완성 문자열 대신 전달하는 `{key, params}` 구조.
- **Rejection_Code**: 액션 거절 사유를 나타내는 코드. `docs/protocol/entities.md`에 목록이 정의된다.
- **Disposition**: 요청 플레이어를 기준으로 계산된 대상의 종족 관계(`friendly`, `neutral`, `hostile`).
- **Harness**: `scripts/`에 위치하며 JSON 라인을 주고받아 서버 동작을 검증하는 테스트 스크립트.
- **Static_Check**: mypy 타입 검사와 ruff 린트 검사.

## Requirements

### Requirement 1: JSON 라인 프로토콜

**User Story:** 개발자로서, 나는 서버가 구조화된 JSON 라인만 내보내기를 원한다. 그래야 GUI 클라이언트가 텍스트를 파싱하지 않고 데이터를 직접 사용할 수 있다.

#### Acceptance Criteria

1. THE Codebase SHALL Game_Channel의 모든 송신 페이로드를 UTF-8 인코딩의 JSON_Line으로 출력한다.
2. THE Codebase SHALL 하나의 JSON_Line 내부에 개행 문자를 포함하지 않는다.
3. THE Codebase SHALL Game_Channel 송신 페이로드에 ANSI 이스케이프 시퀀스를 포함하지 않는다.
4. WHEN 클라이언트가 JSON으로 파싱할 수 없는 라인을 보내면, THE Codebase SHALL `error` 메시지에 `MALFORMED_MESSAGE` 코드로 응답하고 연결을 유지한다.
5. WHEN 클라이언트가 계약에 정의되지 않은 `type`을 보내면, THE Codebase SHALL 해당 메시지를 무시하고 경고를 로그에 기록하며 연결을 유지한다.
6. THE Codebase SHALL 연결 초기의 Telnet IAC 협상을 현행대로 유지한다.
7. THE Codebase SHALL 수신 측에서 개행이 나타날 때까지 바이트를 누적하고 완성된 라인 단위로 UTF-8 디코딩을 수행한다.

### Requirement 2: 프레젠테이션 계층 제거

**User Story:** 개발자로서, 나는 서버에서 텍스트 조립 코드가 사라지기를 원한다. 그래야 표현 변경이 클라이언트만의 문제가 되고 서버가 게임 규칙에 집중할 수 있다.

#### Acceptance Criteria

1. THE Codebase SHALL `server/telnet_session.py`의 `_format_message()`와 `_format_room_info()`를 제거한다.
2. THE Codebase SHALL `server/ansi_colors.py`를 제거하고 이를 참조하는 모든 임포트를 정리한다.
3. THE Codebase SHALL 방 정보를 `docs/protocol/server-to-client.md`의 `room_info` 스키마로 송신한다.
4. THE Codebase SHALL 5x5 텍스트 미니맵 조립(`_generate_minimap`)을 제거하고 `nearby_rooms` 좌표 배열 송신으로 대체한다.
5. THE Codebase SHALL 엔티티 이름과 설명을 `{"en":..., "ko":...}` 형태로 송신하며 서버에서 언어를 선택하지 않는다.
6. THE Codebase SHALL 몬스터의 종족 관계를 요청 플레이어 기준 Disposition으로 계산해 송신한다.
7. THE Codebase SHALL Disposition 판정을 세션 계층에서 분리해 전용 모듈로 이동하고 `telnet_session.py`의 `_is_friendly_faction`/`_is_neutral_faction`을 제거한다.
8. THE Codebase SHALL Disposition 판정 규칙을 현재 동작 그대로 보존한다. 같은 종족은 우호, `ash_knights` 기준 `animals`는 중립, 그 밖은 적대다. `faction_relations` 테이블을 조회하는 동적 판정은 이번 범위에 포함하지 않으며 우호도 기능 개발 시점에 도입한다.

### Requirement 3: uuid 기반 대상 지정

**User Story:** 개발자로서, 나는 대상 지정이 uuid로 통일되기를 원한다. 그래야 순서 번호가 재계산되며 같은 번호가 다른 엔티티를 가리키는 불안정성이 사라지고, 방 안의 엔티티 수 제한도 없어진다.

#### Acceptance Criteria

1. THE Codebase SHALL Entity_Number_Map 생성 로직을 `core/managers/player_movement_manager.py::send_room_info_to_player()`에서 제거한다.
2. THE Codebase SHALL `server/session/state.py`의 `room_entity_map`과 `inventory_entity_map` 필드 및 `telnet_session.py`의 대응 property를 제거한다.
3. THE Codebase SHALL `game/combat.py`의 `_entity_map` 필드와 `get_entity_map`/`set_entity_map`을 제거하고 `core/managers/global_tick_manager.py`의 맵 복사를 제거한다.
4. THE Codebase SHALL Action_Message의 `target`을 Entity_UUID 전체 문자열로만 해석하며 접두어 매칭이나 축약을 지원하지 않는다.
5. THE Codebase SHALL 숫자 입력을 엔티티로 해석하는 모든 경로를 제거한다. 대상 경로는 `commands/combat/attack_command.py`, `commands/dialogue/talk_command.py`, `commands/Basic/look.py`, `commands/get_command.py`, `commands/use_command.py`, `commands/container_commands.py`, `commands/read_command.py`, `commands/admin/terminate_command.py`이다.
6. THE Codebase SHALL `game/managers/world_manager.py`의 `take_item_from_container()`와 `put_item_in_container()` 시그니처를 번호와 entity_map 인자 대신 Entity_UUID를 받도록 변경한다.
7. THE Codebase SHALL 컨테이너 내부 아이템 지정에서 배열 인덱스 기반 참조(`commands/use_command.py`의 `int(x)-1` 경로)를 제거하고 Entity_UUID로 대체한다.
8. THE Codebase SHALL 이름 문자열로 대상을 찾는 로직(`commands/give_command.py` 등의 `get_localized_name(locale).lower()` 비교)을 제거한다.
9. THE Codebase SHALL 방 안의 엔티티 수에 관계없이 모든 엔티티를 지정 가능하게 한다. 현재의 9개 제한은 사라진다.
10. THE Codebase SHALL 대화 선택지 번호를 유지하며 이를 `dialogue_choice` 액션의 params로 수신한다.

### Requirement 4: 액션 디스패처

**User Story:** 개발자로서, 나는 문자열 파싱이 액션 디스패치로 대체되기를 원한다. 그래야 타이핑이 없는 UI에서 불필요한 조립과 파싱 왕복이 사라진다.

#### Acceptance Criteria

1. THE Codebase SHALL Action_Message의 `verb`를 핸들러로 직접 라우팅하는 Action_Dispatcher를 제공한다.
2. THE Codebase SHALL `docs/protocol/client-to-server.md`에 정의된 verb 전체를 처리한다.
3. THE Codebase SHALL 명령어 별칭 체계를 제거한다. 방향 별칭(`n`, `s`, `e`, `w`)은 `move` verb의 `direction` params로 통합된다.
4. THE Codebase SHALL 알 수 없는 명령어에 대한 오타 교정 응답(`command.unknown`, `command.help_suggestion`)을 제거한다.
5. THE Codebase SHALL `commands/processor.py`의 `_convert_combat_number_to_command()`와 `_convert_dialogue_number_to_command()`를 제거한다.
6. THE Codebase SHALL 전투 액션을 숫자 치환이 아닌 `attack`, `flee`, `use_item`, `end_turn` verb로 수신한다.
7. THE Codebase SHALL `help` 및 `language` 명령어를 제거한다.
8. THE Codebase SHALL 관리자 권한 판정을 단일 경로에서만 수행하며 processor의 중복 재검사를 제거한다.
9. THE Codebase SHALL 채팅을 `action`이 아닌 별도 `chat` 메시지로 수신하고 `say`/`whisper` 명령어를 제거한다.
10. THE Codebase SHALL `whisper` 대상을 사용자명 문자열이 아닌 플레이어 Entity_UUID로 해석한다.

### Requirement 5: 번역 책임 이전

**User Story:** 운영자로서, 나는 번역이 클라이언트에서 이뤄지기를 원한다. 그래야 언어 추가가 서버 배포 없이 가능하고 서버가 수신자별 언어를 추적할 필요가 없어진다.

#### Acceptance Criteria

1. THE Codebase SHALL 사용자에게 표시되는 모든 메시지를 Message_Key_Payload로 송신하고 완성된 문장을 송신하지 않는다.
2. THE Codebase SHALL `CommandResult`에서 `message: str` 필드를 제거하고 `message_key`와 `params`를 도입한다.
3. THE Codebase SHALL `params` 값이 엔티티 이름인 경우 언어별 dict로 전달한다.
4. THE Codebase SHALL `data/translations/` 아래 9개 번역 파일과 `core/localization.py`를 서버에서 제거한다.
5. THE Codebase SHALL 번역 키 문자열을 변경하지 않는다. 클라이언트가 기존 키를 그대로 사용한다.
6. THE Codebase SHALL `session.locale`, `state.locale`, `commands/utils.py::get_user_locale()`을 제거한다.
7. THE Codebase SHALL `players.preferred_locale` 컬럼을 유지하되 번역 목적으로 사용하지 않는다. 이 값은 계정 생성 시 기록되고 통계 목적으로만 조회된다.
8. THE Codebase SHALL 브로드캐스트 메시지에서 발신자 locale로 문장을 만들어 수신자에게 전달하는 현재의 locale 오염을 제거한다.
9. THE Codebase SHALL 사용자 노출 경로의 하드코딩된 한국어 문자열을 번역 키로 대체한다. 대상은 `commands/Basic/status.py`, `commands/examine_command.py`, `commands/give_command.py`, `commands/container_commands.py`, `commands/utils.py`를 포함한다.
10. THE Codebase SHALL 서버 로그 메시지는 현행 언어를 유지한다. 로그는 사용자 노출 경로가 아니다.

### Requirement 6: 액션 검증과 거절

**User Story:** 플레이어로서, 나는 적용할 수 없는 동작을 시도했을 때 이유를 알기를 원한다. 그래야 클라이언트가 적절한 안내를 표시하고 버튼 구성을 교정할 수 있다.

#### Acceptance Criteria

1. THE Codebase SHALL 수신한 verb가 대상에 적용 가능한지 검증한다.
2. WHEN 검증에 실패하면, THE Codebase SHALL `action_rejected` 메시지에 요청의 `seq`, `verb`, `target`, Rejection_Code, Message_Key_Payload를 담아 응답한다.
3. THE Codebase SHALL `docs/protocol/entities.md`에 정의된 Rejection_Code만 사용한다.
4. WHEN 인증되지 않은 세션이 `login`과 `ping` 외의 메시지를 보내면, THE Codebase SHALL `NOT_AUTHENTICATED`로 거절한다.
5. WHEN `target`이 현재 컨텍스트에 존재하지 않으면, THE Codebase SHALL `NOT_FOUND`로 거절한다.
6. WHEN verb가 대상의 성질에 적용될 수 없으면, THE Codebase SHALL `NOT_APPLICABLE`로 거절한다.
7. THE Codebase SHALL 클라이언트가 부적절한 verb를 보내는 것을 오류로 취급하지 않는다. 클라이언트는 엔티티 속성으로 버튼을 추론하므로 이는 정상 동작 범위다.
8. THE Codebase SHALL 엔티티 페이로드에 클라이언트가 버튼을 구성하기에 충분한 속성을 포함한다. 몬스터는 Disposition, `can_talk`, `is_alive`, `hp`, `max_hp`, `armor_class`, `attack_power`를, 오브젝트는 `category`, `equipment_slot`, `is_container`, `is_readable`, `is_usable`, `max_stack`, `is_equipped`를 포함한다.
10. THE Codebase SHALL 레벨 개념을 페이로드에 포함하지 않는다. 서버 코드에서 제거된 개념이며 모델과 DB에 해당 필드가 없다.
11. THE Codebase SHALL 상인 여부를 페이로드에 포함하지 않는다. 모든 캐릭터와 거래할 수 있으므로 구분이 불필요하다.
12. THE Codebase SHALL 오브젝트의 `category`를 `properties.category`에서 읽는다. `game_objects.category` 컬럼은 모델이 사용하지 않는다.
9. THE Codebase SHALL 가용 verb 목록을 엔티티 페이로드에 포함하지 않는다. 버튼 구성은 클라이언트의 판단이다.

### Requirement 7: 어드민 채널

**User Story:** 운영자로서, 나는 관리 기능이 게임 서버 안에서 제공되기를 원한다. 그래야 별도 프로세스가 같은 SQLite를 직접 조작해 서버 캐시와 어긋나는 문제가 사라진다.

#### Acceptance Criteria

1. THE Codebase SHALL Game_Channel과 별개인 Admin_Channel을 TCP 4001에 제공한다.
2. THE Codebase SHALL Admin_Channel에서 Telnet IAC 협상을 수행하지 않는다.
3. THE Codebase SHALL Admin_Channel 인증을 Game_Channel 인증과 분리한다. 게임 세션의 인증 상태가 Admin_Channel로 전이되지 않는다.
4. THE Codebase SHALL 관리자 인증에 `players` 테이블의 `is_admin` 계정과 `bcrypt` 해시 비교를 사용한다.
5. THE Codebase SHALL `is_admin`이 거짓인 계정의 Admin_Channel 인증을 `PERMISSION_DENIED`로 거절한다.
6. THE Codebase SHALL 계정 생성만 허용되는 서비스 인증 경로를 제공한다.
7. THE Codebase SHALL `docs/protocol/admin.md`에 정의된 8개 리소스의 목록, 상세, 생성, 수정, 삭제를 제공한다.
8. THE Codebase SHALL 삭제 요청 시 참조 무결성을 검사하고 참조된 행을 `REFERENCED`로 거절한다.
9. WHEN 어드민 변경이 실행 중인 게임 상태에 영향을 주면, THE Codebase SHALL 메모리 캐시를 갱신하고 영향받는 플레이어에게 갱신된 상태를 송신한다.
10. THE Codebase SHALL `AdminManager`의 기존 기능(`create_room_realtime`, `update_room_realtime`, `create_object_realtime`, `validate_and_repair_world`, `kick_player`, `get_admin_stats`)을 Admin_Channel로 노출한다.
11. THE Codebase SHALL `utils/map_exporter.py`의 HTML 생성을 제거하고 좌표·지형·막힌 출구·종족별 분포를 담은 JSON 응답으로 대체한다.
12. THE Codebase SHALL 관리자 명령어 15개를 Game_Channel에서 제거하고 Admin_Channel의 `admin_action`으로 이전한다.
13. THE Codebase SHALL 모든 어드민 변경 작업에 대해 실행 주체, 대상, 변경 내용, 시각을 로그에 기록한다.

### Requirement 8: 계정 생성 경로

**User Story:** 신규 플레이어로서, 나는 웹사이트에서 계정을 만들기를 원한다. 그래야 게임 클라이언트를 내려받기 전에 가입할 수 있다.

#### Acceptance Criteria

1. THE Codebase SHALL Admin_Channel에 서비스 인증으로 호출 가능한 계정 생성 경로를 제공한다.
2. THE Codebase SHALL 계정 생성 시 사용자명 중복, 사용자명 길이와 허용 문자, 비밀번호 최소 길이, 이메일 형식을 검증한다.
3. THE Codebase SHALL 사용자명이 중복이면 `USERNAME_TAKEN`으로 거절한다.
4. THE Codebase SHALL 비밀번호를 `bcrypt`로 해시해 저장한다.
5. THE Codebase SHALL 신규 계정의 `is_admin`을 항상 거짓으로 설정한다.
6. THE Codebase SHALL Game_Channel에서 회원가입 흐름을 제거한다.
7. THE Codebase SHALL 로그인 실패 응답에서 사용자명 존재 여부를 구분해 노출하지 않는다.

### Requirement 9: 검증 하니스

**User Story:** 개발자로서, 나는 Godot 클라이언트 없이도 서버를 검증하기를 원한다. 그래야 클라이언트 개발과 병렬로 서버를 진행할 수 있다.

#### Acceptance Criteria

1. THE Codebase SHALL `scripts/`에 JSON_Line을 주고받는 Harness를 제공한다.
2. THE Harness SHALL 접속, `welcome` 수신, 로그인, `room_info` 수신을 검증한다.
3. THE Harness SHALL 액션 전송과 응답 수신을 검증한다.
4. THE Harness SHALL 거절 응답의 `seq` 대응과 Rejection_Code를 검증한다.
5. THE Harness SHALL 라인 프레이밍을 검증한다. 분할 수신과 병합 수신 모두에서 메시지를 정확히 복원해야 한다.
6. THE Harness SHALL 한국어를 포함한 페이로드가 손상 없이 왕복하는지 검증한다.
7. THE Harness SHALL 명시적 종료 코드를 반환하고 무한 대기하지 않는다.
8. THE Codebase SHALL `telnetlib`에 의존하는 `telnet/telnet_client.py`와 `telnet_test.sh` 경로를 폐기한다. 해당 모듈은 Python 3.13에서 표준 라이브러리에서 제거되어 현재 동작하지 않는다.

### Requirement 10: 단계적 이행과 정적 검사

**User Story:** Maintainer로서, 나는 각 단계가 독립적으로 검증되기를 원한다. 그래야 대규모 전환에서 문제 발생 지점을 특정할 수 있다.

#### Acceptance Criteria

1. THE Codebase SHALL 각 단계 완료 시점에 `mypy src/`를 통과한다.
2. THE Codebase SHALL 각 단계 완료 시점에 `ruff check src/`를 통과한다.
3. THE Codebase SHALL 각 단계 완료 시점에 Harness 검증을 통과한다.
4. THE Codebase SHALL 게임 규칙, 밸런스, 데이터베이스 스키마를 변경하지 않는다. 단 Requirement 7과 8이 요구하는 어드민 및 계정 관련 변경은 예외다.
5. THE Codebase SHALL 번역 키 문자열을 변경하지 않는다.
6. THE Codebase SHALL 소스 파일 하나의 길이를 가능한 한 500행 이내로 유지한다.
7. THE Codebase SHALL `session/protocol.py`의 Telnet IAC 협상 코드를 유지한다. 사람이 터미널로 접속하지 않으므로 실질적으로 사용되지 않으나, 게이트웨이 구현과의 호환을 위해 이번 범위에서 제거하지 않으며 향후 제거 후보로 기록한다.
