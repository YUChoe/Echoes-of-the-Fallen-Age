# 서버 → 클라이언트 메시지

서버는 상태 스냅샷과 이벤트를 구분해서 보낸다. 스냅샷(`room_info`, `player_state`, `inventory`, `combat_state`)은 해당 영역의 전체 상태를 담고, 이벤트(`event`, `entity_enter`, `entity_leave`)는 변화만 알린다. 클라이언트는 스냅샷으로 화면을 재구성하고 이벤트로 부분 갱신한다.

| type | seq | 설명 |
|---|---|---|
| `welcome` | 없음 | 접속 직후 서버 정보 |
| `login_result` | 있음 | 인증 결과 |
| `logout_result` | 있음 | 인증 해제 결과 |
| `pong` | 있음 | ping 응답 |
| `room_info` | 조건부 | 방 전체 상태 |
| `entity_enter` | 없음 | 엔티티 입장 |
| `entity_leave` | 없음 | 엔티티 퇴장 |
| `entity_update` | 없음 | 엔티티 속성 변화 |
| `player_state` | 조건부 | 플레이어 상태 |
| `inventory` | 조건부 | 인벤토리 전체 |
| `container_contents` | 있음 | 컨테이너 내용 |
| `combat_state` | 조건부 | 전투 전체 상태 |
| `dialogue` | 조건부 | 대화 상태 |
| `shop` | 있음 | 상점 목록 |
| `who_result` | 있음 | 접속자 목록 |
| `chat` | 없음 | 채팅 수신 |
| `event` | 없음 | 번역 키 기반 알림 |
| `action_rejected` | 있음 | 액션 거절 |
| `error` | 조건부 | 프로토콜 오류 |

`seq`가 조건부인 메시지는 클라이언트 요청에 대한 응답이면 요청의 `seq`를, 서버가 자발적으로 보내면 `seq`를 생략한다.

## welcome

```json
{
  "type": "welcome",
  "protocol_version": 1,
  "server_version": "development@dev",
  "supported_locales": ["en", "ko"],
  "title": {
    "en": "The Chronicles of Karnas: Divided Dominion",
    "ko": "카르나스 연대기: 분할된 지배권"
  }
}
```

`supported_locales`는 DB의 이중언어 컬럼이 제공하는 언어를 알린다. 클라이언트의 UI 번역 범위와는 별개다. 클라이언트가 서버보다 많은 언어를 지원하면 엔티티 이름은 폴백 언어로 표시된다.

## login_result

성공:

```json
{
  "type": "login_result",
  "seq": 1,
  "success": true,
  "player": {
    "id": "cf65f7f3-...",
    "username": "player5426",
    "display_name": "SUPERADMIN",
    "is_admin": true,
    "faction_id": "ash_knights"
  }
}
```

실패:

```json
{
  "type": "login_result",
  "seq": 1,
  "success": false,
  "reason_code": "INVALID_CREDENTIALS",
  "message": { "key": "auth.login_failed", "params": {} }
}
```

실패 사유 코드는 `INVALID_CREDENTIALS`, `ALREADY_LOGGED_IN`, `ACCOUNT_LOCKED`뿐이다. 사용자명 존재 여부를 구분해서 알려주지 않는다. 계정 열거 공격을 막기 위한 조치다.

`is_admin`이 true여도 게임 세션에서 어드민 기능을 쓸 수 없다. 어드민은 별도 채널에서 별도 인증을 거친다. 이 플래그는 클라이언트가 어드민 패널 진입 버튼을 노출할지 결정하는 데만 쓰인다.

## logout_result

```json
{
  "type": "logout_result",
  "seq": 42,
  "success": true
}
```

## pong

```json
{
  "type": "pong",
  "seq": 45,
  "server_time": "2026-08-08T16:45:11.652000"
}
```

## room_info

```json
{
  "type": "room_info",
  "seq": null,
  "room": {
    "id": "0a1b2c3d-...",
    "x": 0,
    "y": 7,
    "room_type": "gate",
    "description": {
      "en": "A wide plaza before the gate, never empty of footfall.",
      "ko": "성문 앞 넓은 광장에 사람들의 발길이 끊이지 않는다."
    },
    "exits": ["north", "east", "south"],
    "blocked_exits": ["west"],
    "has_passage": true
  },
  "time_of_day": "day",
  "entities": [],
  "nearby_rooms": [
    { "x": -2, "y": 9, "room_type": "forest" },
    { "x": -1, "y": 9, "room_type": "forest" }
  ]
}
```

| 필드 | 설명 |
|---|---|
| `room.id` | 방 uuid |
| `room.x` `room.y` | 좌표. 이동과 미니맵 렌더링 기준 |
| `room.room_type` | 지형 분류. 22종. 클라이언트가 아이콘과 색상을 매핑 |
| `room.description` | 언어별 dict. `rooms` 테이블에 방 이름 컬럼이 없으므로 이름은 제공되지 않는다 |
| `room.exits` | 이동 가능한 방향 배열 |
| `room.blocked_exits` | 막힌 방향 배열. 클라이언트가 출구 버튼을 비활성 상태로 표시 |
| `room.has_passage` | 이 좌표에 `room_connections` 항목이 있는지. 참이면 클라이언트가 진입 버튼을 표시하고 `enter` verb를 보낼 수 있다 |
| `time_of_day` | `day` 또는 `night` |
| `entities` | 방 안의 모든 엔티티. 스키마는 entities.md 참조 |
| `nearby_rooms` | 반경 2칸 이내 방의 좌표와 지형. 미니맵 렌더링용 |

방 이름이 없는 것은 현재 DB 구조를 반영한 것이다. `rooms` 테이블은 `description_en`, `description_ko`만 갖는다. 클라이언트는 좌표와 지형으로 위치를 표시한다.

`nearby_rooms`는 서버가 텍스트 미니맵을 조립하던 로직을 대체한다. 좌표와 지형만 보내고 렌더링은 클라이언트가 담당한다. 현재 위치는 `room.x`, `room.y`와 비교해 클라이언트가 판별한다.

## entity_enter / entity_leave / entity_update

```json
{
  "type": "entity_enter",
  "room_id": "0a1b2c3d-...",
  "entity": {}
}
```

```json
{
  "type": "entity_leave",
  "room_id": "0a1b2c3d-...",
  "entity_id": "49a55ff4-...",
  "direction": "west"
}
```

```json
{
  "type": "entity_update",
  "entity_id": "49a55ff4-...",
  "changes": { "hp": 18 }
}
```

`entity_update`의 `changes`는 변경된 필드만 담는다. 클라이언트는 보유한 엔티티 사본에 병합한다. 병합 대상이 없으면 무시하고 `look` verb로 전체 상태를 재요청한다.

`entity_leave`의 `direction`은 이동 방향이며, 사라진 이유가 이동이 아니면(사망, 소멸) `null`이다.

## player_state

```json
{
  "type": "player_state",
  "seq": null,
  "player": {
    "id": "cf65f7f3-...",
    "username": "player5426",
    "display_name": "SUPERADMIN",
    "faction_id": "ash_knights",
    "room_id": "0a1b2c3d-...",
    "x": 0,
    "y": 7,
    "hp": 42,
    "max_hp": 50,
    "stamina": 30,
    "max_stamina": 50,
    "gold": 1240,
    "stats": {
      "strength": 10,
      "dexterity": 14,
      "constitution": 12,
      "intelligence": 8,
      "wisdom": 10,
      "charisma": 6
    },
    "equipment_bonuses": {},
    "temporary_effects": {},
    "in_combat": false,
    "in_dialogue": false,
    "following": null
  }
}
```

`stats`는 `players` 테이블의 `stat_strength` 계열 6개 컬럼에 대응한다. `hp`는 `stat_current` JSON에서, `equipment_bonuses`와 `temporary_effects`는 각각 `stat_equipment_bonuses`, `stat_temporary_effects` JSON에서 온다.

`gold`는 별도 컬럼이 아니라 인벤토리의 화폐 아이템 합계다. 서버가 계산해서 보낸다.

상태가 바뀌면 서버가 자발적으로 다시 보낸다. 전투 중에는 `combat_state`가 HP를 포함하므로 중복 전송을 피하기 위해 `player_state`를 매 턴 보내지 않는다.

## inventory

```json
{
  "type": "inventory",
  "seq": null,
  "total_weight": 12.0,
  "max_weight": 20.0,
  "items": [],
  "equipped": {
    "HEAD": null,
    "BODY": "b8593baf-...",
    "WEAPON": "c277fa85-...",
    "SHIELD": null,
    "FEET": null
  }
}
```

`items`는 인벤토리와 장착 중인 아이템을 모두 포함한다. 장착 여부는 각 아이템의 `is_equipped`로 판별한다. `equipped`는 슬롯별 uuid 매핑이며 빈 슬롯은 `null`이다.

스택 가능한 아이템은 서버가 그룹으로 묶어 하나의 항목으로 보내고 `stack_count`에 수량을 담는다. 그룹의 uuid는 대표 아이템의 uuid이며, 수량을 지정하는 액션(`drop`, `put`, `shop_sell`)은 이 uuid와 `quantity`로 처리된다.

## container_contents

```json
{
  "type": "container_contents",
  "seq": 50,
  "container_id": "2be3c315-...",
  "items": []
}
```

컨테이너 내부 아이템도 `entities.md`의 오브젝트 스키마를 따른다. 기존 구현에는 컨테이너 내부 목록을 배열 인덱스로 지정하는 경로가 있었으나 폐기되고 uuid로 통일된다.

## combat_state

```json
{
  "type": "combat_state",
  "seq": null,
  "combat_id": "7f3a9b21-...",
  "round": 3,
  "current_turn": "cf65f7f3-...",
  "is_my_turn": true,
  "turn_order": ["cf65f7f3-...", "49a55ff4-...", "2ff6700d-..."],
  "allies": [],
  "enemies": [],
  "is_over": false
}
```

`allies`와 `enemies`의 각 항목은 전투 참가자다.

```json
{
  "id": "49a55ff4-...",
  "name": { "en": "Ash Raider", "ko": "재의 약탈자" },
  "hp": 18,
  "max_hp": 30,
  "level": 4,
  "is_alive": true
}
```

전투가 끝나면 `is_over`가 true인 `combat_state`를 보낸 뒤 `room_info`와 `player_state`를 보낸다. 클라이언트는 전투 화면을 닫고 탐험 화면으로 전환한다.

## dialogue

```json
{
  "type": "dialogue",
  "seq": null,
  "dialogue_id": "9c4e1a55-...",
  "speaker": {
    "id": "2be3c315-...",
    "name": { "en": "Town Merchant", "ko": "마을 상인" }
  },
  "lines": [
    { "key": "npc.merchant.greeting", "params": {} }
  ],
  "choices": [
    { "index": 1, "text": { "key": "npc.merchant.who_are_you", "params": {} } },
    { "index": 2, "text": { "key": "npc.merchant.where_is_this", "params": {} } },
    { "index": 3, "text": { "key": "npc.merchant.show_goods", "params": {} } },
    { "index": 4, "text": { "key": "npc.dialogue.farewell", "params": {} } }
  ],
  "is_active": true
}
```

`choices[].index`는 대화 인스턴스 안에서만 유효한 로컬 번호다. 클라이언트는 이 값을 `dialogue_choice` 액션의 params로 되돌려 보낸다. uuid 규약의 예외이며, 선택지는 엔티티가 아니라 대화 트리의 분기이므로 uuid를 갖지 않는다.

`is_active`가 false면 대화가 종료됐다는 뜻이다. 클라이언트는 대화 창을 닫는다.

## shop

```json
{
  "type": "shop",
  "seq": 51,
  "merchant_id": "2be3c315-...",
  "items": [
    {
      "template_id": "health_potion",
      "name": { "en": "Health Potion", "ko": "체력 물약" },
      "description": { "en": "Restores 25 health.", "ko": "체력을 25 회복한다." },
      "category": "consumable",
      "buy_price": 50,
      "sell_price": 20,
      "stock": null
    }
  ]
}
```

상점 재고는 `item_prices` 테이블의 `template_id` 단위다. 실물 아이템이 아니므로 uuid가 없고 구매는 `template_id`로 지정한다. `stock`이 `null`이면 무제한이다. `buy_price`나 `sell_price`가 0이면 해당 방향 거래가 불가하며 클라이언트는 그 버튼을 숨긴다.

## who_result

```json
{
  "type": "who_result",
  "seq": 52,
  "players": [
    {
      "id": "cf65f7f3-...",
      "username": "player5426",
      "display_name": "SUPERADMIN",
      "faction_id": "ash_knights",
      "is_admin": true
    }
  ]
}
```

`whisper` 대상 uuid를 확보하는 경로다. 좌표는 포함하지 않는다. 플레이어 위치를 다른 플레이어에게 노출하지 않기 위한 조치다.

## chat

```json
{
  "type": "chat",
  "channel": "room",
  "from": {
    "id": "cf65f7f3-...",
    "display_name": "나그네"
  },
  "message": "안녕하세요",
  "timestamp": "2026-08-08T16:45:11.652000"
}
```

`channel`이 `whisper`면 발신자와 수신자에게만 전달된다. 채팅 본문은 번역하지 않는다.

## event

```json
{
  "type": "event",
  "category": "combat",
  "message": {
    "key": "combat.damage_dealt",
    "params": {
      "target": { "en": "Ash Raider", "ko": "재의 약탈자" },
      "damage": 12
    }
  }
}
```

번역 키와 치환 파라미터만 전달한다. 완성된 문장을 보내지 않는다. `params` 값이 오브젝트면 언어별 dict이므로 클라이언트가 현재 locale에 맞는 값을 골라 치환하고, 스칼라면 그대로 치환한다.

`category`는 클라이언트가 로그 채널을 분류하는 데 쓴다. 값은 `combat`, `movement`, `item`, `social`, `system`, `dialogue`다.

## action_rejected

```json
{
  "type": "action_rejected",
  "seq": 43,
  "verb": "talk",
  "target": "2ff6700d-...",
  "reason_code": "NOT_APPLICABLE",
  "message": { "key": "action.cannot_talk_to_target", "params": {} }
}
```

클라이언트가 낙관적으로 구성한 버튼이 실제로는 적용 불가할 때의 응답이다. `seq`로 어느 요청이 거절됐는지 판별하고 `reason_code`로 처리를 분기한다. 사유 코드 목록은 entities.md에 정의한다.

## error

```json
{
  "type": "error",
  "seq": null,
  "reason_code": "MALFORMED_MESSAGE",
  "detail": "line is not valid JSON"
}
```

프로토콜 수준 오류다. 게임 로직의 거절은 `action_rejected`를 쓰고, `error`는 JSON 파싱 실패, 필수 필드 누락, 인증 전 금지된 메시지처럼 계약 위반에만 사용한다. `detail`은 개발자용 영문 문자열이며 사용자에게 표시할 목적이 아니다.
