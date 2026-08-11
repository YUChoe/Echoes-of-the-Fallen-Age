# 스펙 간 정합성 매핑

프로토콜 계약에 정의된 모든 메시지와 verb가 세 스펙에 반영되었는지 점검한 결과다. 계약이 변경되면 이 표를 갱신한다.

관련 스펙:

- 서버: `Echoes-of-the-Fallen-Age/.kiro/specs/server-json-protocol/`
- 게이트웨이와 랜딩: `KarnasChronicles-DividedDominio-client/.kiro/specs/gateway-landing/`
- Godot 클라이언트: `KarnasChronicles-DividedDominio-client/.kiro/specs/godot-client/`

## 클라이언트 → 서버 메시지

| 메시지 | 서버 처리 | 클라이언트 송신 |
|---|---|---|
| `login` | Task 3.5 | Task 3 |
| `logout` | Task 3.5 | Task 3 |
| `action` | Task 4.2 | Task 1.5 |
| `chat` | Task 4.5 | Task 5.7 |
| `ping` | Task 3.4 | Task 1.3 |
| `client_info` | Task 3.4 | Task 1.9 |

## 서버 → 클라이언트 메시지

| 메시지 | 서버 송신 | 클라이언트 처리 |
|---|---|---|
| `welcome` | Task 3.5 | Task 1.2, 1.6 |
| `login_result` | Task 3.5 | Task 3 |
| `logout_result` | Task 3.5 | Task 3 |
| `pong` | Task 3.4 | Task 1.3 |
| `room_info` | Task 2.3, 3.1 | Task 5.1, 5.3 |
| `entity_enter` | Task 2.1 | Task 5.6 |
| `entity_leave` | Task 2.1 | Task 5.6 |
| `entity_update` | Task 2.1 | Task 5.6 |
| `player_state` | Task 2.3 | Task 5.1, 10 |
| `inventory` | Task 2.3 | Task 7.1 |
| `container_contents` | Task 2.3 | Task 7.4 |
| `combat_state` | Task 2.3 | Task 8 |
| `dialogue` | Task 4.4 | Task 9.1 |
| `shop` | Task 4.4 | Task 9.2 |
| `who_result` | Task 4.4 | Task 5.8 |
| `chat` | Task 4.5 | Task 5.7 |
| `event` | Task 6.1, 6.2 | Task 5.9 |
| `action_rejected` | Task 4.2, 6.1 | Task 4.2 |
| `error` | Task 3.4 | Task 1.4 |

## verb 매핑

| verb | 서버 핸들러 | 클라이언트 버튼 |
|---|---|---|
| `move` | actions/movement.py | Task 5.2 출구 버튼 |
| `enter` | actions/movement.py | Task 5.2 진입 버튼 |
| `look` | actions/movement.py | Task 5.6 재동기화 |
| `examine` | actions/inspection.py | Task 6 대상 동사 |
| `get` | actions/items.py | Task 6 대상 동사 |
| `drop` | actions/items.py | Task 7.3 |
| `use` | actions/items.py | Task 7.1 |
| `equip` | actions/items.py | Task 7.2 |
| `unequip` | actions/items.py | Task 7.2 |
| `unequip_all` | actions/items.py | Task 7.2 |
| `give` | actions/items.py | Task 6 대상 동사 |
| `read` | actions/items.py | Task 6 대상 동사 |
| `open` | actions/containers.py | Task 7.4 |
| `put` | actions/containers.py | Task 7.4 |
| `take_from` | actions/containers.py | Task 7.4 |
| `attack` | actions/combat.py | Task 8 |
| `flee` | actions/combat.py | Task 8 |
| `use_item` | actions/combat.py | Task 8 |
| `end_turn` | actions/combat.py | Task 8 |
| `talk` | actions/dialogue.py | Task 6 대상 동사 |
| `dialogue_choice` | actions/dialogue.py | Task 9.1 |
| `dialogue_end` | actions/dialogue.py | Task 9.1 |
| `shop_open` | actions/shop.py | Task 6 대상 동사 |
| `shop_buy` | actions/shop.py | Task 9.2 |
| `shop_sell` | actions/shop.py | Task 9.2 |
| `follow` | actions/social.py | Task 6 대상 동사 |
| `unfollow` | actions/social.py | Task 5.10 |
| `emote` | actions/social.py | Task 5.10 |
| `who` | actions/social.py | Task 5.8 |
| `players_here` | actions/social.py | Task 5.8 |
| `request_state` | actions/state.py | Task 1.7 |
| `request_inventory` | actions/state.py | Task 7.1 |
| `request_combat_state` | actions/state.py | Task 8 |
| `changename` | actions/account.py | Task 10 |

서버측 파일 배치는 `server-json-protocol` design.md의 `commands/actions/` 구조를 따르며 Task 4.4에서 구현한다.

## 거절 코드 매핑

| 코드 | 서버 발생 | 클라이언트 처리 |
|---|---|---|
| `NOT_AUTHENTICATED` | Task 4.2 디스패처 1단계 | Task 4.2 로그인 전환 |
| `NOT_FOUND` | Task 5.1 target 해석 | Task 4.2 `look` 재동기화 |
| `NOT_APPLICABLE` | Task 6(액션 검증) | Task 4.2 버튼 제거 |
| `PERMISSION_DENIED` | Task 7.1 어드민 인증 | Task 4.2, 11.1 안내 |
| `WRONG_STATE` | Task 4.2 상태 게이팅 | Task 4.2 안내 |
| `NOT_YOUR_TURN` | actions/combat.py | Task 8 턴 대기 표시 |
| `OUT_OF_RANGE` | 각 액션 핸들러 | Task 4.2 안내 |
| `INSUFFICIENT_FUNDS` | actions/shop.py | Task 9.2 부족액 표시 |
| `INSUFFICIENT_QUANTITY` | actions/items.py | Task 4.2 상한 조정 |
| `INVENTORY_FULL` | actions/items.py | Task 4.2 안내 |
| `SLOT_OCCUPIED` | actions/items.py | Task 4.2 교체 확인 |
| `COOLDOWN` | actions/account.py | Task 10 잔여 시간 |
| `TARGET_REQUIRED` | Task 4.2 디스패처 | Task 4.2 로그 기록 |
| `INVALID_PARAMS` | Task 4.2 디스패처 | Task 4.2 로그 기록 |
| `INTERNAL_ERROR` | 전역 예외 처리 | Task 4.2 재시도 안내 |

어드민 전용 코드는 `admin.md`에 정의되며 클라이언트 Task 11.1이 처리한다. 어드민 채널의 거절에는 번역 키가 없고 `detail`에 영문 설명이 온다.

## 어드민 메시지 매핑

| 메시지 | 서버 | 클라이언트 |
|---|---|---|
| `admin_login` / `admin_login_result` | Task 7.1 | Task 11.1 |
| `service_login` | Task 7.1 | 게이트웨이 Task 5.3 |
| `account_create` | Task 8 | 게이트웨이 Task 5.4 |
| `admin_list` / `admin_get` | Task 7.2 | Task 11.3 |
| `admin_create` / `admin_update` / `admin_delete` | Task 7.2, 7.3 | Task 11.4 |
| `admin_stats` | Task 7.4 | Task 11.5 |
| `admin_map` | Task 7.5 | Task 11.2 |
| `admin_action` | Task 7.4 | Task 11.5 |
| `admin_rejected` | Task 7 전체 | Task 11.1 |

## 전송 계층 매핑

| 항목 | 서버 | 게이트웨이 | 클라이언트 |
|---|---|---|---|
| JSON 라인 프레이밍 | Task 3.1, 3.4 | Task 2.1~2.4 | Task 1.2 |
| Telnet IAC 협상 | 유지 (Req 10.7) | Task 2.3 필터 유지 | 해당 없음 |
| 게임 채널 | TCP 4000 | `/ws` → 4000 | `ws://host/ws` |
| 어드민 채널 | TCP 4001 (Task 7.1) | `/admin` → 4001 (Task 3.2) | `ws://host/admin` (Task 11.1) |
| 계정 생성 | TCP 4001 (Task 8) | `POST /api/register` (Task 5.4) | 해당 없음 (랜딩) |
| ANSI 제거 | Task 3.2 | sanitizer 제거 (Task 3.3) | 해당 없음 |

## 저장소 간 의존 그래프

```mermaid
flowchart TD
    P[프로토콜 계약<br/>docs/protocol/] --> S[서버 스펙]
    P --> G[게이트웨이·랜딩 스펙]
    P --> C[Godot 스펙]

    S3[서버 3. JSON 송신] <-->|동시 배포| G2[게이트웨이 2. 라인 프레이밍]
    S65[서버 6.5 번역 이관] --> C2[Godot 2. 다국어]
    S7[서버 7. 어드민 채널] --> G32[게이트웨이 3.2 어드민 프록시]
    S7 --> G4[게이트웨이 4. 웹어드민 제거]
    G32 --> C11[Godot 11. 어드민 패널]
    S7 --> C11
    S8[서버 8. 계정 생성] --> G5[게이트웨이 5. 랜딩]
    G2 --> C1[Godot 1. 연결 계층]
```

## 착수 순서

```
1단계  프로토콜 계약 확정 (완료)
       └ docs/protocol/ 5개 문서

2단계  병렬 착수
       ├ 서버:      Task 0 → 1(하니스) → 2(직렬화)
       ├ 게이트웨이: Task 1(터미널 제거) → 2.1~2.2(LineFramer 단위 구현)
       └ Godot:     Task 1(기반과 연결)

3단계  프로토콜 교체 (동시 배포 필요)
       ├ 서버:      Task 3(JSON 송신) → 4(디스패처) → 5(uuid)
       └ 게이트웨이: Task 2.3~2.5(프레이밍 통합)

4단계  번역 이관
       ├ 서버:      Task 6
       └ Godot:     Task 2

5단계  게임 화면
       └ Godot:     Task 3~10

6단계  어드민 이전
       ├ 서버:      Task 7
       ├ 게이트웨이: Task 3.2 → 4(웹어드민 제거)
       └ Godot:     Task 11

7단계  계정 생성과 랜딩
       ├ 서버:      Task 8
       └ 게이트웨이: Task 5

8단계  정리와 검증
       ├ 서버:      Task 9
       ├ 게이트웨이: Task 6~7
       └ Godot:     Task 12
```

3단계가 가장 위험하다. 서버와 게이트웨이를 동시에 배포해야 하며 어긋나면 통신이 성립하지 않는다. 서버는 하니스로, 게이트웨이는 `LineFramer` 단위 테스트로 각각 독립 검증한 뒤 통합한다.

6단계에서 Node 웹어드민과 서버 어드민이 공존하는 기간이 발생한다. 같은 데이터베이스를 조작하면 서버 캐시와 불일치가 생기므로 이 기간을 최소화한다.

## 점검에서 발견해 보완한 항목

계약과 스펙을 대조하며 클라이언트 스펙에 누락된 항목을 찾아 보완했다.

| 누락 항목 | 보완 |
|---|---|
| `client_info` 송신 | Godot Requirement 1.12, Task 1.9 추가 |
| `chat` 송수신 UI | Godot Requirement 5.12~5.14, Task 5.7 추가 |
| `who` / `players_here` verb와 `who_result` | Godot Requirement 5.15, Task 5.8 추가 |
| `event` 로그 표시 | Godot Requirement 5.16, Task 5.9 추가 |
| `unfollow`, `emote` verb | Godot Requirement 5.17, Task 5.10 추가 |
| `unequip_all` verb | Godot 인벤토리 화면 버튼(Task 7.2)으로 반영. 대상이 없는 액션이므로 규칙 테이블 대상이 아니다 |

## 점검에서 정정한 계약 오류

코드를 확인해 계약의 사실 오류를 정정했다.

| 오류 | 확인 내용 | 정정 |
|---|---|---|
| `enter`의 `target`을 uuid로 정의 | `commands/Basic/enter.py`는 현재 방 좌표로 `room_connections`를 조회해 이동한다. 대상 엔티티가 없다 | `enter`를 target 없는 verb로 변경. `room_info`에 `has_passage` 필드를 추가해 클라이언트가 진입 버튼 표시 여부를 판단하게 함 |
| `close` verb 정의 | `commands/container_commands.py`에는 `OpenCommand`와 `PutCommand`만 있다. 열림 상태를 추적하는 필드가 없어 `open`은 내용 조회 동작이다 | `close` verb 제거 |
| monster와 combatant에 `level` 정의 | level은 코드에서 의도적으로 제거된 개념이다. `MonsterStats.from_dict`이 `pop('level')`, `PlayerStats.from_dict`이 `pop("level")`, `Player.from_dict`의 deprecated 목록에 `stat_level`. DB 컬럼도 없다 | `level` 제거. 대신 능력치에서 계산되는 `armor_class`, `attack_power`를 제공 |
| monster에 `is_merchant` 정의 | `Monster.is_merchant()`는 없다. 유일한 판정식은 deprecated·미등록 `shop_command.py`에 있고, `ExchangeManager.buy_from_npc`는 상인 여부를 검사하지 않는다 | `is_merchant` 제거. 모든 캐릭터와 거래 가능하므로 구분이 불필요하다 |
| object의 `category` 출처 | DB에 `category` 컬럼이 있으나 `GameObject.from_dict`이 명시적으로 버리고 실제로는 `properties['category']`를 쓴다 | 출처를 `properties.category`로 명시 |
| `can_talk` 판정 근거 | `talk_command.py`는 `type == 'monster'`만 확인하고 스크립트 존재를 보지 않는다. 조회용 API가 없다 | `LuaScriptLoader`에 스크립트 존재 확인 메서드를 추가해 산출한다. 거짓이어도 서버는 침묵 응답을 주므로 버튼 우선순위 판단용으로 정의 |
| `max_stack` 제공과 스택 그룹 전제 | DB에 값이 있으나 서버가 그에 따라 동작하지 않는다. 스택 병합은 `CurrencyManager`에만 있고 `_group_stackable_objects`는 `return []`로 무력화됐다. 프로덕션 데이터에서 `properties.quantity`를 가진 25건은 전부 화폐이며 모두 `max_stack=9999`, `max_stack>1`인 나머지 22건은 `quantity`가 없다. 두 필드가 함께 쓰이는 사례가 없다 | `max_stack` 제거. `stack_count`는 `properties.quantity`에서 산출하며 화폐만 1을 초과한다. 같은 종류 아이템은 개별 엔티티로 송신하고 묶음 표시는 클라이언트 책임으로 정의 |

## 미해결 사항

다음은 구현 단계에서 결정해야 한다.

| 항목 | 결정 시점 |
|---|---|
| 감사 로그를 DB 테이블로 저장할지 | 서버 Task 7.7 |
| `resize` 메시지 타입 존속 여부 | 게이트웨이 Task 3.4 |
| `sanitizer.ts` 제거 또는 연결 | 게이트웨이 Task 3.3 |
| 랜딩 정적 서빙 주체(게이트웨이 vs nginx) | 게이트웨이 Task 5.2 |
| 랜딩 한국어 병기 여부 | 게이트웨이 Task 5.1 |
| GDScript 테스트 프레임워크 선택 | Godot Task 12.3 |
| 대상 선택 UI 방식(팝오버 vs 고정 패널) | Godot Task 6 |
| faction_relations 기반 동적 disposition 판정 | 범위 외. 우호도 기능 개발 시. 현재는 하드코딩 규칙 보존 |
| 일반 아이템 스택 병합 구현 | 범위 외. 아이템 시스템 전반(get/drop/put/give, 무게 계산)에 영향이 크다. 페이즈2 이후 별도 작업 |
| max_stack 데이터 정리 | 범위 외. 부피 있는 물건에 스택이 붙어 있다(건초 더미 5kg=3, 밧줄 1.5kg=5, 횃불 0.5kg=10, 빈 병 5, 말굽 5). 체력 물약은 5와 20으로 불일치하고 무게도 0.30/0.60으로 갈린다. 어드민 기능 준비 후 정리 |
| category 분류 정리 | 범위 외. 101건 중 97건이 `misc`이며 `consumable` 1건, `currency` 2건, `readable` 1건뿐이다. 클라이언트 카테고리 필터가 실질적으로 동작하려면 분류가 필요하다 |
| room_connections 조회를 매니저로 이전 | 차후 개발. 현재 `commands/Basic/enter.py::_get_room_connection()`이 매니저를 거치지 않고 `SELECT to_x, to_y FROM room_connections`를 직접 실행한다. `has_passage` 산출에도 같은 조회가 필요해 중복이 생긴다. `RoomManager`에 조회 메서드를 만들어 양쪽이 공유하는 것이 구조상 맞으며, 명령어를 액션 핸들러로 옮기는 Task 4 시점에 함께 정리한다. 그때까지는 호출부가 조회해 직렬화 계층에 인자로 전달한다 |
| 계약 밖 메시지 타입 정리 | 서버 Task 4·6. JSON 송신 전환(Task 3) 이후에도 계약에 없는 `type` 24종이 남아 있다: `system_message`(11), `room_message`(8), `combat_message`(4), `object_update`, `info`, `success`, `whisper_received`, `room_updated`, `room_players_update`, `room_chat_message`, `private_message`, `object_created`, `moving message`, `movement`, `kicked`, `item_received`, `inventory_update`, `follow_stopped`, `combat_rejoin`, `chat_message`, `broadcast_message`, `being_followed`, `admin_action`. 계약의 "알 수 없는 type은 무시" 규칙에 의해 클라이언트가 버리므로 통신은 깨지지 않으나 해당 알림이 전달되지 않는다. 액션 응답은 Task 4, 알림은 Task 6에서 `event`·`entity_update`로 흡수한다 |
| `event` 과도기 필드 제거 | 서버 Task 6.7 완료. `TelnetSession.send_event()`는 `key`/`params`/`category`/`seq`를 받아 `build_event()`에 위임한다. 계약 밖 필드 `text`·`severity`는 게임 채널에서 사라졌다. `send_error`·`send_success`·`send_info`는 삭제했다. 남은 사용처는 어드민 전용 `send_admin_notice()` 하나이며 `category: "admin"`으로 나가고 Task 7.6에서 어드민 채널로 옮기며 사라진다 |
| Lua 아이템 콜백 문장 미전달 | 서버 Task 10. Task 6.7에서 `result.message` 직송을 제거했다. `actions/items.py`의 `use`/`consume` 가 Lua 콜백의 완성 문장을 `ActionResult.message`로 실어 오는데, 이 필드는 개발자용 사유로 재정의됐으므로 서버 로그에만 남는다. 아이템 사용 결과 문장은 대사 번역 키 전환(Task 10)까지 클라이언트에 표시되지 않는다 |
| `gold` 필드와 화폐 구현 불일치 | 범위 외. 경제 규칙 변경을 수반한다. `player_state.gold`와 `inventory.gold`는 `CurrencyManager.get_balance()`가 채우는데, 이 매니저는 `properties.template_id == "silver_coin"`인 스택만 집계한다(`currency_manager.py:19,37`). 테스트 계정 player5426은 Gold Coin 2개를 보유하지만 `template_id`가 달라 잔액이 0으로 보고된다. 계약 필드명은 `gold`인데 구현된 화폐는 실버뿐이므로, 필드명을 화폐 종류에 맞게 정정하거나 화폐를 다종으로 확장해야 한다. 어느 쪽이든 상점·교환 로직에 영향이 있어 화폐 설계를 정리할 때 함께 처리한다 |
| `combat_state.is_over` 기준 | 기존 동작 유지로 결정. `build_combat_state`는 `not combat.is_active`를 보내며, 이는 `combat.is_combat_over()`(한쪽 전멸 판정)와 다른 개념이다. 한쪽이 전멸했으나 `end_combat()`이 아직 호출되지 않은 짧은 구간에서는 `is_over: false`가 나간다. 클라이언트는 전투 종료를 `is_over` 대신 `combat_state` 수신 중단과 `room_info` 재수신으로도 판별할 수 있으므로 현재 동작을 바꾸지 않는다. 전투 종료 처리를 정리할 때 재검토한다 |
| 대화 대사의 번역 키 전환 | 서버 Task 10(신규). 계약은 `dialogue.lines[]`와 `choices[].text`가 `{key, params}`를 담도록 규정하지만, 대사 원본이 `configs/dialogues/*.lua` 19개 스크립트의 언어별 완성 문장이라 키가 존재하지 않는다. 결정: 키 방식으로 전환한다. 다만 Lua 스크립트 대사를 키로 바꾸고 클라이언트 번역 파일로 옮기는 작업이 커서 별도 태스크로 분리했다. 그때까지 `lines[]`와 `choices[].text`는 언어별 dict를 그대로 싣는다 |
| 상점 verb 미구현 | 범위 외. `shop_open`/`shop_buy`/`shop_sell`을 등록하지 않는다. 계약이 요구하는 `item_prices` 기반 상점이 서버에 없다. `shop_command.py`는 폐기 표시가 붙어 있고 등록되지 않으며 `item_prices`가 아니라 몬스터 properties의 `shop_items`를 쓴다. 살아 있는 거래 경로는 대화 안의 Lua exchange API뿐이므로 기능 손실이 없다. 계약을 만족시키려면 세 가지가 필요하다: `shop_buy`의 `template_id`를 NPC 인벤토리 실물 uuid로 해석하는 계층(현재 Lua 래퍼에만 존재), `ExchangeManager`의 수량 처리(현재 없음), `stock` 의미 재정의(`exchange_config`에 판매 목록이 없고 `initial_silver`와 `buy_margin`만 있어 실제 재고는 NPC 인벤토리 실물 개수다). 데이터 스키마 변경을 수반하므로 페이즈2 이후 별도 작업 |
| `monsters.faction_id` 끊어진 참조 | 데이터 정리. `townspeople` 을 가리키는 몬스터가 1건 있으나 `factions` 에 그 행이 없다(현재 `ash_knights`, `goblins`, `animals` 3개). `monsters.faction_id` 에는 외래키가 선언돼 있지 않아 DB 가 막지 못했다. 어드민 채널의 참조 검사(Task 7.3)는 이 값을 참조로 세지만 기존 행을 고치지는 않는다. `townspeople` 종족을 만들거나 해당 몬스터의 종족을 바꿔야 한다 |
| `game_objects.location_type` 대소문자 혼재 | 데이터 정리. `room` 45건과 `ROOM` 10건, `container` 1건과 `CONTAINER` 5건이 함께 있다. 어드민 참조 검사와 재동기화는 대소문자를 무시해 비교하므로 동작에 문제는 없으나, 필터로 조회하는 클라이언트가 한쪽만 얻게 된다. 한쪽으로 통일해야 한다 |
| `rooms` 좌표 중복 | 데이터 정리. 좌표 (-20,-1) 에 방이 2개 있다. `room_connections` 와 `monsters` 가 방을 좌표로 가리키므로 어느 방을 뜻하는지 결정되지 않는다. 어드민 삭제의 참조 검사는 좌표가 유일할 때만 참조로 세는 방식으로 우회했다 |
| `town_merchant.json` 중복 키 | 데이터 정리. `configs/monsters/town_merchant.json`에 `exchange_config` 키가 두 번 있다. JSON 중복 키라 뒤의 것이 이기고 값이 같아 동작에는 영향이 없다 |
| 어드민 명령어 재작성 | 서버 Task 7. Task 4.6에서 `commands/admin/` 15개 파일을 삭제했다. 텍스트 프로토콜과 번호 기반 대상 지정에 묶여 있어 어드민 채널에서 재사용할 수 없었고, 삭제 시점에 이미 도달 불가 상태였다. `core/managers/admin_manager.py`는 남겼으며 어드민 채널이 그것을 호출한다. 그때까지 `admin_manager`의 메서드는 호출자가 없다. 필요하면 커밋 91790e3에서 삭제된 파일을 참고할 수 있다 |
| NPC 침묵 폴백 문구 | 서버 Task 10. Lua 스크립트가 없는 NPC 와 대화하면 `lines` 에 `"..."` 가 담긴다. 기존에는 `npc.talk.silent_stare` 키로 "아무 말 없이 바라봅니다"를 렌더링했으나, 대화 대사가 언어별 dict 인 과도기에는 키를 실을 자리가 없다. 대화 대사가 키 방식으로 전환되면 이 센티널을 해당 키로 바꾼다 |
| 이관된 번역 파일의 사용처 없는 키 | Godot Task 5.2. 서버에서 이관한 9개 파일에는 명령어 도움말, 어드민 명령어 안내처럼 페이즈2 에서 사라진 기능의 키가 남아 있다. 클라이언트가 i18n 계층을 만들 때 실제 사용 키만 남기고 정리한다 |
| `SessionState.last_command` 제거 | 서버 Task 9. 텍스트 프로토콜의 `.` 반복 입력에 쓰였고 참조하는 코드가 사라졌다. 필드만 남아 있으며 잔여 정리 단계에서 제거한다 |
| 전투 알림의 번역 키 전환 | 서버 Task 6. `combat_handler`의 공격·명중·사망·시체 생성 알림이 아직 완성 문장을 `combat_message` 타입으로 보낸다. 전투 상태표와 턴 안내, 행동 메뉴는 Task 5에서 `combat_state` 브로드캐스트로 대체해 제거했다 |
| 역할 기반 어드민 권한 | 범위 외. 향후 확장 |
| 한국어 조사 자동 선택 | 범위 외. 향후 개선 |
| Telnet IAC 협상 제거 | 범위 외. 향후 후보 |
