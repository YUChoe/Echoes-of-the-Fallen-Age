# 구현 계획: 아이템 가격 시스템 (Item Pricing System)

## 개요

아이템별 고정 매수/매도 가격 시스템과 Lua 스크립트 기반 동적 가격 조정 기능을 구현한다.
PriceResolver 신규 모듈 생성, LuaScriptLoader 확장, 아이템 템플릿 JSON 업데이트 순서로 진행하며,
각 단계마다 단위 테스트와 속성 기반 테스트로 정확성을 검증한다.

## Tasks

- [ ] 1. PriceResolver 모듈 구현
  - [ ] 1.1 PriceResolver 클래스 생성
    - `src/mud_engine/game/managers/price_resolver.py` 파일 생성
    - `PriceResolver` 클래스에 `get_buy_price(item_properties, price_modifier)` 메서드 구현
    - `PriceResolver` 클래스에 `get_sell_price(item_properties, price_modifier)` 메서드 구현
    - 가격 산출 규칙: `buy_price`/`sell_price` 미정의 시 0 반환, `price_modifier` 적용 후 `round()`, 양수일 때 `max(1, value)` 보장
    - 방어적 프로그래밍: `item_properties`가 None이면 0 반환, 음수 가격은 `max(1, value)`로 보정
    - `managers/__init__.py`에 PriceResolver export 추가
    - mypy + ruff 통과 확인
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

  - [ ]* 1.2 PriceResolver 단위 테스트 작성
    - `tests/unit/test_price_resolver.py` 파일 생성
    - `buy_price` 정의 시 해당 값 반환 테스트
    - `sell_price` 정의 시 해당 값 반환 테스트
    - `buy_price`/`sell_price` 미정의 시 0 반환 테스트
    - `price_modifier` 적용 시 곱셈 및 반올림 테스트
    - `price_modifier` 미제공 시 기준 가격 그대로 반환 테스트
    - None 입력, 빈 dict 등 에러 케이스 테스트
    - _Requirements: 1.5, 2.1, 2.2, 2.3, 2.4, 2.5_

  - [ ]* 1.3 Property 1 속성 기반 테스트: 가격 필드 직접 사용
    - **Property 1: 가격 필드 직접 사용**
    - hypothesis 라이브러리로 `item_properties` dict를 랜덤 생성하여 `buy_price`/`sell_price` 키 존재 여부에 따른 반환값 검증
    - `buy_price` 키 존재 시 `get_buy_price(properties, None)` == `buy_price` 값
    - `buy_price` 키 미존재 시 `get_buy_price(properties, None)` == 0
    - `sell_price` 키 존재 시 `get_sell_price(properties, None)` == `sell_price` 값
    - `sell_price` 키 미존재 시 `get_sell_price(properties, None)` == 0
    - **Validates: Requirements 1.1, 1.2, 1.5, 2.1, 2.5**

  - [ ]* 1.4 Property 2 속성 기반 테스트: price_modifier 적용
    - **Property 2: price_modifier 적용**
    - hypothesis 라이브러리로 유효한 `item_properties`와 양의 실수 `price_modifier`를 랜덤 생성
    - `get_buy_price(properties, modifier)` == `max(1, round(base_price * modifier))` 검증
    - `get_sell_price(properties, modifier)` == `max(1, round(base_price * modifier))` 검증
    - 반환값이 항상 int 타입인지 검증
    - **Validates: Requirements 2.2, 2.3, 2.5**

  - [ ]* 1.5 Property 3 속성 기반 테스트: 최소값 1 보장
    - **Property 3: 최소값 1 보장**
    - hypothesis 라이브러리로 양수 `buy_price`/`sell_price`와 극단적으로 작은 `price_modifier` (0.001 등) 생성
    - `get_buy_price(properties, modifier)` >= 1 검증
    - `get_sell_price(properties, modifier)` >= 1 검증
    - **Validates: Requirements 2.4**

- [ ] 2. Checkpoint - PriceResolver 검증
  - mypy + ruff 통과 확인
  - 모든 테스트 통과 확인, 문제 발생 시 사용자에게 질문

- [ ] 3. LuaScriptLoader 확장
  - [ ] 3.1 exchange API에 가격 조회 함수 3개 추가
    - `_register_exchange_globals()` 메서드에 `exchange.get_buy_price(item_id)` 함수 추가
    - `_register_exchange_globals()` 메서드에 `exchange.get_sell_price(item_id)` 함수 추가
    - `_register_exchange_globals()` 메서드에 `exchange.get_item_properties(item_id)` 함수 추가
    - PriceResolver 인스턴스를 LuaScriptLoader에 주입하여 가격 산출 위임
    - 에러 처리: `item_id` 타입 검증, 아이템 미존재 시 0 반환 (가격) / `_make_error` 반환 (속성)
    - Lua 글로벌 exchange 테이블에 3개 함수 등록
    - mypy + ruff 통과 확인
    - _Requirements: 3.1, 3.2, 3.6, 4.4_

  - [ ] 3.2 기존 인벤토리 조회 함수에 가격 필드 추가
    - `get_npc_inventory` 반환 항목에 `buy_price` 필드 추가 (PriceResolver 산출)
    - `get_player_inventory` 반환 항목에 `sell_price` 필드 추가 (PriceResolver 산출)
    - 기존 반환 구조 유지하면서 필드만 추가 (하위 호환성)
    - mypy + ruff 통과 확인
    - _Requirements: 5.1, 5.2, 5.3, 4.3, 4.4_

  - [ ]* 3.3 LuaScriptLoader 확장 단위 테스트 작성
    - `tests/unit/test_exchange_api.py`에 테스트 추가
    - `exchange.get_buy_price(item_id)` 호출 시 올바른 가격 반환 테스트
    - `exchange.get_sell_price(item_id)` 호출 시 올바른 가격 반환 테스트
    - `exchange.get_item_properties(item_id)` 호출 시 Lua 테이블 반환 테스트
    - 잘못된 `item_id` 타입 시 에러 반환 테스트
    - 존재하지 않는 아이템 조회 시 0 반환 테스트
    - `get_npc_inventory` 반환에 `buy_price` 필드 포함 테스트
    - `get_player_inventory` 반환에 `sell_price` 필드 포함 테스트
    - 기존 테스트가 수정 없이 통과하는지 확인 (하위 호환성)
    - _Requirements: 3.1, 3.2, 3.6, 4.1, 4.2, 4.3, 4.4, 5.1, 5.2, 5.3_

- [ ] 4. Checkpoint - LuaScriptLoader 확장 검증
  - mypy + ruff 통과 확인
  - 모든 테스트 통과 확인, 문제 발생 시 사용자에게 질문

- [ ] 5. 아이템 템플릿 JSON 업데이트
  - [ ] 5.1 기존 아이템 템플릿에 buy_price/sell_price 필드 추가
    - `configs/items/` 디렉토리의 거래 가능 아이템 JSON에 `buy_price`, `sell_price` 필드 추가
    - 기존 `base_value` 필드는 하위 호환성을 위해 유지
    - 거래 불가 아이템(quest item 등)은 `buy_price: 0`, `sell_price: 0` 설정
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [ ] 6. 최종 Checkpoint - 전체 시스템 검증
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
