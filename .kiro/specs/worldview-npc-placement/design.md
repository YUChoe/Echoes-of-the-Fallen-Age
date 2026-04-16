# 설계 문서: WorldView 기반 NPC 배치

## 개요

잿빛 항구(Greyhaven Port) 세계관에 기반하여 14개의 NPC를 게임 맵에 배치한다. 모든 NPC는 코드 변경 없이 데이터(DB INSERT + Lua 대화 스크립트 + JSON 템플릿)만 추가하는 방식으로 구현한다.

핵심 설계 결정:
- 정적 DB INSERT 방식(church_monk 패턴): 사전 생성된 UUID로 monsters 테이블에 직접 등록
- NPC_Init_Script(Python): scripts/ 디렉토리에 위치하는 일회성 초기화 스크립트
- Lua 대화 스크립트: configs/dialogues/{npc_id}.lua 파일명 규칙
- 거래 NPC(밀수업자): exchange_config를 properties에 포함, game_objects에 silver_coin + 판매 아이템 INSERT
- 멱등성: 동일 ID가 이미 존재하면 INSERT 건너뜀

## 아키텍처

### 시스템 구성도

```mermaid
graph TD
    A[NPC_Init_Script<br/>scripts/init_worldview_npcs.py] -->|INSERT| B[monsters 테이블]
    A -->|INSERT| C[game_objects 테이블<br/>거래 NPC 전용]
    D[NPC_Template JSON<br/>configs/monsters/*.json] -->|참조용| A
    E[Lua_Dialogue_Script<br/>configs/dialogues/{npc_id}.lua] -->|런타임 로드| F[LuaScriptLoader]
    F --> G[DialogueInstance]
    G --> H[DialogueManager]
    B -->|MonsterManager 로드| I[게임 서버]
    C -->|Exchange_System| I
```

### 데이터 흐름

1. 서버 시작 전: `NPC_Init_Script` 실행 → monsters/game_objects 테이블에 데이터 INSERT
2. 서버 시작: `MonsterManager`가 monsters 테이블에서 NPC 로드
3. 플레이어 대화: `DialogueManager` → `DialogueInstance` → `LuaScriptLoader`가 `configs/dialogues/{npc_id}.lua` 실행
4. 거래 NPC: `DialogueContext.build_with_exchange()` → `Exchange API` (exchange.buy_from_npc / exchange.sell_to_npc)

### 기존 시스템과의 관계

이 설계는 기존 시스템에 코드 변경을 가하지 않는다. 활용하는 기존 컴포넌트:

| 컴포넌트 | 역할 | 변경 여부 |
|---|---|---|
| MonsterManager | monsters 테이블에서 NPC 로드 | 변경 없음 |
| LuaScriptLoader | configs/dialogues/ 에서 Lua 스크립트 로드 | 변경 없음 |
| DialogueInstance | Lua get_dialogue/on_choice 실행 | 변경 없음 |
| DialogueContext | 플레이어/NPC/세션 정보를 Lua에 전달 | 변경 없음 |
| CurrencyManager | silver_coin 스택 관리 | 변경 없음 |
| ExchangeManager | buy_from_npc/sell_to_npc 원자적 거래 | 변경 없음 |
| Exchange API | Lua 글로벌 exchange 테이블 | 변경 없음 |

## 컴포넌트 및 인터페이스

### 1. NPC_Init_Script (scripts/init_worldview_npcs.py)

일회성 Python 스크립트로, 14개 NPC를 DB에 등록한다.

```python
# 의사 코드
# 각 NPC의 UUID는 스크립트 내에서 상수로 사전 정의
NPC_LIST = [
    {"id": "a1b2c3d4-...", "name_en": "Knight Lieutenant", ...},
    ...
]

async def main():
    db_manager = await get_database_manager()

    for npc in NPC_LIST:
        # 멱등성: 이미 존재하면 건너뜀
        existing = await db_manager.execute(
            "SELECT id FROM monsters WHERE id = ?", (npc['id'],)
        )
        if existing.fetchone():
            print(f"SKIP: {npc['id']} 이미 존재")
            continue

        await db_manager.execute("""
            INSERT INTO monsters (
                id, name_en, name_ko, description_en, description_ko,
                monster_type, behavior, stats, drop_items,
                respawn_time, is_alive, aggro_range, roaming_range,
                properties, faction_id, x, y
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, npc_values)

        # 거래 NPC인 경우 silver_coin + 판매 아이템 INSERT
        if npc.get('exchange_config'):
            await insert_exchange_items(db_manager, npc)
```

스크립트 실행: `./script_test.sh init_worldview_npcs`

### 2. NPC_Template JSON (configs/monsters/)

각 NPC의 참조용 템플릿. NPC_Init_Script에서 데이터 소스로 사용한다. 실제 spawn_config 기반 스폰은 사용하지 않으며, 정적 INSERT의 데이터 정의 역할만 한다.

### 3. Lua_Dialogue_Script (configs/dialogues/{npc_id}.lua)

각 NPC별 대화 스크립트. 기존 패턴(3914fbe8...lua, merchant_sample.lua)을 따른다.

일반 NPC 인터페이스:
```lua
function get_dialogue(ctx)
    -- ctx.player.display_name, ctx.npc.name, ctx.session.locale 사용
    return {
        text = { {en = "...", ko = "..."} },
        choices = { [1] = {en = "...", ko = "..."} }
    }
end

function on_choice(choice_number, ctx)
    -- 선택지 처리, nil 반환 시 대화 종료
    return { text = {...}, choices = {...} }
end
```

거래 NPC 인터페이스 (merchant_sample.lua 패턴):
```lua
-- 선택지 번호 규칙:
--   1-99: 메뉴 탐색
--   101-199: 구매 아이템 (인덱스 = 번호 - 100)
--   201-299: 판매 아이템 (인덱스 = 번호 - 200)

function get_dialogue(ctx) ... end
function on_choice(choice_number, ctx) ... end
-- exchange.buy_from_npc(), exchange.sell_to_npc() API 사용
```

## 데이터 모델

### monsters 테이블 INSERT 구조

각 NPC 레코드의 컬럼 매핑:

| 컬럼 | 타입 | 설명 | 예시 |
|---|---|---|---|
| id | TEXT PK | 사전 생성된 UUID (= Lua 파일명) | `a1b2c3d4-e5f6-...` |
| name_en | TEXT | 영국 영어 이름 | `Knight Lieutenant` |
| name_ko | TEXT | 한국어 이름 | `기사단 부관` |
| description_en | TEXT | 영국 영어 설명 | `A stern officer of the Ash Knights...` |
| description_ko | TEXT | 한국어 설명 | `잿빛 기사단의 엄격한 장교...` |
| monster_type | TEXT | NPC 타입 | `neutral` |
| behavior | TEXT | 행동 패턴 | `stationary` |
| stats | TEXT (JSON) | D&D 기반 능력치 | `{"strength": 16, ...}` |
| drop_items | TEXT (JSON) | 드롭 아이템 (비전투 NPC는 빈 배열) | `[]` |
| respawn_time | INTEGER | 리스폰 시간 (비전투 NPC는 0) | `0` |
| is_alive | BOOLEAN | 생존 여부 | `TRUE` |
| aggro_range | INTEGER | 어그로 범위 (비전투 NPC는 0) | `0` |
| roaming_range | INTEGER | 로밍 범위 (비전투 NPC는 0) | `0` |
| properties | TEXT (JSON) | 추가 속성 (exchange_config 포함 가능) | `{"template_id": "..."}` |
| faction_id | TEXT FK | 세력 ID | `ash_knights` |
| x | INTEGER | X 좌표 | `3` |
| y | INTEGER | Y 좌표 | `0` |

### 14개 NPC 상세 정의

#### 구역 1: 잿빛 기사단 (동쪽 마을)

| ID (UUID) | 이름 (en/ko) | 좌표 | faction_id | 특이사항 |
|---|---|---|---|---|
| NPC_Init_Script에서 생성 | Knight Lieutenant / 기사단 부관 | (3, 0) | ash_knights | 기사단 조직, 고블린 위협 대화 |
| NPC_Init_Script에서 생성 | Knight Recruiter / 기사단 모병관 | (-1, 0) | ash_knights | 입단 권유, 성벽 안팎 상황 대화 |

#### 구역 2: 술집/여관

| ID (UUID) | 이름 (en/ko) | 좌표 | faction_id | 특이사항 |
|---|---|---|---|---|
| NPC_Init_Script에서 생성 | Drunken Refugee / 술에 취한 난민 | (-8, -1) | ash_knights | 대마법사 소문, 원정 패배, 가족 그리움 |
| NPC_Init_Script에서 생성 | Wandering Bard / 떠돌이 음유시인 | (-8, -1) | ash_knights | 황금의 시대, 제국 몰락, 현재 상황 |

#### 구역 3: 교회

| ID (UUID) | 이름 (en/ko) | 좌표 | faction_id | 특이사항 |
|---|---|---|---|---|
| NPC_Init_Script에서 생성 | Priest / 사제 | (2, 0) | ash_knights | 잊혀진 신들, 네크로폴리스 경고 |
| NPC_Init_Script에서 생성 | Crypt Guard Monk / 교회 지하 입구 경비 수도사 | (2, -1) | ash_knights | 지하 위험 경고, 접근 제한 |

#### 구역 4: 성문

| ID (UUID) | 이름 (en/ko) | 좌표 | faction_id | 특이사항 |
|---|---|---|---|---|
| NPC_Init_Script에서 생성 | Gate Warden / 성문 관리인 | (-10, 0) | ash_knights | 성벽 너머 상황, 이주 명령 |
| NPC_Init_Script에서 생성 | Refugee / 난민 | (-9, 0) | ash_knights | 가족 생사 불명, 절박한 분위기 |

#### 구역 5: 성벽 밖

| ID (UUID) | 이름 (en/ko) | 좌표 | faction_id | 특이사항 |
|---|---|---|---|---|
| NPC_Init_Script에서 생성 | Disgruntled Farmer / 불만 가득한 농부 | (-14, 0) | ash_knights | 이주 명령 분노, 성 안 적대감 |
| NPC_Init_Script에서 생성 | Former Merchant / 전직 상인 | (-18, 0) | ash_knights | 약탈 경험, 도적질 변화 |

#### 구역 6: 성(Castle)

| ID (UUID) | 이름 (en/ko) | 좌표 | faction_id | 특이사항 |
|---|---|---|---|---|
| NPC_Init_Script에서 생성 | Royal Adviser / 왕의 조언자 | (12, -2) | ash_knights | 정치 상황, 왕위 계승 위기 |
| NPC_Init_Script에서 생성 | Royal Guard / 왕실 경비병 | (12, -1) | ash_knights | 성 접근 제한, 엄격한 경비 |

#### 구역 7: 항구

| ID (UUID) | 이름 (en/ko) | 좌표 | faction_id | 특이사항 |
|---|---|---|---|---|
| NPC_Init_Script에서 생성 | Fisherman / 어부 | (0, 8) | ash_knights | 바다, 절벽, 잔교 상태 |
| NPC_Init_Script에서 생성 | Smuggler / 밀수업자 | (0, 7) | ash_knights | exchange_config 포함, 숨겨진 거래 |

### 거래 NPC (Smuggler) 추가 데이터

Smuggler의 properties에 exchange_config 블록을 포함한다:

```json
{
    "exchange_config": {
        "initial_silver": 300,
        "buy_margin": 0.4
    }
}
```

game_objects 테이블에 추가할 아이템:
- silver_coin: Smuggler 인벤토리에 initial_silver 수량만큼 스택
- 판매 아이템: 밀수품 (rope, torch 등 기존 아이템 템플릿 활용)

### NPC 스탯 설계 기준

모든 NPC는 비전투 NPC이므로:
- experience_reward = 0, gold_reward = 0 (properties에 포함하지 않음, DB 기본값 사용)
- respawn_time = 0
- aggro_range = 0, roaming_range = 0
- is_alive = TRUE

스탯은 NPC 역할에 맞게 설정:
- 기사단 NPC: 높은 strength, constitution
- 왕실 NPC: 높은 intelligence, wisdom, charisma
- 상인/밀수업자: 높은 charisma, dexterity
- 일반 주민: 평균적 스탯

### faction_id 매핑

모든 NPC는 ash_knights 소속으로 설정한다.

| faction_id | NPC 목록 |
|---|---|
| `ash_knights` | 14개 NPC 전체 |

## 오류 처리

### NPC_Init_Script 오류 처리

| 오류 상황 | 처리 방식 |
|---|---|
| DB 연결 실패 | 에러 메시지 출력 후 exit(1) |
| 동일 ID 이미 존재 | SKIP 로그 출력, 다음 NPC 진행 (멱등성) |
| INSERT 실패 | 에러 로그 출력, 해당 NPC 건너뛰고 계속 진행 |
| game_objects INSERT 실패 (거래 NPC) | 에러 로그 출력, 해당 아이템 건너뛰고 계속 진행 |

### Lua 대화 스크립트 오류 처리

| 오류 상황 | 처리 방식 |
|---|---|
| Lua 파일 미존재 | LuaScriptLoader가 폴백 대화 ("...") 반환 (기존 동작) |
| get_dialogue 실행 오류 | DialogueInstance가 폴백 대화 반환 (기존 동작) |
| on_choice nil 반환 | 대화 종료 처리 (기존 동작) |
| exchange API 호출 실패 | Lua 스크립트 내에서 에러 메시지 반환 (merchant_sample.lua 패턴) |

### 거래 오류 처리 (Smuggler)

| 오류 상황 | Lua 스크립트 응답 |
|---|---|
| 실버 부족 (insufficient_silver) | Locale_Dict 형식 에러 메시지 반환 |
| 무게 초과 (weight_exceeded) | Locale_Dict 형식 에러 메시지 반환 |
| NPC 실버 부족 (npc_insufficient_silver) | Locale_Dict 형식 에러 메시지 반환 |
| 기타 거래 실패 | 일반 에러 메시지 반환 |

## 테스팅 전략

이 기능은 코드 변경 없이 데이터(DB INSERT + config 파일)만 추가하는 작업이므로, Property-Based Testing은 적용하지 않는다. 데이터 정합성과 런타임 동작을 검증하는 수동/스크립트 기반 테스트를 수행한다.

### 검증 스크립트 (scripts/verify_worldview_npcs.py)

NPC_Init_Script 실행 후 데이터 정합성을 검증하는 스크립트:

1. 14개 NPC가 모두 monsters 테이블에 존재하는지 확인
2. 각 NPC의 필수 컬럼(name_en, name_ko, description_en, description_ko, x, y)이 올바른지 확인
3. 각 NPC의 UUID에 대응하는 Lua 파일이 configs/dialogues/ 에 존재하는지 확인
4. 거래 NPC(smuggler)의 exchange_config가 properties에 포함되어 있는지 확인
5. 거래 NPC의 game_objects(silver_coin, 판매 아이템)가 존재하는지 확인

### Telnet 수동 테스트

서버 실행 후 Telnet MCP를 사용하여:

1. 각 NPC 위치로 이동 (goto 명령어)
2. look 명령어로 NPC 존재 확인
3. talk {npc_name} 명령어로 대화 시작
4. 대화 선택지 탐색 및 응답 확인
5. 거래 NPC(smuggler)의 구매/판매 기능 확인
6. 세계관 일관성 확인 (영국 영어, WorldView 반영)

### 멱등성 테스트

NPC_Init_Script를 2회 연속 실행하여:
- 첫 실행: 14개 NPC 모두 INSERT 성공
- 두 번째 실행: 14개 NPC 모두 SKIP (이미 존재)
- DB 상태가 동일한지 확인
