# 요구사항 문서: Lua 대화 기반 교환(Exchange) 시스템

## 소개

기존 Lua 대화 시스템(DialogueInstance, DialogueManager, LuaScriptLoader, DialogueContext)을 확장하여 NPC와의 양방향 아이템 교환(Exchange) 시스템을 구현한다. NPC도 플레이어와 동일하게 인벤토리(game_objects)와 소지금(silver_coin)을 보유하며, 양쪽 모두 자원이 충분해야 거래가 성립한다. 장착 중인 아이템도 거래 대상에 포함된다. 화폐 단위는 실버(Silver)이며, 기존 레거시 shop_command.py와 trade_command.py를 대체한다.

## 용어집

- **Exchange_System**: NPC와 플레이어 간 양방향 아이템 교환을 처리하는 시스템. 양쪽 모두 인벤토리와 소지금을 기반으로 거래한다
- **Exchange_API**: Lua 스크립트에서 호출 가능한 Python 측 교환 관련 함수 집합 (인벤토리 조회, 실버 조회, 아이템 교환 등)
- **Silver_Coin**: 기본 화폐 아이템. template_id='silver_coin', weight=0.003kg(3g), category='currency', max_stack=9999
- **NPC_Inventory**: NPC(Monster)가 game_objects 테이블에 보유하는 아이템 목록 (location_type='inventory', location_id=monster_id). 스폰 시 equipment 아이템과 silver_coin이 생성됨
- **DialogueContext**: Lua 스크립트에 전달되는 읽기 전용 컨텍스트 객체 (기존 구현)
- **LuaScriptLoader**: NPC ID 기반으로 Lua 스크립트를 로드하고 실행하는 모듈 (기존 구현)
- **DialogueInstance**: 진행 중인 대화 인스턴스를 관리하는 dataclass (기존 구현)
- **DialogueManager**: 대화 인스턴스의 생성, 조회, 종료 및 메시지 전송을 담당하는 매니저 (기존 구현)
- **Player**: 플레이어 모델 (기존 구현)
- **Monster**: NPC/몬스터 모델. game_objects를 인벤토리로 사용 (기존 구현)
- **Weight_Limit**: 플레이어가 소지할 수 있는 최대 무게 제한
- **Humanoid_NPC**: 인간형 NPC. 반드시 소지품(장비, silver_coin)을 보유해야 하는 NPC 유형

## 요구사항

### 요구사항 1: 화폐 시스템 (Silver Coin)

**사용자 스토리:** 플레이어로서, 나는 게임 내 화폐(실버)를 소지하고 사용할 수 있기를 원한다. 그래야 NPC와 아이템을 교환할 수 있다.

#### 승인 기준

1. THE Exchange_System은 아이템 템플릿 'silver_coin'을 제공해야 한다 (name_en='Silver Coin', name_ko='은화', weight=0.003, category='currency', max_stack=9999)
2. THE Exchange_System은 실버를 game_objects 테이블의 스택 가능한 아이템으로 관리해야 한다 (location_type='inventory', location_id=소유자_id)
3. WHEN 소유자(플레이어 또는 NPC)가 실버를 획득하면, THE Exchange_System은 소유자 인벤토리에 기존 실버 스택이 있을 경우 수량을 증가시키고, 없을 경우 새 실버 아이템을 생성해야 한다
4. WHEN 소유자가 실버를 소비하면, THE Exchange_System은 인벤토리의 실버 스택 수량을 차감하고, 수량이 0이 되면 해당 아이템을 삭제해야 한다
5. IF 소유자의 실버 잔액이 요청된 금액보다 적으면, THEN THE Exchange_System은 거래를 거부하고 잔액 부족 사유를 반환해야 한다

### 요구사항 2: NPC 소지품 시스템

**사용자 스토리:** 게임 디자이너로서, 나는 인간형 NPC가 실버와 판매 아이템을 소지하기를 원한다. 그래야 NPC가 플레이어로부터 아이템을 매입할 때 실버가 부족하면 거래가 거부되는 현실적인 경제 시스템을 구현할 수 있다.

#### 승인 기준

1. THE NPC_Inventory는 기존 Monster 모델의 game_objects 인벤토리 시스템(location_type='inventory', location_id=monster_id)을 그대로 사용해야 한다
2. WHEN Humanoid_NPC가 스폰될 때, THE Exchange_System은 해당 NPC의 몬스터 템플릿에 정의된 silver_coin 수량을 NPC 인벤토리에 생성해야 한다
3. WHEN Humanoid_NPC가 스폰될 때, THE Exchange_System은 해당 NPC의 몬스터 템플릿에 정의된 판매 아이템 목록을 NPC 인벤토리에 생성해야 한다
4. THE NPC 몬스터 템플릿의 properties에 exchange_config 필드를 정의해야 하며, 이 필드는 initial_silver(초기 실버 수량)와 buy_margin(매입 비율, 예: 0.5 = base_value의 50%로 매입)을 포함해야 한다. 판매 아이템 목록은 별도로 정의하지 않으며, NPC 인벤토리에 실제 존재하는 아이템이 곧 판매 목록이다. 각 아이템의 가격은 아이템 properties의 base_value 필드에서 읽는다
5. WHEN NPC가 사망하면, THE Exchange_System은 기존 사망 처리 로직(인벤토리 → corpse 컨테이너 이동)을 그대로 따라야 한다

### 요구사항 3: Exchange API (Lua용)

**사용자 스토리:** 게임 디자이너로서, 나는 Lua 대화 스크립트에서 Python 측 교환 함수를 호출할 수 있기를 원한다. 그래야 대화 흐름 안에서 양방향 아이템 교환을 처리할 수 있다.

#### 승인 기준

1. THE Exchange_API는 Lua 스크립트에서 호출 가능한 조회 함수를 제공해야 한다: get_npc_inventory(npc_id), get_player_inventory(player_id), get_npc_silver(npc_id), get_player_silver(player_id)
2. THE Exchange_API는 Lua 스크립트에서 호출 가능한 교환 함수를 제공해야 한다: buy_from_npc(player_id, npc_id, game_object_id, price), sell_to_npc(player_id, npc_id, game_object_id, price)
3. THE Exchange_API의 buy_from_npc 함수는 플레이어 실버 잔액 확인, 플레이어 무게 제한 확인, 플레이어 실버 차감, NPC 실버 증가, NPC 인벤토리에서 아이템 제거, 플레이어 인벤토리에 아이템 추가를 원자적으로 수행하고 결과 테이블을 반환해야 한다
4. THE Exchange_API의 sell_to_npc 함수는 NPC 실버 잔액 확인, 아이템 소유 확인, NPC 실버 차감, 플레이어 실버 증가, 플레이어 인벤토리에서 아이템 제거, NPC 인벤토리에 아이템 추가를 원자적으로 수행하고 결과 테이블을 반환해야 한다
5. IF Exchange_API 함수 실행 중 NPC 실버 잔액이 부족하면, THEN THE Exchange_API는 거래를 거부하고 NPC 소지금 부족 사유를 반환해야 한다
6. THE Exchange_API의 모든 함수는 Lua 샌드박스 내에서 안전하게 호출되어야 하며, Python 내부 객체에 대한 직접 접근을 허용하지 않아야 한다
7. IF Exchange_API 함수 실행 중 오류가 발생하면, THEN THE Exchange_API는 오류를 로깅하고 실패 결과 테이블(success=false, error=사유)을 반환해야 한다

### 요구사항 4: 대화 흐름 기반 교환 인터페이스

**사용자 스토리:** 플레이어로서, 나는 NPC와 대화하면서 자연스럽게 교환 메뉴에 진입하고 아이템을 사고팔 수 있기를 원한다. 그래야 몰입감 있는 거래 경험을 할 수 있다.

#### 승인 기준

1. WHEN 플레이어가 교환 NPC에게 talk 명령을 실행하면, THE Lua 스크립트는 대화 인사말과 함께 교환 관련 선택지(구매, 판매 등)를 표시해야 한다
2. WHEN 플레이어가 구매 선택지를 선택하면, THE Lua 스크립트는 NPC 인벤토리에서 판매 가능한 아이템 목록을 번호, 가격, 무게 정보와 함께 선택지로 표시해야 한다
3. WHEN 플레이어가 판매 선택지를 선택하면, THE Lua 스크립트는 플레이어 인벤토리에서 판매 가능한 아이템 목록을 번호와 매입 가격과 함께 선택지로 표시해야 한다
4. WHEN 플레이어가 특정 아이템 구매 선택지를 선택하면, THE Lua 스크립트는 Exchange_API의 buy_from_npc를 호출하고 거래 결과(성공 또는 실패 사유)를 대화 텍스트로 표시해야 한다
5. WHEN 플레이어가 특정 아이템 판매 선택지를 선택하면, THE Lua 스크립트는 Exchange_API의 sell_to_npc를 호출하고 거래 결과를 대화 텍스트로 표시해야 한다
6. WHEN NPC 소지금이 부족하여 매입이 불가능하면, THE Lua 스크립트는 NPC가 소지금 부족을 알리는 대화 텍스트를 표시해야 한다
7. WHEN 거래가 완료되거나 실패한 후, THE Lua 스크립트는 교환 메인 메뉴(구매, 판매, 나가기)로 복귀하는 선택지를 제공해야 한다
8. THE Lua 스크립트의 모든 교환 대화 텍스트와 선택지는 다국어 dict 형식({en = "...", ko = "..."})으로 제공해야 한다

### 요구사항 5: 장착 아이템 거래

**사용자 스토리:** 플레이어로서, 나는 현재 장착 중인 무기나 옷도 NPC에게 판매할 수 있기를 원한다. 그래야 거래 대상에 제한 없이 자유롭게 교환할 수 있다.

#### 승인 기준

1. WHEN 플레이어가 장착 중인 아이템을 판매하면, THE Exchange_API는 해당 아이템의 장착을 해제(is_equipped=false, equipment_slot 초기화)한 후 거래를 진행해야 한다
2. WHEN NPC가 장착 중인 아이템을 플레이어에게 판매하면, THE Exchange_API는 해당 아이템의 NPC 장착 상태를 해제한 후 거래를 진행해야 한다
3. THE Lua 스크립트는 판매 목록에 장착 중인 아이템을 포함하되, 장착 상태를 표시하여 플레이어가 인지할 수 있게 해야 한다

### 요구사항 6: DialogueContext 교환 정보 확장

**사용자 스토리:** 게임 디자이너로서, 나는 Lua 스크립트에서 플레이어와 NPC의 실버 잔액, 인벤토리 정보에 접근할 수 있기를 원한다. 그래야 교환 UI에 현재 상태를 표시할 수 있다.

#### 승인 기준

1. THE DialogueContext는 플레이어의 현재 실버 잔액을 Lua 스크립트에 제공해야 한다
2. THE DialogueContext는 플레이어의 현재 인벤토리 총 무게와 Weight_Limit을 Lua 스크립트에 제공해야 한다
3. THE DialogueContext는 플레이어의 인벤토리 아이템 목록(id, name, category, weight, is_equipped, equipment_slot, properties)을 Lua 스크립트에 제공해야 한다
4. THE DialogueContext는 NPC의 현재 실버 잔액을 Lua 스크립트에 제공해야 한다
5. THE DialogueContext는 NPC의 인벤토리 아이템 목록(id, name, category, weight, is_equipped, equipment_slot, properties)을 Lua 스크립트에 제공해야 한다

### 요구사항 7: 샘플 교환 NPC Lua 스크립트

**사용자 스토리:** 개발자로서, 나는 샘플 교환 NPC Lua 스크립트를 통해 교환 시스템이 정상 동작하는지 검증할 수 있기를 원한다.

#### 승인 기준

1. THE 샘플 스크립트는 교환 NPC의 Lua 대화 스크립트로 configs/dialogues/{npc_id}.lua 경로에 위치해야 한다
2. WHEN 플레이어가 교환 NPC에게 talk 명령을 실행하면, THE 스크립트는 인사말과 함께 구매, 판매, 나가기 선택지를 표시해야 한다
3. THE 스크립트는 NPC 인벤토리 기반으로 판매 아이템 목록을 동적으로 생성해야 한다
4. THE 스크립트는 구매 성공, 플레이어 실버 부족, NPC 실버 부족, 무게 초과, 판매 성공, 장착 해제 후 판매 등 모든 거래 시나리오에 대한 다국어 메시지를 포함해야 한다
5. THE 스크립트의 모든 텍스트는 다국어 dict 형식({en = "...", ko = "..."})으로 작성해야 한다

### 요구사항 8: 레거시 명령어 Deprecated

**사용자 스토리:** 개발자로서, 나는 기존 shop_command.py와 trade_command.py를 Lua 대화 기반 교환 시스템으로 대체하여 코드 중복을 제거하고 싶다.

#### 승인 기준

1. WHEN Lua 대화 기반 교환 시스템이 완성되면, THE 레거시 shop_command.py는 deprecated 표시되어야 한다
2. WHEN Lua 대화 기반 교환 시스템이 완성되면, THE 레거시 trade_command.py는 deprecated 표시되어야 한다
3. THE 기존 상점 NPC의 monster.properties에 저장된 shop_items 데이터는 exchange_config 형식으로의 마이그레이션 가이드가 제공되어야 한다
