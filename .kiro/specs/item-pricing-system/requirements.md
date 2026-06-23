# 요구사항 문서

## 소개

아이템별 고정 매수/매도 가격 시스템과 Lua 스크립트 기반 동적 가격 조정 기능을 구현한다.
현재 시스템은 `properties.base_value`만 존재하여 매수/매도 가격 구분이 없고, 상인 Lua 스크립트에서 `base_value`에 하드코딩된 마진을 곱해 판매 가격을 산출한다.
이 기능은 아이템 가격을 DB `item_prices` 테이블에서 관리하고, PriceResolver가 `template_id`로 DB를 조회하여 가격을 산출하며, Lua 스크립트에서 평판·호감도 등 외부 조건에 따라 최종 가격을 동적으로 조정할 수 있는 구조를 제공한다.

## 용어집

- **item_prices**: 아이템 가격 정보를 저장하는 DB 테이블. `template_id`를 PRIMARY KEY로 사용하며, `buy_price`와 `sell_price`를 저장한다.
- **template_id**: 아이템 템플릿의 고유 식별자. `game_objects.properties` JSON 내의 `template_id` 필드로 저장되며, `item_prices` 테이블의 키로 사용된다.
- **buy_price**: 플레이어가 NPC로부터 아이템을 구매할 때의 고정 기준 가격 (NPC 판매가). `item_prices` 테이블에 저장.
- **sell_price**: 플레이어가 NPC에게 아이템을 판매할 때의 고정 기준 가격 (NPC 매입가). `item_prices` 테이블에 저장.
- **PriceResolver**: `template_id`로 `item_prices` DB 테이블을 조회하여 기준 가격을 반환하고, 선택적 `price_modifier`를 적용하여 최종 거래 가격을 산출하는 모듈.
- **price_modifier**: Lua 스크립트에서 반환하는 가격 조정 배율 (예: 0.9 = 10% 할인, 1.1 = 10% 할증).
- **DatabaseManager**: 비동기 SQLite 데이터베이스 연결을 관리하는 기존 모듈.
- **ExchangeManager**: 플레이어와 NPC 간 양방향 아이템 교환을 원자적으로 처리하는 기존 매니저.
- **LuaScriptLoader**: NPC 대화 스크립트를 로드하고 실행하는 기존 모듈. exchange API를 Lua 글로벌에 등록한다.
- **exchange_API**: Lua 글로벌에 등록된 교환 함수 테이블 (`exchange.buy_from_npc`, `exchange.sell_to_npc` 등).

## 요구사항

### 요구사항 1: item_prices DB 테이블에 가격 저장

**사용자 스토리:** 게임 디자이너로서, 아이템별로 NPC 구매가와 판매가를 DB에서 중앙 관리하고 싶다. 이를 통해 아이템 템플릿 JSON을 수정하지 않고도 가격을 조정할 수 있다.

#### 수용 기준

1. THE Database SHALL `item_prices` 테이블을 포함하며, 스키마는 `template_id TEXT PRIMARY KEY, buy_price INTEGER DEFAULT 0, sell_price INTEGER DEFAULT 0`이다.
2. THE item_prices 테이블 SHALL 모든 거래 가능 아이템의 `template_id`에 대해 `buy_price`와 `sell_price` 레코드를 포함한다.
3. THE item_prices 테이블 SHALL `buy_price` 값이 0 이상의 정수임을 보장한다.
4. THE item_prices 테이블 SHALL `sell_price` 값이 0 이상의 정수임을 보장한다.
5. WHEN `template_id`가 `item_prices` 테이블에 존재하지 않는 아이템에 대해 거래가 시도되면, THE PriceResolver SHALL 가격 0을 반환하여 거래가 불가능함을 나타낸다.
6. THE item_prices 테이블 SHALL 거래 불가 아이템(quest item 등)에 대해 레코드를 포함하지 않는다 (조회 시 0 반환).

### 요구사항 2: PriceResolver 모듈 구현 (DB 기반)

**사용자 스토리:** 개발자로서, 아이템의 최종 거래 가격을 `template_id` 기반 DB 조회로 일관되게 산출하는 중앙 모듈이 필요하다. 이를 통해 가격 산출 로직이 분산되지 않고 단일 지점에서 관리된다.

#### 수용 기준

1. THE PriceResolver SHALL `template_id`로 `item_prices` DB 테이블을 조회하여 `buy_price`, `sell_price` 기준 가격을 반환한다.
2. WHEN Lua 스크립트가 price_modifier를 반환하면, THE PriceResolver SHALL 기준 가격에 price_modifier를 곱하여 최종 가격을 산출한다.
3. THE PriceResolver SHALL 최종 가격을 정수로 반올림(round)하여 반환한다.
4. THE PriceResolver SHALL 최종 가격이 1 미만이 되지 않도록 최소값 1을 보장한다.
5. WHEN price_modifier가 제공되지 않으면, THE PriceResolver SHALL 기준 가격을 그대로 최종 가격으로 사용한다.
6. THE PriceResolver SHALL `async get_buy_price(template_id, price_modifier)` 메서드를 제공한다.
7. THE PriceResolver SHALL `async get_sell_price(template_id, price_modifier)` 메서드를 제공한다.
8. THE PriceResolver SHALL `__init__`에서 `DatabaseManager`를 주입받아 DB 조회에 사용한다.

### 요구사항 3: Lua 스크립트 기반 동적 가격 조정

**사용자 스토리:** 게임 디자이너로서, NPC별로 평판, 호감도 등 외부 조건에 따라 가격을 동적으로 조정하고 싶다. 이를 통해 NPC마다 다른 가격 정책을 Lua 스크립트로 제어할 수 있다.

#### 수용 기준

1. THE exchange_API SHALL Lua 글로벌에 `exchange.get_buy_price(item_id)` 함수를 등록하여 아이템의 기준 구매 가격을 조회할 수 있게 한다.
2. THE exchange_API SHALL Lua 글로벌에 `exchange.get_sell_price(item_id)` 함수를 등록하여 아이템의 기준 판매 가격을 조회할 수 있게 한다.
3. THE LuaScriptLoader SHALL Lua 컨텍스트(ctx)에 플레이어 평판, 호감도 등 외부 조건 데이터를 포함하여 전달한다.
4. WHEN Lua 스크립트가 `exchange.buy_from_npc`를 호출할 때, THE Lua_Script SHALL price 인자에 동적으로 계산된 최종 가격을 전달할 수 있다.
5. WHEN Lua 스크립트가 `exchange.sell_to_npc`를 호출할 때, THE Lua_Script SHALL price 인자에 동적으로 계산된 최종 가격을 전달할 수 있다.
6. THE exchange_API SHALL `exchange.get_item_properties(item_id)` 함수를 등록하여 아이템의 전체 속성을 Lua 테이블로 조회할 수 있게 한다.

### 요구사항 4: 기존 ExchangeManager 호환성 유지

**사용자 스토리:** 개발자로서, 새로운 가격 시스템이 기존 교환 API와 완전히 호환되어야 한다. 이를 통해 기존 Lua 스크립트가 수정 없이 동작한다.

#### 수용 기준

1. THE ExchangeManager SHALL 기존 `buy_from_npc(player_id, npc_id, game_object_id, price)` 시그니처를 변경하지 않는다.
2. THE ExchangeManager SHALL 기존 `sell_to_npc(player_id, npc_id, game_object_id, price)` 시그니처를 변경하지 않는다.
3. WHEN 기존 Lua 스크립트가 `base_value`를 사용하여 가격을 계산하는 경우, THE exchange_API SHALL 기존 동작과 동일한 결과를 생성한다.
4. THE exchange_API SHALL 기존에 등록된 모든 Lua 글로벌 함수(`get_npc_inventory`, `get_player_inventory`, `get_npc_silver`, `get_player_silver`, `buy_from_npc`, `sell_to_npc`)를 유지한다.

### 요구사항 5: 인벤토리 조회 시 가격 정보 포함

**사용자 스토리:** 게임 디자이너로서, Lua 스크립트에서 NPC/플레이어 인벤토리를 조회할 때 각 아이템의 구매/판매 가격 정보를 함께 확인하고 싶다. 이를 통해 상점 UI를 구성할 때 별도 가격 조회 없이 인벤토리 데이터만으로 가격을 표시할 수 있다.

#### 수용 기준

1. WHEN `exchange.get_npc_inventory`가 호출되면, THE exchange_API SHALL 각 아이템 항목에 `buy_price` 필드를 포함하여 반환한다.
2. WHEN `exchange.get_player_inventory`가 호출되면, THE exchange_API SHALL 각 아이템 항목에 `sell_price` 필드를 포함하여 반환한다.
3. THE exchange_API SHALL 인벤토리 항목의 가격 필드에 PriceResolver가 산출한 기준 가격을 사용한다.
