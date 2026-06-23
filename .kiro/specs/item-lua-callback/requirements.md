# 요구사항 문서: 아이템 Lua 콜백 시스템

## 소개

아이템에 대해 use, read 등의 동사(verb) 명령어가 실행될 때, 해당 아이템의 `template_id`에 대응하는 Lua 스크립트 파일(`configs/items/{template_id}.lua`)이 존재하면 이를 로딩하여 콜백 함수(`on_use`, `on_read` 등)를 실행하는 시스템이다. Lua 스크립트가 없거나 해당 콜백 함수가 정의되지 않은 경우 기존 동작을 그대로 유지한다(폴백). 기존 NPC 대화 시스템의 `LuaScriptLoader`를 재사용하여 샌드박스 환경과 핫 리로드를 활용한다.

## 용어집

- **Item_Command**: 아이템에 대해 동사를 실행하는 명령어 클래스 (UseCommand, ReadCommand 등)
- **Item_Lua_Callback_Handler**: 아이템 Lua 콜백 스크립트를 로드하고 실행하는 핸들러 모듈
- **LuaScriptLoader**: 기존 NPC 대화 시스템에서 사용하는 Lua 스크립트 로더 (`src/mud_engine/game/lua_script_loader.py`). lupa 라이브러리 기반 샌드박스 환경 제공
- **template_id**: 아이템 템플릿의 고유 식별자. `configs/items/{template_id}.json`에 정의되며, 게임 오브젝트의 `properties.template_id` 필드에 저장됨
- **Lua_Callback_Script**: `configs/items/{template_id}.lua` 경로에 위치하는 Lua 스크립트 파일. `on_use(ctx)`, `on_read(ctx)` 등의 콜백 함수를 정의
- **Callback_Context**: Lua 콜백 함수에 전달되는 컨텍스트 테이블. 플레이어 정보, 아이템 정보, 세션 정보 등을 포함
- **Callback_Result**: Lua 콜백 함수의 반환값. 메시지 텍스트, 아이템 소모 여부, 추가 효과 등을 포함하는 테이블
- **Fallback**: Lua 스크립트 또는 콜백 함수가 없을 때 기존 하드코딩된 동작으로 처리하는 방식

## 요구사항

### 요구사항 1: Lua 콜백 스크립트 로딩

**사용자 스토리:** 개발자로서, 아이템 동사 실행 시 해당 아이템의 template_id에 대응하는 Lua 스크립트를 자동으로 로딩하고 싶다. 이를 통해 아이템별 커스텀 동작을 코드 변경 없이 Lua 스크립트로 정의할 수 있다.

#### 수용 기준

1. WHEN 아이템 동사 명령어가 실행될 때, THE Item_Lua_Callback_Handler SHALL 해당 아이템의 `properties.template_id` 값을 사용하여 `configs/items/{template_id}.lua` 파일의 존재 여부를 확인한다
2. WHEN Lua_Callback_Script 파일이 존재할 때, THE Item_Lua_Callback_Handler SHALL LuaScriptLoader를 사용하여 해당 스크립트를 로드하고 실행한다
3. WHEN Lua_Callback_Script 파일이 존재하지 않을 때, THE Item_Lua_Callback_Handler SHALL None을 반환하여 기존 Fallback 동작이 수행되도록 한다
4. WHEN 아이템에 `template_id`가 없을 때, THE Item_Lua_Callback_Handler SHALL 스크립트 로딩을 시도하지 않고 None을 반환한다
5. THE Item_Lua_Callback_Handler SHALL LuaScriptLoader의 기존 샌드박스 환경(attribute_filter)을 그대로 사용하여 Lua 스크립트를 실행한다
6. THE Item_Lua_Callback_Handler SHALL 매 호출 시 디스크에서 스크립트를 읽어 핫 리로드를 지원한다

### 요구사항 2: on_use 콜백 실행

**사용자 스토리:** 게임 디자이너로서, 아이템 사용(use) 시 Lua 스크립트의 `on_use(ctx)` 콜백을 통해 커스텀 효과를 정의하고 싶다. 이를 통해 단순 HP/스태미나 회복 외의 다양한 사용 효과를 구현할 수 있다.

#### 수용 기준

1. WHEN UseCommand가 실행되고 Lua_Callback_Script에 `on_use` 함수가 정의되어 있을 때, THE UseCommand SHALL `on_use(ctx)` 함수를 호출하고 Callback_Result를 처리한다
2. WHEN `on_use(ctx)` 함수가 Callback_Result를 반환할 때, THE UseCommand SHALL 반환된 메시지를 플레이어에게 표시한다
3. WHEN Callback_Result의 `consume` 필드가 true일 때, THE UseCommand SHALL 기존 소모 로직(아이템 삭제 또는 변환)을 수행한다
4. WHEN Callback_Result의 `consume` 필드가 false이거나 없을 때, THE UseCommand SHALL 아이템을 소모하지 않는다
5. WHEN Lua_Callback_Script에 `on_use` 함수가 정의되지 않았을 때, THE UseCommand SHALL 기존 하드코딩된 소모품 사용 로직(HP/스태미나 회복)을 Fallback으로 실행한다
6. WHEN `on_use(ctx)` 실행 중 오류가 발생할 때, THE UseCommand SHALL 오류를 로깅하고 기존 Fallback 동작을 수행한다

### 요구사항 3: on_read 콜백 실행

**사용자 스토리:** 게임 디자이너로서, 아이템 읽기(read) 시 Lua 스크립트의 `on_read(ctx)` 콜백을 통해 동적 텍스트를 생성하고 싶다. 이를 통해 플레이어 상태에 따라 다른 내용을 보여주거나 읽기 시 특수 효과를 발동할 수 있다.

#### 수용 기준

1. WHEN ReadCommand가 실행되고 Lua_Callback_Script에 `on_read` 함수가 정의되어 있을 때, THE ReadCommand SHALL `on_read(ctx)` 함수를 호출하고 Callback_Result를 처리한다
2. WHEN `on_read(ctx)` 함수가 Callback_Result를 반환할 때, THE ReadCommand SHALL 반환된 메시지를 플레이어에게 표시한다
3. WHEN Lua_Callback_Script에 `on_read` 함수가 정의되지 않았을 때, THE ReadCommand SHALL 기존 readable 속성 기반 텍스트 표시 로직을 Fallback으로 실행한다
4. WHEN `on_read(ctx)` 실행 중 오류가 발생할 때, THE ReadCommand SHALL 오류를 로깅하고 기존 Fallback 동작을 수행한다

### 요구사항 4: Callback_Context 구성

**사용자 스토리:** 게임 디자이너로서, Lua 콜백 함수에서 플레이어 정보, 아이템 정보, 세션 정보에 접근하고 싶다. 이를 통해 플레이어 상태에 따른 조건부 동작을 구현할 수 있다.

#### 수용 기준

1. THE Item_Lua_Callback_Handler SHALL Callback_Context에 플레이어 정보(id, display_name, locale)를 포함한다
2. THE Item_Lua_Callback_Handler SHALL Callback_Context에 아이템 정보(id, template_id, name, properties)를 포함한다
3. THE Item_Lua_Callback_Handler SHALL Callback_Context에 세션 정보(locale)를 포함한다
4. THE Item_Lua_Callback_Handler SHALL Callback_Context를 LuaScriptLoader의 `_build_lua_context` 메서드를 사용하여 Lua 테이블로 변환한다
5. THE Item_Lua_Callback_Handler SHALL 아이템 이름을 다국어 dict 형태(`{en: "...", ko: "..."}`)로 Callback_Context에 포함한다


### 요구사항 5: Callback_Result 처리

**사용자 스토리:** 게임 디자이너로서, Lua 콜백의 반환값을 통해 메시지 표시, 아이템 소모, 추가 효과 등을 제어하고 싶다. 이를 통해 Lua 스크립트에서 다양한 동작을 선언적으로 정의할 수 있다.

#### 수용 기준

1. THE Item_Lua_Callback_Handler SHALL Callback_Result의 `message` 필드(다국어 dict `{en: "...", ko: "..."}`)를 플레이어 locale에 맞게 선택하여 반환한다
2. THE Item_Lua_Callback_Handler SHALL Callback_Result의 `consume` 필드(boolean)를 통해 아이템 소모 여부를 결정한다
3. WHEN Callback_Result가 nil일 때, THE Item_Lua_Callback_Handler SHALL Fallback 동작이 수행되도록 None을 반환한다
4. THE Item_Lua_Callback_Handler SHALL Callback_Result의 Lua 테이블을 Python dict로 변환하여 반환한다

### 요구사항 6: 확장 가능한 동사 지원

**사용자 스토리:** 개발자로서, use와 read 외에도 향후 새로운 동사(예: activate, open, drink 등)에 대한 Lua 콜백을 쉽게 추가할 수 있는 구조를 원한다.

#### 수용 기준

1. THE Item_Lua_Callback_Handler SHALL 동사 이름을 매개변수로 받아 `on_{verb}(ctx)` 형태의 콜백 함수를 동적으로 호출하는 범용 메서드를 제공한다
2. WHEN 새로운 동사에 대한 Lua 콜백을 추가할 때, THE Item_Command SHALL Item_Lua_Callback_Handler의 범용 메서드를 호출하는 것만으로 Lua 콜백 지원을 활성화할 수 있다
3. THE Item_Lua_Callback_Handler SHALL 지원하는 동사 목록을 하드코딩하지 않고, 스크립트에 정의된 `on_{verb}` 함수의 존재 여부로 지원 여부를 판단한다

### 요구사항 7: 오류 처리 및 로깅

**사용자 스토리:** 운영자로서, Lua 콜백 실행 중 발생하는 오류를 추적하고 디버깅할 수 있어야 한다.

#### 수용 기준

1. IF Lua 스크립트 파일 읽기에 실패하면, THEN THE Item_Lua_Callback_Handler SHALL 오류를 ERROR 레벨로 로깅하고 None을 반환한다
2. IF Lua 스크립트 실행 중 구문 오류가 발생하면, THEN THE Item_Lua_Callback_Handler SHALL template_id와 오류 내용을 ERROR 레벨로 로깅하고 None을 반환한다
3. IF 콜백 함수 실행 중 런타임 오류가 발생하면, THEN THE Item_Lua_Callback_Handler SHALL template_id, 동사 이름, 오류 내용을 ERROR 레벨로 로깅하고 None을 반환한다
4. WHEN Lua_Callback_Script가 성공적으로 로드되고 콜백이 실행될 때, THE Item_Lua_Callback_Handler SHALL template_id와 동사 이름을 DEBUG 레벨로 로깅한다
5. WHEN lupa 라이브러리가 설치되지 않았을 때, THE Item_Lua_Callback_Handler SHALL 스크립트 실행을 시도하지 않고 None을 반환한다
