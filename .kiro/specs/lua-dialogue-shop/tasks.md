# Implementation Plan: Lua 대화 기반 교환(Exchange) 시스템

## Overview

기존 Lua 대화 시스템을 확장하여 NPC와의 양방향 아이템 교환 시스템을 구현한다. CurrencyManager → ExchangeManager → Exchange API(Lua 등록) → DialogueContext 확장 → NPC 스폰 확장 → 샘플 스크립트 순서로 점진적으로 구현하며, 각 단계에서 기존 시스템과의 통합을 검증한다.

## Tasks

- [ ] 1. silver_coin 아이템 템플릿 및 CurrencyManager 구현
  - [ ] 1.1 silver_coin 아이템 템플릿 생성
    - `configs/items/silver_coin.json` 파일 생성
    - template_id='silver_coin', name_en='Silver Coin', name_ko='은화', weight=0.003, max_stack=9999, category='currency', base_value=1
    - _Requirements: 1.1_
  - [ ] 1.2 CurrencyManager 클래스 구현
    - `src/mud_engine/game/managers/currency_manager.py` 파일 생성
    - GameObjectRepository를 주입받아 silver_coin 스택 관리
    - get_balance(owner_id): silver_coin의 properties.quantity 합산 조회
    - earn(owner_id, amount): 기존 스택 수량 증가 또는 새 스택 생성, max_stack=9999 초과 시 추가 스택
    - spend(owner_id, amount): 수량 차감, 0이면 삭제, 잔액 부족 시 False
    - _find_silver_stacks(owner_id): silver_coin game_objects 목록 조회
    - _create_silver_stack(owner_id, quantity): 새 silver_coin 생성
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_
  - [ ]* 1.3 CurrencyManager 속성 테스트 작성
    - **Property 1: 실버 earn/spend 잔액 보존**
    - hypothesis 라이브러리 사용, 최소 100회 반복
    - earn 후 잔액 = 초기 + amount, spend 후 잔액 = 초기 - amount, 잔액 부족 시 False 및 잔액 불변 검증
    - **Validates: Requirements 1.3, 1.4, 1.5**

- [ ] 2. ExchangeManager 구현
  - [ ] 2.1 ExchangeManager 클래스 구현
    - `src/mud_engine/game/managers/exchange_manager.py` 파일 생성
    - ExchangeResult TypedDict 정의 (success, error, error_code)
    - CurrencyManager와 GameObjectRepository를 주입
    - buy_from_npc: 잔액 확인 → 무게 확인 → 실버 차감 → NPC 실버 증가 → 장착 해제 → 아이템 이동, 실패 시 보상 트랜잭션 롤백
    - sell_to_npc: NPC 잔액 확인 → 소유 확인 → 장착 해제 → NPC 실버 차감 → 플레이어 실버 증가 → 아이템 이동, 실패 시 롤백
    - _unequip_item: is_equipped=false 처리 (equipment_slot 유지)
    - _get_player_carry_weight, _get_player_weight_limit 구현
    - error_code: 'insufficient_silver', 'npc_insufficient_silver', 'weight_exceeded', 'item_not_found', 'item_not_owned'
    - _Requirements: 3.2, 3.3, 3.4, 3.5, 3.7, 5.1, 5.2_
  - [ ]* 2.2 buy_from_npc 속성 테스트 작성
    - **Property 2: buy_from_npc 원자성 및 잔액/인벤토리 정합성**
    - 성공 시 플레이어 잔액 감소, NPC 잔액 증가, 아이템 이동 검증
    - 실패 시 (잔액 부족, 무게 초과) 양쪽 상태 불변 검증
    - **Validates: Requirements 3.3, 5.2**
  - [ ]* 2.3 sell_to_npc 속성 테스트 작성
    - **Property 3: sell_to_npc 원자성 및 잔액/인벤토리 정합성**
    - 성공 시 NPC 잔액 감소, 플레이어 잔액 증가, 아이템 이동 검증
    - 실패 시 (NPC 잔액 부족) 양쪽 상태 불변 검증
    - 장착 아이템 판매 시 is_equipped=false 확인
    - **Validates: Requirements 3.4, 3.5, 5.1**

- [ ] 3. Checkpoint - 기반 컴포넌트 검증
  - mypy + ruff 정적 검사 통과 확인
  - CurrencyManager, ExchangeManager 단위 테스트 통과 확인
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Exchange API Lua 등록
  - [ ] 4.1 LuaScriptLoader에 Exchange API 등록 구현
    - `src/mud_engine/game/lua_script_loader.py` 확장
    - register_exchange_api(exchange_manager) 메서드 추가
    - _register_exchange_globals() 메서드 추가: Lua 글로벌에 exchange 테이블 등록
    - 비동기 함수를 동기적으로 호출하기 위한 래퍼 구현 (nest_asyncio 또는 별도 스레드 풀)
    - exchange.get_npc_inventory(npc_id), exchange.get_player_inventory(player_id)
    - exchange.get_npc_silver(npc_id), exchange.get_player_silver(player_id)
    - exchange.buy_from_npc(player_id, npc_id, game_object_id, price)
    - exchange.sell_to_npc(player_id, npc_id, game_object_id, price)
    - 인자 타입 검증, 예외 처리 후 {success=false, error=사유} 반환
    - _Requirements: 3.1, 3.2, 3.6, 3.7_
  - [ ]* 4.2 Exchange API 등록 단위 테스트 작성
    - Lua 글로벌에 exchange 테이블 등록 확인
    - 각 함수 호출 가능 여부 확인
    - 잘못된 인자 타입 시 실패 결과 반환 확인
    - _Requirements: 3.6, 3.7_

- [ ] 5. DialogueContext 확장
  - [ ] 5.1 DialogueContext에 교환 정보 추가
    - `src/mud_engine/game/dialogue_context.py` 확장
    - _build_player_context에 silver, carry_weight, weight_limit, inventory 필드 추가
    - _build_npc_context에 silver, inventory 필드 추가
    - 인벤토리 아이템: id, name, category, weight, is_equipped, equipment_slot, properties
    - silver_coin은 inventory 목록에서 제외, 별도 silver 필드로 제공
    - CurrencyManager와 GameObjectRepository 참조 필요 → build() 시그니처 확장 또는 별도 빌더 메서드
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_
  - [ ]* 5.2 DialogueContext 확장 속성 테스트 작성
    - **Property 4: DialogueContext 교환 수치 정보 완전성**
    - silver, carry_weight, weight_limit이 실제 값과 일치하는지 검증
    - **Validates: Requirements 6.1, 6.2, 6.4**
  - [ ]* 5.3 DialogueContext 인벤토리 목록 속성 테스트 작성
    - **Property 5: DialogueContext 인벤토리 목록 완전성**
    - 각 아이템의 필수 필드(id, name, category, weight, is_equipped, equipment_slot, properties) 존재 확인
    - silver_coin이 inventory 목록에 포함되지 않는지 검증
    - **Validates: Requirements 6.3, 6.5**

- [ ] 6. NPC 스폰 시 exchange_config 처리
  - [ ] 6.1 MonsterManager 확장
    - `src/mud_engine/game/managers/monster_manager.py` 확장
    - _create_monster_equipment()에서 exchange_config 처리 로직 추가
    - exchange_config.initial_silver > 0이면 CurrencyManager.earn()으로 silver_coin 생성
    - exchange_config 파싱 실패 시 로깅 후 무시 (NPC는 교환 기능 없이 스폰)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_
  - [ ]* 6.2 NPC 스폰 시 exchange_config 단위 테스트 작성
    - exchange_config가 있는 NPC 스폰 시 silver_coin 생성 확인
    - exchange_config가 없는 NPC 스폰 시 기존 동작 유지 확인
    - _Requirements: 2.2, 2.3, 2.4_

- [ ] 7. Checkpoint - 핵심 로직 검증
  - mypy + ruff 정적 검사 통과 확인
  - Exchange API, DialogueContext 확장, NPC 스폰 확장 테스트 통과 확인
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. 샘플 교환 NPC Lua 스크립트 작성
  - [ ] 8.1 샘플 교환 NPC Lua 스크립트 구현
    - `configs/dialogues/{merchant_npc_id}.lua` 파일 생성
    - get_dialogue(ctx): 인사말 + 구매/판매/나가기 선택지
    - on_choice: 구매 메뉴(show_buy_menu), 판매 메뉴(show_sell_menu) 분기
    - show_buy_menu: NPC 인벤토리 기반 동적 아이템 목록, 가격/무게 표시, exchange.buy_from_npc 호출
    - show_sell_menu: 플레이어 인벤토리 기반 동적 아이템 목록, 매입가(buy_margin 적용) 표시, exchange.sell_to_npc 호출
    - 거래 결과 메시지: 성공, 실버 부족, NPC 실버 부족, 무게 초과
    - 장착 아이템 표시 (is_equipped 상태 표시)
    - 거래 후 메인 메뉴 복귀
    - 모든 텍스트 다국어 dict 형식 {en = "...", ko = "..."}
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 5.3, 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ] 9. DialogueManager 및 GameEngine 통합 배선
  - [ ] 9.1 DialogueManager에 ExchangeManager 연결
    - DialogueManager 초기화 시 CurrencyManager, ExchangeManager 생성 및 LuaScriptLoader에 등록
    - GameEngine 또는 적절한 초기화 지점에서 의존성 주입 배선
    - DialogueContext.build() 호출 시 교환 정보 포함되도록 연결
    - _Requirements: 3.1, 3.2, 6.1, 6.4_

- [ ] 10. Telnet MCP E2E 테스트
  - [ ] 10.1 교환 NPC E2E 테스트 수행
    - 서버 실행 후 telnet-mcp 도구로 접속
    - 교환 NPC에게 talk 명령 → 인사말 및 선택지 확인
    - 구매 흐름: 구매 선택 → 아이템 목록 확인 → 아이템 구매 → 결과 메시지 확인
    - 판매 흐름: 판매 선택 → 아이템 목록 확인 → 아이템 판매 → 결과 메시지 확인
    - 실패 시나리오: 실버 부족, NPC 실버 부족, 무게 초과
    - 거래 후 메인 메뉴 복귀 확인
    - 다국어 메시지 확인 (en/ko)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 7.2, 7.3, 7.4_

- [ ] 11. 레거시 명령어 deprecated 처리
  - [ ] 11.1 shop_command.py, trade_command.py deprecated 표시
    - 각 파일 상단에 deprecated 주석 및 warnings.warn() 추가
    - exchange_config 마이그레이션 가이드 주석 작성
    - _Requirements: 8.1, 8.2, 8.3_

- [ ] 12. Final checkpoint
  - mypy + ruff 정적 검사 최종 통과 확인
  - 전체 테스트 스위트 통과 확인
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- 각 태스크는 특정 요구사항을 참조하여 추적 가능
- Checkpoint에서 정적 검사(mypy + ruff) 통과 필수
- Property 테스트는 hypothesis 라이브러리 사용, 최소 100회 반복
- Exchange API의 비동기→동기 래퍼는 nest_asyncio 또는 별도 스레드 풀로 구현
- silver_coin은 인벤토리 목록에서 제외하고 별도 silver 필드로 제공
- 장착 아이템 거래 시 is_equipped=false 후 location 변경
- 보상 트랜잭션 패턴으로 롤백 처리
- 다국어 dict {en = "...", ko = "..."} 형식 준수
