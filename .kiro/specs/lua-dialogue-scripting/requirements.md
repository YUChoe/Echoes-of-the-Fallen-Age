# 요구사항 문서: Lua 스크립트 기반 NPC 대화 시스템

## 소개

Python MUD Engine(카르나스 연대기)의 NPC 대화 시스템을 Lua 스크립트 기반으로 확장한다. lupa 라이브러리를 사용하여 Python에서 Lua 스크립트를 실행하고, NPC별 대화 로직을 외부 Lua 파일로 관리한다. Lua 스크립트는 세션 및 플레이어 변수에 접근하여 동적 대화 분기를 구현할 수 있다.

## 용어집

- **Lua_Runtime**: lupa 라이브러리를 통해 Python 내에서 Lua 스크립트를 실행하는 런타임 환경
- **Dialogue_Script_Loader**: NPC ID 기반으로 `configs/dialogues/{npc_id}.lua` 파일을 로드하고 Lua 런타임에서 실행하는 모듈
- **Dialogue_Context**: Lua 스크립트에 전달되는 세션 및 플레이어 정보를 담은 읽기 전용 컨텍스트 객체
- **DialogueInstance**: 진행 중인 대화 인스턴스를 관리하는 dataclass (기존 구현)
- **DialogueManager**: 대화 인스턴스의 생성, 조회, 종료 및 메시지 전송을 담당하는 매니저 (기존 구현)
- **TalkCommand**: talk 명령어를 처리하는 커맨드 클래스 (기존 구현)
- **choice_entity**: 대화 선택지를 저장하는 OrderedDict (키: 번호, 값: 선택지 텍스트)
- **Player**: 플레이어 모델 (username, display_name, preferred_locale, stats, completed_quests, quest_progress 등)
- **Session**: Telnet 세션 (session_id, locale, current_room_id, in_dialogue, stamina 등)
- **Monster**: NPC/몬스터 모델 (id, name, properties 등)

## 요구사항

### 요구사항 1: lupa 라이브러리 통합

**사용자 스토리:** 개발자로서, 나는 Python 환경에서 Lua 스크립트를 실행할 수 있기를 원한다. 그래야 NPC 대화 로직을 외부 스크립트로 관리할 수 있다.

#### 승인 기준

1. THE Lua_Runtime은 lupa 라이브러리를 사용하여 LuaRuntime 인스턴스를 초기화해야 한다
2. THE Lua_Runtime은 Lua 스크립트 문자열을 실행하고 반환값을 Python 객체로 변환해야 한다
3. IF lupa 라이브러리가 설치되지 않은 경우, THEN THE Dialogue_Script_Loader는 에러를 로깅하고 기본 대화(silent_stare)로 폴백해야 한다

### 요구사항 2: NPC 대화 스크립트 로딩

**사용자 스토리:** 게임 디자이너로서, 나는 NPC별 대화 스크립트를 `configs/dialogues/{npc_id}.lua` 파일로 관리할 수 있기를 원한다. 그래야 서버 재시작 없이 대화 내용을 수정할 수 있다.

#### 승인 기준

1. WHEN 플레이어가 NPC에게 talk 명령을 실행하면, THE Dialogue_Script_Loader는 `configs/dialogues/{npc_id}.lua` 경로에서 Lua 스크립트 파일을 로드해야 한다
2. WHEN Lua 스크립트 파일이 존재하면, THE DialogueInstance의 get_new_dialogue 메서드는 Lua 스크립트를 실행하여 초기 대화 텍스트와 choice_entity를 생성해야 한다
3. WHEN Lua 스크립트 파일이 존재하지 않으면, THE DialogueInstance는 기존 동작(silent_stare 메시지와 [1] Bye 선택지)을 유지해야 한다
4. IF Lua 스크립트 실행 중 오류가 발생하면, THEN THE Dialogue_Script_Loader는 오류를 로깅하고 기본 대화(silent_stare)로 폴백해야 한다

### 요구사항 3: Lua 스크립트 컨텍스트 변수

**사용자 스토리:** 게임 디자이너로서, 나는 Lua 스크립트에서 세션과 플레이어 정보를 변수로 사용할 수 있기를 원한다. 그래야 플레이어 상태에 따라 동적으로 대화를 분기할 수 있다.

#### 승인 기준

1. THE Dialogue_Context는 다음 플레이어 정보를 Lua 스크립트에 읽기 전용 변수로 제공해야 한다: username, display_name, preferred_locale, completed_quests, quest_progress
2. THE Dialogue_Context는 다음 세션 정보를 Lua 스크립트에 읽기 전용 변수로 제공해야 한다: session_id, locale, current_room_id, stamina
3. THE Dialogue_Context는 다음 NPC 정보를 Lua 스크립트에 읽기 전용 변수로 제공해야 한다: npc_id, npc_name(로케일 기반), npc_properties
4. THE Lua_Runtime은 Python 내부 객체에 대한 직접 접근을 차단하고, Dialogue_Context를 통해서만 데이터를 제공해야 한다

### 요구사항 4: Lua 스크립트 대화 선택지 처리

**사용자 스토리:** 플레이어로서, 나는 NPC와 대화할 때 Lua 스크립트에서 정의한 선택지를 선택하고 후속 대화를 진행할 수 있기를 원한다. 그래야 풍부한 대화 경험을 할 수 있다.

#### 승인 기준

1. THE Lua 스크립트는 `get_dialogue()` 함수를 통해 초기 대화 텍스트와 선택지 테이블을 반환해야 한다
2. THE Lua 스크립트는 `on_choice(choice_number)` 함수를 통해 플레이어의 선택에 대한 후속 대화 텍스트와 새로운 선택지 테이블을 반환해야 한다
3. WHEN Lua 스크립트의 on_choice 함수가 선택지 없이 텍스트만 반환하면, THE DialogueInstance는 자동으로 [1] Bye 선택지를 추가해야 한다
4. WHEN 플레이어가 Bye 선택지를 선택하면, THE DialogueManager는 대화를 종료하고 세션을 원래 상태로 복원해야 한다

### 요구사항 5: 샘플 Veteran Guard 대화 스크립트

**사용자 스토리:** 개발자로서, 나는 Veteran Guard(id: 3914fbe8-c8a9-493a-b451-1084ee4d6d2a)의 샘플 Lua 대화 스크립트를 통해 시스템이 정상 동작하는지 검증할 수 있기를 원한다.

#### 승인 기준

1. THE 샘플 스크립트는 `configs/dialogues/3914fbe8-c8a9-493a-b451-1084ee4d6d2a.lua` 경로에 위치해야 한다
2. WHEN 플레이어가 Veteran Guard에게 talk 명령을 실행하면, THE 스크립트는 초기 인사말과 함께 "Who are you?" 선택지를 표시해야 한다
3. WHEN 플레이어가 "Who are you?" 선택지를 선택하면, THE 스크립트는 Veteran Guard의 자기소개 텍스트를 표시하고 [1] Bye 선택지를 제공해야 한다
4. THE 샘플 스크립트는 Dialogue_Context의 player 변수(예: display_name)를 사용하여 플레이어 이름을 대화에 포함해야 한다
5. THE Lua 스크립트의 모든 대화 텍스트와 선택지 텍스트는 다국어 dict 형식(`{en = "...", ko = "..."}`)으로 내장해야 한다. DialogueManager는 세션의 locale에 맞는 텍스트를 선택하여 표시한다
