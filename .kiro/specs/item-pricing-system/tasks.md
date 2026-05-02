# 구현 계획: 아이템 가격 시스템 (Item Pricing System)

## 개요

아이템별 고정 매수/매도 가격 시스템과 Lua 스크립트 기반 동적 가격 조정 기능을 구현한다.
가격 데이터를 DB `item_prices` 테이블에서 관리하고, PriceResolver가 `template_id`로 DB를 조회하여 가격을 산출한다.
DB 마이그레이션, PriceResolver 변경, LuaScriptLoader 변경 순서로 진행하며,
각 단계마다 단위 테스트와 속성 기반 테스트로 정확성을 검증한다.

## Tasks

- [ ] 1. PriceResolver 모듈 변경 (DB 기반)
  - [x] 1.1 PriceResolver 클래스를 async + template_id 기반으로 변경
    - `src/mud_engine/game/managers/price_resolver.py` 수정
    - `__init__(self, db_manager: DatabaseManager)` — DatabaseManager 주입
    - `async get_buy_price(self, template_id: str, price_modifier: float | None = None) -> int` — DB 조회
    - `async get_sell_price(self, template_id: str, price_modifier: float | None = None) -> int` — DB 조회
    - 기존 `item_properties` 파라미터 제거
    - `item_prices` 테이블에서 `template_id`로 `SELECT buy_price, sell_price` 조회
    - `template_id` 미존재 시 0 반환 (거래 불가)
    - `price_modifier` 적용 후 `round()`, 양수일 때 `max(1, value)` 보장
    - 방어적 프로그래밍: `template_id`가 None/빈 문자열이면 0 반환, DB 조회 실패 시 0 반환
    - mypy + ruff 통과 확인
    - _Requirements: 1.1, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8_

  - [ ]* 1.2 PriceResolver 단위 테스트 작성
    - `tests/unit/test_price_resolver.py` 수정
    - `template_id`가 `item_prices`에 존재할 때 해당 가격 반환 테스트
    - `template_id`가 `item_prices`에 미존재 시 0 반환 테스트
    - `price_modifier` 적용 시 곱셈 및 반올림 테스트
    - `price_modifier` 미제공 시 기준 가격 그대로 반환 테스트
    - None 입력, 빈 문자열 등 에러 케이스 테스트
    - _Requirements: 1.5, 2.1, 2.2, 2.3, 2.4, 2.5_

  - [ ]* 1.3 Property 1 속성 기반 테스트: template_id 기반 DB 조회
    - **Property 1: template_id 기반 DB 조회**
    - hypothesis 라이브러리로 `template_id`를 랜덤 생성하여 item_prices 테이블 존재 여부에 따른 반환값 검증
    - `template_id`가 item_prices에 존재 시 `get_buy_price(template_id, None)` == DB의 `buy_price` 값
    - `template_id`가 item_prices에 미존재 시 `get_buy_price(template_id, None)` == 0
    - `template_id`가 item_prices에 존재 시 `get_sell_price(template_id, None)` == DB의 `sell_price` 값
    - `template_id`가 item_prices에 미존재 시 `get_sell_price(template_id, None)` == 0
    - **Validates: Requirements 1.1, 1.5, 1.6, 2.1, 2.5**

  - [ ]* 1.4 Property 2 속성 기반 테스트: price_modifier 적용
    - **Property 2: price_modifier 적용**
    - hypothesis 라이브러리로 유효한 `template_id`(item_prices에 존재)와 양의 실수 `price_modifier`를 랜덤 생성
    - `get_buy_price(template_id, modifier)` == `max(1, round(base_price * modifier))` 검증
    - `get_sell_price(template_id, modifier)` == `max(1, round(base_price * modifier))` 검증
    - 반환값이 항상 int 타입인지 검증
    - **Validates: Requirements 2.2, 2.3, 2.5**

  - [ ]* 1.5 Property 3 속성 기반 테스트: 최소값 1 보장
    - **Property 3: 최소값 1 보장**
    - hypothesis 라이브러리로 양수 `buy_price`/`sell_price`를 가진 template_id와 극단적으로 작은 `price_modifier` (0.001 등) 생성
    - `get_buy_price(template_id, modifier)` >= 1 검증
    - `get_sell_price(template_id, modifier)` >= 1 검증
    - **Validates: Requirements 2.4**

- [ ] 2. Checkpoint - PriceResolver 검증
  - mypy + ruff 통과 확인
  - 모든 테스트 통과 확인, 문제 발생 시 사용자에게 질문

- [ ] 3. LuaScriptLoader 변경 (template_id 기반)
  - [x] 3.1 가격 조회 함수를 template_id 기반으로 변경
    - `get_buy_price(item_id)` 내부: `item.properties` 대신 `item.properties.get("template_id")`로 PriceResolver 호출
    - `get_sell_price(item_id)` 내부: 동일하게 `template_id` 기반으로 변경
    - PriceResolver가 async이므로 `_run_async()` 래퍼 사용
    - PriceResolver 생성 시 `DatabaseManager` 주입 (ExchangeManager에서 참조)
    - mypy + ruff 통과 확인
    - _Requirements: 3.1, 3.2, 4.4_

  - [x] 3.2 인벤토리 조회 함수의 가격 산출을 template_id 기반으로 변경
    - `_inventory_to_lua()` 내부의 `price_resolver.get_buy_price(item.properties)` → `_run_async(price_resolver.get_buy_price(template_id))` 변경
    - `_inventory_to_lua()` 내부의 `price_resolver.get_sell_price(item.properties)` → `_run_async(price_resolver.get_sell_price(template_id))` 변경
    - 기존 반환 구조 유지하면서 내부 구현만 변경 (하위 호환성)
    - mypy + ruff 통과 확인
    - _Requirements: 5.1, 5.2, 5.3, 4.3, 4.4_

  - [ ]* 3.3 LuaScriptLoader 변경 단위 테스트 작성
    - `tests/unit/test_exchange_api.py`에 테스트 추가/수정
    - `exchange.get_buy_price(item_id)` 호출 시 DB에서 올바른 가격 반환 테스트
    - `exchange.get_sell_price(item_id)` 호출 시 DB에서 올바른 가격 반환 테스트
    - `template_id`가 item_prices에 없는 아이템 조회 시 0 반환 테스트
    - `get_npc_inventory` 반환에 `buy_price` 필드 포함 테스트
    - `get_player_inventory` 반환에 `sell_price` 필드 포함 테스트
    - 기존 테스트가 수정 없이 통과하는지 확인 (하위 호환성)
    - _Requirements: 3.1, 3.2, 4.1, 4.2, 4.3, 4.4, 5.1, 5.2, 5.3_

- [ ] 4. Checkpoint - LuaScriptLoader 변경 검증
  - mypy + ruff 통과 확인
  - 모든 테스트 통과 확인, 문제 발생 시 사용자에게 질문

- [x] 5. DB 마이그레이션 및 초기 데이터
  - [x] 5.1 schema.py에 item_prices 테이블 정의 추가
    - `src/mud_engine/database/schema.py`의 `DATABASE_SCHEMA` 리스트에 item_prices 테이블 CREATE 문 추가
    - `verify_schema()`의 `expected_tables`에 `item_prices` 추가
    - mypy + ruff 통과 확인
    - _Requirements: 1.1_

  - [x] 5.2 마이그레이션 스크립트: item_prices 테이블 생성 + 초기 데이터 INSERT
    - `migrate_database()`에 item_prices 테이블 존재 확인 및 생성 로직 추가
    - 초기 데이터 INSERT (27개 거래 가능 아이템):
      - health_potion: buy=20, sell=7
      - stamina_potion: buy=16, sell=5
      - bread: buy=4, sell=1
      - club: buy=15, sell=5
      - guard_sword: buy=50, sell=12
      - guard_heavy_sword: buy=100, sell=25
      - guard_halberd: buy=80, sell=20
      - guard_spear: buy=60, sell=15
      - rusty_dagger: buy=8, sell=2
      - guide_walking_stick: buy=10, sell=3
      - rope: buy=10, sell=3
      - torch: buy=7, sell=2
      - backpack: buy=25, sell=8
      - saddle: buy=50, sell=15
      - leather_bridle: buy=30, sell=10
      - horse_brush: buy=12, sell=4
      - horseshoe: buy=8, sell=3
      - oats: buy=6, sell=2
      - hay_bale: buy=5, sell=2
      - oak_branch: buy=3, sell=1
      - forest_mushroom: buy=2, sell=1
      - wild_berries: buy=1, sell=0
      - smooth_stone: buy=1, sell=0
      - wildflower_crown: buy=3, sell=1
      - empty_bottle: buy=2, sell=1
      - merchant_journal: buy=20, sell=8
      - forgotten_scripture: buy=15, sell=5
    - 거래 불가 아이템은 item_prices에 레코드 없음 (조회 시 0 반환)
    - INSERT OR IGNORE로 멱등성 보장
    - mypy + ruff 통과 확인
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.6_

  - [x] 5.3 DATABASE_SCHEMA.md 업데이트
    - `data/DATABASE_SCHEMA.md`에 item_prices 테이블 문서 추가
    - 테이블 스키마, 필드 설명, 초기 데이터 목록 기재
    - _Requirements: 1.1_

- [x] 6. 최종 Checkpoint - 전체 시스템 검증
  - mypy + ruff 통과 확인
  - 전체 테스트 스위트 통과 확인
  - 기존 테스트가 수정 없이 통과하는지 확인 (하위 호환성)
  - 문제 발생 시 사용자에게 질문

## Notes

- `*` 표시된 태스크는 선택 사항이며 빠른 MVP를 위해 건너뛸 수 있습니다
- 각 태스크는 특정 요구사항을 참조하여 추적 가능합니다
- Checkpoint에서 증분 검증을 수행합니다
- 속성 기반 테스트(Property-Based Tests)는 hypothesis 라이브러리를 사용합니다
- 정적 검사(mypy + ruff)는 각 구현 단계마다 필수 통과해야 합니다
- ExchangeManager는 시그니처 변경 없이 유지됩니다
- 기존 아이템 템플릿 JSON의 buy_price/sell_price 필드는 DB로 이전되므로 더 이상 사용하지 않습니다
- PriceResolver는 동기 → 비동기로 변경되므로 LuaScriptLoader에서 `_run_async()` 래퍼 필요
