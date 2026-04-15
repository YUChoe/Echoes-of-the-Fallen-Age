# 요구사항 문서

## 소개

잿빛 항구(Greyhaven Port)의 세계관(docs/WorldView.md)에 기반하여 NPC들을 게임 맵 전역에 배치한다. 각 NPC는 대화, 분위기 연출, 상점(Exchange) 기능만 담당하며, 퀘스트 관련 기능은 완전히 제외한다. 모든 NPC는 고정 ID로 DB에 직접 등록하는 정적 방식(church_monk 패턴)으로 생성하며, Lua 대화 스크립트 파일명은 해당 NPC의 고정 ID와 일치시킨다. 거래 NPC는 기존 Exchange 시스템(CurrencyManager, ExchangeManager, Exchange API)을 활용한다. 영어 텍스트는 영국 영어(British English)를 사용한다.

## 용어집

- **NPC_Record**: monsters 테이블에 고정 ID로 직접 INSERT되는 NPC 레코드. 서버 재시작 시에도 동일한 ID를 유지한다 (church_monk 패턴)
- **NPC_Init_Script**: scripts/ 디렉토리에 위치하는 Python 스크립트로, NPC 레코드를 DB에 INSERT하고 인벤토리 아이템(장비, silver_coin)을 생성하는 일회성 초기화 스크립트

- **NPC_Template**: configs/monsters/ 디렉토리에 위치하는 JSON 파일로, NPC의 이름, 설명, 스탯, 장비, 거래 설정 등을 정의하는 참조용 템플릿 (정적 NPC의 경우 NPC_Init_Script에서 참조)
- **Lua_Dialogue_Script**: configs/dialogues/{npc_id}.lua 파일로, get_dialogue(ctx)와 on_choice(choice_number, ctx) 함수를 통해 NPC 대화 흐름을 제어. 파일명은 NPC의 고정 ID와 일치
- **Dialogue_System**: LuaScriptLoader, DialogueInstance, DialogueManager로 구성된 NPC 대화 처리 시스템
- **Exchange_System**: CurrencyManager, ExchangeManager, Exchange API(Lua 글로벌 exchange 테이블)로 구성된 NPC 거래 시스템
- **MonsterManager**: 몬스터/NPC 상태 관리를 담당하는 매니저 클래스
- **exchange_config**: NPC properties 내에서 초기 실버, 매입 마진 등 거래 조건을 정의하는 설정 블록
- **Ash_Knights**: 잿빛 기사단. 몰락 이후 남은 유일한 기사단으로, 정의를 내세우지만 잔혹한 질서도 강요하는 세력
- **Greyhaven_Port**: 잿빛 항구. 원정 패배 후 살아남은 사람들이 모여 삶을 꾸려나가는 성벽 도시
- **WorldView**: docs/WorldView.md에 정의된 카르나스(Karnas) 대륙의 세계관 설정 문서
- **Locale_Dict**: `{en = "...", ko = "..."}` 형식의 다국어 텍스트 딕셔너리

## 요구사항

### 요구사항 1: 잿빛 기사단 NPC 배치

**사용자 스토리:** 플레이어로서, 나는 마을에서 잿빛 기사단 NPC를 만나고 싶다. 그래야 기사단 조직과 고블린 위협 상황에 대해 알 수 있다.

#### 승인 기준

1. THE NPC_Init_Script SHALL Knight Lieutenant (기사단 부관) NPC를 고정 ID로 monsters 테이블에 등록하고, 좌표를 동쪽 마을 구역 (3,0) 또는 (4,0)으로 설정한다
2. THE NPC_Init_Script SHALL Knight Recruiter (기사단 모병관) NPC를 고정 ID로 monsters 테이블에 등록하고, 좌표를 마을 광장 근처 (-1,0)으로 설정한다
3. WHEN 플레이어가 Knight Lieutenant (기사단 부관)와 대화를 시작하면, THE Dialogue_System SHALL Lua_Dialogue_Script를 사용하여 Ash_Knights 조직과 고블린 위협 상황에 대한 대화 선택지를 제시한다
4. WHEN 플레이어가 Knight Recruiter (기사단 모병관)와 대화를 시작하면, THE Dialogue_System SHALL Lua_Dialogue_Script를 사용하여 Ash_Knights 입단과 성벽 안팎의 상황에 대한 대화 선택지를 제시한다
5. THE Knight Lieutenant (기사단 부관) NPC_Template SHALL monster_type을 NEUTRAL, behavior를 STATIONARY, faction_id를 ash_knights로 정의한다
6. THE Knight Recruiter (기사단 모병관) NPC_Template SHALL monster_type을 NEUTRAL, behavior를 STATIONARY, faction_id를 ash_knights로 정의한다

### 요구사항 2: 술집(여관) NPC 배치

**사용자 스토리:** 플레이어로서, 나는 술집/여관에서 다양한 인물들을 만나고 싶다. 그래야 세계의 역사와 현재 상황에 대한 이야기를 들을 수 있다.

#### 승인 기준

1. THE NPC_Init_Script SHALL Drunken Refugee (술에 취한 난민) NPC를 고정 ID로 monsters 테이블에 등록하고, 좌표를 술집/여관 (-8,-1)으로 설정한다
2. THE NPC_Init_Script SHALL Wandering Bard (떠돌이 음유시인) NPC를 고정 ID로 monsters 테이블에 등록하고, 좌표를 술집/여관 (-8,-1)으로 설정한다
3. WHEN 플레이어가 Drunken Refugee (술에 취한 난민)와 대화를 시작하면, THE Dialogue_System SHALL Lua_Dialogue_Script를 사용하여 대마법사에 대한 소문, 원정 패배 이야기, 잃어버린 가족에 대한 그리움을 담은 대화를 제시한다
4. WHEN 플레이어가 Wandering Bard (떠돌이 음유시인)와 대화를 시작하면, THE Dialogue_System SHALL Lua_Dialogue_Script를 사용하여 황금의 시대, 제국의 몰락, 세계의 현재 상황에 대한 대화를 제시한다
5. THE Drunken Refugee (술에 취한 난민) NPC_Template SHALL monster_type을 NEUTRAL, behavior를 STATIONARY, faction_id를 ash_knights로 정의한다
6. THE Wandering Bard (떠돌이 음유시인) NPC_Template SHALL monster_type을 NEUTRAL, behavior를 STATIONARY, faction_id를 ash_knights로 정의한다

### 요구사항 3: 교회 NPC 배치

**사용자 스토리:** 플레이어로서, 나는 교회 NPC들과 상호작용하고 싶다. 그래야 잊혀진 신들과 교회 지하 네크로폴리스의 위험에 대해 알 수 있다.

#### 승인 기준

1. THE NPC_Init_Script SHALL Priest (사제) NPC를 고정 ID로 monsters 테이블에 등록하고, 좌표를 교회 (2,0)으로 설정한다 (Brother Marcus와 동일 위치)
2. THE NPC_Init_Script SHALL Crypt Guard Monk (교회 지하 입구 경비 수도사) NPC를 고정 ID로 monsters 테이블에 등록하고, 좌표를 (2,-1) 또는 지하 입구로 설정한다
3. WHEN 플레이어가 Priest (사제)와 대화를 시작하면, THE Dialogue_System SHALL Lua_Dialogue_Script를 사용하여 잊혀진 신들과 네크로폴리스에 대한 경고를 담은 대화를 제시한다
4. WHEN 플레이어가 Crypt Guard Monk (교회 지하 입구 경비 수도사)와 대화를 시작하면, THE Dialogue_System SHALL Lua_Dialogue_Script를 사용하여 지하의 위험에 대한 경고와 지하 접근 제한에 대한 대화를 제시한다
5. THE Priest (사제) NPC_Template SHALL monster_type을 NEUTRAL, behavior를 STATIONARY, faction_id를 ash_knights로 정의한다
6. THE Crypt Guard Monk (교회 지하 입구 경비 수도사) NPC_Template SHALL monster_type을 NEUTRAL, behavior를 STATIONARY, faction_id를 ash_knights로 정의한다

### 요구사항 4: 성문 구역 NPC 배치

**사용자 스토리:** 플레이어로서, 나는 서쪽 성문 근처에서 NPC들을 만나고 싶다. 그래야 성벽 밖의 상황과 이주 명령에 대해 알 수 있다.

#### 승인 기준

1. THE NPC_Init_Script SHALL Gate Warden (성문 관리인) NPC를 고정 ID로 monsters 테이블에 등록하고, 좌표를 서쪽 성문 (-10,0)으로 설정한다
2. THE NPC_Init_Script SHALL Refugee (난민) NPC를 고정 ID로 monsters 테이블에 등록하고, 좌표를 서쪽 성문 근처 (-10,0) 또는 (-9,0)으로 설정한다
3. WHEN 플레이어가 Gate Warden (성문 관리인)과 대화를 시작하면, THE Dialogue_System SHALL Lua_Dialogue_Script를 사용하여 성벽 너머의 상황과 이주 명령에 대한 대화를 제시한다
4. WHEN 플레이어가 Refugee (난민)와 대화를 시작하면, THE Dialogue_System SHALL Lua_Dialogue_Script를 사용하여 가족의 생사를 모르는 상황과 절박한 분위기에 대한 대화를 제시한다
5. THE Gate Warden (성문 관리인) NPC_Template SHALL monster_type을 NEUTRAL, behavior를 STATIONARY, faction_id를 ash_knights로 정의한다
6. THE Refugee (난민) NPC_Template SHALL monster_type을 NEUTRAL, behavior를 STATIONARY, faction_id를 ash_knights로 정의한다

### 요구사항 5: 성벽 밖 마을 NPC 배치

**사용자 스토리:** 플레이어로서, 나는 성벽 밖에서 NPC들을 만나고 싶다. 그래야 쫓겨난 마을 사람들의 분노와 악화되는 사회 질서를 이해할 수 있다.

#### 승인 기준

1. THE NPC_Init_Script SHALL Disgruntled Farmer (불만 가득한 농부) NPC를 고정 ID로 monsters 테이블에 등록하고, 좌표를 성벽 밖 (-15~-13) 범위 내로 설정한다
2. THE NPC_Init_Script SHALL Former Merchant (전직 상인) NPC를 고정 ID로 monsters 테이블에 등록하고, 좌표를 성벽 밖 (-18~-20) 범위 내로 설정한다
3. WHEN 플레이어가 Disgruntled Farmer (불만 가득한 농부)와 대화를 시작하면, THE Dialogue_System SHALL Lua_Dialogue_Script를 사용하여 이주 명령에 대한 분노와 성 안 사람들에 대한 적대감을 담은 대화를 제시한다
4. WHEN 플레이어가 Former Merchant (전직 상인)와 대화를 시작하면, THE Dialogue_System SHALL Lua_Dialogue_Script를 사용하여 약탈당한 경험과 세상이 도적질로 변해가는 상황에 대한 대화를 제시한다
5. THE Disgruntled Farmer (불만 가득한 농부) NPC_Template SHALL monster_type을 NEUTRAL, behavior를 STATIONARY, faction_id를 ash_knights로 정의한다
6. THE Former Merchant (전직 상인) NPC_Template SHALL monster_type을 NEUTRAL, behavior를 STATIONARY, faction_id를 ash_knights로 정의한다

### 요구사항 6: 성(Castle) NPC 배치

**사용자 스토리:** 플레이어로서, 나는 성 안에서 NPC들을 만나고 싶다. 그래야 정치적 상황과 왕위 계승 위기에 대해 알 수 있다.

#### 승인 기준

1. THE NPC_Init_Script SHALL Royal Adviser (왕의 조언자) NPC를 고정 ID로 monsters 테이블에 등록하고, 좌표를 성 구역 (12, -2~0) 범위 내로 설정한다
2. THE NPC_Init_Script SHALL Royal Guard (왕실 경비병) NPC를 고정 ID로 monsters 테이블에 등록하고, 좌표를 성 내부 (12,-1)로 설정한다
3. WHEN 플레이어가 Royal Adviser (왕의 조언자)와 대화를 시작하면, THE Dialogue_System SHALL Lua_Dialogue_Script를 사용하여 정치적 상황과 왕위 계승 위기를 암시하는 대화를 제시한다
4. WHEN 플레이어가 Royal Guard (왕실 경비병)와 대화를 시작하면, THE Dialogue_System SHALL Lua_Dialogue_Script를 사용하여 성 접근 제한 경고와 엄격한 경비 대화를 제시한다
5. THE Royal Adviser (왕의 조언자) NPC_Template SHALL monster_type을 NEUTRAL, behavior를 STATIONARY, faction_id를 ash_knights로 정의한다
6. THE Royal Guard (왕실 경비병) NPC_Template SHALL monster_type을 NEUTRAL, behavior를 STATIONARY, faction_id를 ash_knights로 정의한다

### 요구사항 7: 항구 NPC 배치

**사용자 스토리:** 플레이어로서, 나는 항구에서 NPC들을 만나고 싶다. 그래야 바다와 절벽에 대해 알 수 있고, 숨겨진 거래 기회를 발견할 수 있다.

#### 승인 기준

1. THE NPC_Init_Script SHALL Fisherman (어부) NPC를 고정 ID로 monsters 테이블에 등록하고, 좌표를 항구 근처 (0,8)로 설정한다
2. THE NPC_Init_Script SHALL Smuggler (밀수업자) NPC를 고정 ID로 monsters 테이블에 등록하고, 좌표를 항구 근처 (0,7)로 설정한다
3. WHEN 플레이어가 Fisherman (어부)와 대화를 시작하면, THE Dialogue_System SHALL Lua_Dialogue_Script를 사용하여 바다, 절벽, 잔교의 상태에 대한 대화를 제시한다
4. WHEN 플레이어가 Smuggler (밀수업자)와 대화를 시작하면, THE Dialogue_System SHALL Lua_Dialogue_Script를 사용하여 Exchange_System을 통한 숨겨진 물품 거래 인터페이스로 이어지는 대화를 제시한다
5. THE Smuggler (밀수업자) NPC_Template SHALL 거래 기능을 위해 initial_silver와 buy_margin을 정의하는 exchange_config 블록을 포함한다
6. THE Fisherman (어부) NPC_Template SHALL monster_type을 NEUTRAL, behavior를 STATIONARY, faction_id를 ash_knights로 정의한다
7. THE Smuggler (밀수업자) NPC_Template SHALL monster_type을 NEUTRAL, behavior를 STATIONARY, faction_id를 ash_knights로 정의한다

### 요구사항 8: NPC 레코드 및 초기화 스크립트 일관성

**사용자 스토리:** 개발자로서, 나는 모든 새 NPC가 고정 ID로 DB에 직접 등록되고, 초기화 스크립트가 멱등성을 보장하기를 원한다. 그래야 서버 재시작 시에도 NPC ID가 변하지 않고 Lua 스크립트와 안정적으로 매칭된다.

#### 승인 기준

1. THE 각 새 NPC의 NPC_Record SHALL monsters 테이블의 모든 필수 컬럼을 포함한다: id (사전 생성된 UUID), name_en, name_ko, description_en, description_ko, monster_type, behavior, faction_id, stats, x, y, is_alive, properties
2. THE 각 NPC_Record의 name과 description SHALL en과 ko 모두 설정한다
3. THE 각 NPC_Record의 en 텍스트 SHALL 영국 영어(British English) 철자와 어휘를 사용한다
4. THE 각 NPC_Record의 x, y 좌표 SHALL 해당 NPC가 배치될 방의 좌표와 일치해야 한다
5. THE 모든 비전투 NPC의 experience_reward와 gold_reward SHALL 0으로 설정한다
6. THE 모든 비전투 NPC의 respawn_time SHALL 0으로 설정한다
7. THE NPC_Init_Script SHALL 이미 동일 ID의 레코드가 존재하면 INSERT를 건너뛰는 멱등성을 보장한다

### 요구사항 9: Lua 대화 스크립트 구조 일관성

**사용자 스토리:** 개발자로서, 나는 모든 새 NPC 대화 스크립트가 기존 Lua 스크립팅 패턴을 따르기를 원한다. 그래야 Dialogue_System이 올바르게 로드하고 실행할 수 있다.

#### 승인 기준

1. THE 각 새 NPC의 Lua_Dialogue_Script SHALL text (Locale_Dict 배열)와 choices (Locale_Dict 테이블)를 포함하는 테이블을 반환하는 get_dialogue(ctx) 함수를 구현한다
2. THE 각 새 NPC의 Lua_Dialogue_Script SHALL 플레이어 선택을 처리하고 대화 응답 테이블을 반환하는 on_choice(choice_number, ctx) 함수를 구현한다
3. THE 각 Lua_Dialogue_Script의 text 값 SHALL en과 ko 키를 모두 포함하는 Locale_Dict 형식을 사용한다
4. THE 각 Lua_Dialogue_Script의 en 텍스트 SHALL 영국 영어(British English) 철자와 어휘를 사용한다
5. WHEN 대화에 더 이상 선택지가 없으면, THE Lua_Dialogue_Script SHALL on_choice에서 nil을 반환하여 대화 종료를 알린다

### 요구사항 10: 거래 NPC의 Exchange 시스템 통합

**사용자 스토리:** 개발자로서, 나는 거래 NPC가 기존 Exchange 시스템을 사용하기를 원한다. 그래야 구매와 판매가 기존 상인 패턴과 일관되게 작동한다.

#### 승인 기준

1. THE 각 거래 NPC의 Lua_Dialogue_Script SHALL 모든 거래에 exchange.buy_from_npc()와 exchange.sell_to_npc() API 함수를 사용한다
2. THE 각 거래 NPC의 NPC_Template SHALL initial_silver와 buy_margin 값을 포함하는 exchange_config 블록을 포함한다
3. THE 각 거래 NPC의 Lua_Dialogue_Script SHALL 기존 merchant_sample.lua의 선택지 번호 규칙을 따른다: 1-99는 메뉴 탐색, 101-199는 구매 아이템, 201-299는 판매 아이템
4. IF 실버 부족으로 거래가 실패하면, THEN THE Lua_Dialogue_Script SHALL Locale_Dict 형식의 적절한 오류 메시지를 반환한다
5. IF 무게 제한 초과로 거래가 실패하면, THEN THE Lua_Dialogue_Script SHALL Locale_Dict 형식의 적절한 오류 메시지를 반환한다

### 요구사항 11: 세계관 충실도

**사용자 스토리:** 플레이어로서, 나는 NPC 대화가 WorldView 설정을 충실히 반영하기를 원한다. 그래야 게임 세계가 일관되고 몰입감 있게 느껴진다.

#### 승인 기준

1. THE Ash_Knights NPC들의 Lua_Dialogue_Script SHALL WorldView와 일관되게 기사단의 정의와 잔혹한 질서라는 이중적 성격을 언급한다
2. THE 술집 NPC들의 Lua_Dialogue_Script SHALL WorldView와 일관되게 대마법사 소문, 원정 패배, 황금의 시대를 언급한다
3. THE 교회 NPC들의 Lua_Dialogue_Script SHALL WorldView와 일관되게 잊혀진 신들과 네크로폴리스를 언급한다
4. THE 성문 및 성벽 밖 NPC들의 Lua_Dialogue_Script SHALL WorldView와 일관되게 이주 명령, 성 안 사람들에 대한 적대감, 악화되는 사회 질서를 언급한다
5. THE 성 NPC들의 Lua_Dialogue_Script SHALL WorldView와 일관되게 왕위 계승권자인 동생과 아들의 행방불명 이후의 정치적 상황과 왕위 계승 위기를 언급한다
6. THE 항구 NPC들의 Lua_Dialogue_Script SHALL WorldView와 일관되게 북쪽 절벽, 좁은 선착장, 폐허가 된 남쪽 항구를 언급한다
7. THE Dialogue_System SHALL WorldView와 일관되게 마법이 존재하지 않으며 사람들이 그러한 현상을 행하지도 믿지도 않는 세계를 표현한다
