# 서버 → 클라이언트 메시지

서버는 상태 스냅샷과 이벤트를 구분해서 보낸다. 스냅샷(`room_info`, `player_state`, `inventory`, `combat_state`)은 해당 영역의 전체 상태를 담고, 이벤트(`event`, `entity_enter`, `entity_leave`)는 변화만 알린다. 클라이언트는 스냅샷으로 화면을 재구성하고 이벤트로 부분 갱신한다.

| type | seq | 설명 |
|---|---|---|
| `welcome` | 없음 | 접속 직후 서버 정보 |
| `register_result` | 있음 | 계정 생성 결과 |
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
| `readable_content` | 있음 | 읽을 수 있는 물건의 본문 |
| `combat_state` | 조건부 | 전투 전체 상태 |
| `dialogue` | 조건부 | 대화 상태 |
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
  "channel": "game",
  "server_version": "development@dev",
  "supported_locales": ["en", "ko"],
  "title": {
    "en": "The Chronicles of Karnas: Divided Dominion",
    "ko": "카르나스 연대기: 분할된 지배권"
  }
}
```

`channel`은 이 연결이 어느 채널인지 알린다. 값은 `game` 또는 `admin`이다. 두 채널은 프레이밍 규약이 같고 포트만 다르므로, 클라이언트가 잘못된 포트에 붙었을 때 조용히 실패하지 않도록 서버가 접속 직후 채널을 밝힌다. 어드민 채널의 `welcome`은 `supported_locales`와 `title`을 담지 않는다. 어드민은 번역을 하지 않고 도구가 소비하기 때문이다.

클라이언트는 기대한 `channel`이 아니면 연결을 끊고 접속 설정 오류를 알린다.

`supported_locales`는 DB의 이중언어 컬럼이 제공하는 언어를 알린다. 클라이언트의 UI 번역 범위와는 별개다. 클라이언트가 서버보다 많은 언어를 지원하면 엔티티 이름은 폴백 언어로 표시된다.

### 타 채널 메시지 거절

각 채널은 상대 채널 전용 메시지를 조용히 무시하지 않고 사유를 붙여 거절한다.

| 수신 채널 | 대상 메시지 | 응답 |
|---|---|---|
| game | `admin_login`, `account_create`, `admin_*` | `error`, `reason_code: NOT_APPLICABLE` |
| admin | `login`, `logout`, `action`, `chat`, `client_info` | `admin_rejected`, `reason_code: NOT_APPLICABLE` |

`detail`에 기대 채널과 현재 채널을 모두 담는다. `ping`은 두 채널 모두에서 허용된다.

## register_result

성공:

```json
{
  "type": "register_result",
  "seq": 1,
  "success": true,
  "player_id": "a1b2c3d4-..."
}
```

실패:

```json
{
  "type": "register_result",
  "seq": 1,
  "success": false,
  "reason_code": "USERNAME_TAKEN"
}
```

`register`의 응답이다. 사유는 `USERNAME_TAKEN`, `VALIDATION_FAILED`, `INTERNAL_ERROR`뿐이다. 어느 항목이 문제인지는 응답에 담지 않고 서버 로그에만 남긴다. 클라이언트가 같은 규칙으로 미리 검증하므로 서버까지 온 검증 실패는 클라이언트 버그이거나 조작된 요청이다.

실패 응답에는 `player_id`를 담지 않는다.

성공해도 세션은 인증되지 않는다. 클라이언트는 이어서 `login`을 보낸다.

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
  },
  "admin_channel": {
    "available": true,
    "channel": "admin",
    "requires_reauth": true
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

`is_admin`이 true여도 게임 세션에서 어드민 기능을 쓸 수 없다. 어드민은 별도 채널에서 별도 인증을 거친다.

### admin_channel

`is_admin`이 true인 계정에만 담긴다. 거짓이면 필드가 아예 없다.

| 필드 | 의미 |
|---|---|
| `available` | 어드민 채널에 실제로 진입할 수 있는지. 권한만이 아니라 서버가 어드민 포트를 열고 있는지를 반영한다 |
| `channel` | 진입 대상 채널. 항상 `admin` |
| `requires_reauth` | 어드민 채널에서 다시 인증해야 하는지. 게임 세션 인증이 전이되지 않으므로 항상 true |

`is_admin`만으로는 진입 가능 여부를 알 수 없다. 권한이 있어도 어드민 채널을 띄우지 않은 배포가 있으므로, 클라이언트는 `available`이 true일 때만 어드민 패널 진입 버튼을 노출한다.

진입 단계는 다음과 같다.

1. 게임 채널에 로그인한다. `login_result`의 `admin_channel.available`을 확인한다.
2. true이면 어드민 패널 진입 버튼을 노출한다. false 또는 필드가 없으면 노출하지 않는다.
3. 사용자가 버튼을 누르면 어드민 채널로 별도 연결을 맺는다. 게임 연결은 유지한다.
4. `welcome`의 `channel`이 `admin`인지 확인한다.
5. `admin_login`으로 다시 인증한다. 게임 로그인 자격을 재사용해도 되지만 인증 자체는 생략할 수 없다.
6. `admin_login_result`의 `expires_at`을 보관한다. 2시간이 지나면 서버가 `SESSION_EXPIRED`로 거절하므로 재인증한다.

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
    "silver": 1240,
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

`silver`는 별도 컬럼이 아니라 인벤토리의 실버 코인 스택 합계다. 서버가 계산해서 보낸다.

상태가 바뀌면 서버가 자발적으로 다시 보낸다. 전투 중에는 `combat_state`가 HP를 포함하므로 중복 전송을 피하기 위해 `player_state`를 매 턴 보내지 않는다.

## inventory

```json
{
  "type": "inventory",
  "seq": null,
  "total_weight": 12.0,
  "max_weight": 20.0,
  "silver": 1240,
  "items": [],
  "equipped": {
    "right_hand": "b8593baf-..."
  }
}
```

`items`는 인벤토리와 장착 중인 아이템을 모두 포함한다. 장착 여부는 각 아이템의 `is_equipped`로 판별한다.

`equipped`는 슬롯별 uuid 매핑이며 채워진 슬롯만 담는다. 서버는 슬롯 이름을 확정하지 않는다. 허용값이 16종이고 `accessory`나 대문자 `RING` 같은 레거시가 섞여 있어서다. 클라이언트가 표시할 슬롯 목록을 자체 보유하고 없는 키를 빈 슬롯으로 처리한다.

`silver`는 `CurrencyManager`가 집계한 실버 잔액이다. `properties.template_id`가 `silver_coin`인 스택의 수량 합이다.

화폐는 실버 하나다. 골드는 화폐가 아니라 아이템이며 잔액에 잡히지 않는다. 1골드는 10실버의 값을 가지므로 NPC에게 팔아 실버로 바꿀 수 있다. 두 동전의 무게는 같다.

서버는 아이템을 묶지 않고 개별 엔티티로 보낸다. 같은 종류가 여럿이면 uuid가 다른 항목 여러 개가 온다. `stack_count`는 `properties.quantity` 값이며 현재 화폐만 1을 초과한다. 클라이언트가 표시할 때 같은 `template_id`끼리 묶을 수 있으나 액션의 `target`은 개별 uuid를 사용한다.

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

## readable_content

```json
{
  "type": "readable_content",
  "seq": 52,
  "object_id": "98355bcf-...",
  "readable_type": "scroll",
  "page": 1,
  "total_pages": 1,
  "content": {
    "en": "Hear us, O Alva, whose name means 'white' and 'bright'...",
    "ko": "들으소서, 알바여. 당신의 이름은 우리 선조의 말로 '희다', '밝다'를 뜻하나이다..."
  }
}
```

`read` verb의 응답이다. `content`는 언어별 dict이며 번역 키가 아니다. 책과 두루마리의 본문은 DB의 이중언어 컬럼에 담긴 콘텐츠이므로 클라이언트 번역 파일로 옮기지 않는다. 엔티티 이름·설명과 같은 성질이다.

여러 쪽이면 `total_pages`가 1보다 크고 클라이언트가 `read`에 `params.page`를 붙여 다음 쪽을 요청한다. 범위를 벗어난 쪽은 `INVALID_PARAMS`로 거절하며 `params.total`에 전체 쪽수를 담는다.

`readable_type`은 표시 형태를 고르는 힌트다. 값은 `book`, `scroll`, `note`다.

Lua `on_read` 콜백이 있는 물건은 분위기 문장이 `event`(`category: "item"`)로 먼저 오고 본문이 이 메시지로 온다. 콜백만 있고 `readable` 속성이 없으면 이 메시지 없이 `event`만 간다.

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
  "combatant_type": "monster",
  "hp": 18,
  "max_hp": 30,
  "attack_power": 6,
  "defense": 3,
  "is_defending": false,
  "is_alive": true
}
```

전투 참가자는 `Combatant` 구조를 따른다. 방 정보의 monster 엔티티와 필드가 다르다. `Combatant`는 `armor_class`를 갖지 않고 `defense`를 가지며, 플레이어와 몬스터가 같은 구조로 표현된다.

`name`은 몬스터의 경우 `data["monster"]`의 언어별 dict에서, 플레이어의 경우 표시 이름을 양쪽 언어에 복제해 만든다. `Combatant.name`은 문자열 단일 값이므로 직접 쓰지 않는다.

`combatant_type`은 `player` 또는 `monster`다. `allies`와 `enemies` 분류는 요청 플레이어를 기준으로 서버가 나누며, 현재 구현은 참가자 타입으로 구분한다.

레벨은 제공하지 않는다. 서버에 level 개념이 없다. 전투 화면은 HP와 `attack_power`, `defense`로 상대의 강함을 표현한다.

전투가 끝나면 `is_over`가 true인 `combat_state`를 보낸 뒤 `room_info`와 `player_state`를 보낸다. 클라이언트는 전투 화면을 닫고 탐험 화면으로 전환한다.

## dialogue

```json
{
  "type": "dialogue",
  "seq": null,
  "dialogue_id": "9c4e1a55-...",
  "speaker": {
    "id": "3914fbe8-...",
    "name": { "en": "Brother Marcus", "ko": "마르쿠스 수사" }
  },
  "lines": [
    {
      "key": "npc.brother_marcus.intro.text.1",
      "params": { "player_name": "player5426" }
    }
  ],
  "choices": [
    { "index": 1, "text": { "key": "npc.brother_marcus.intro.choice.1", "params": {} } },
    { "index": 2, "text": { "key": "npc.brother_marcus.intro.choice.2", "params": {} } },
    { "index": 3, "text": { "key": "npc.brother_marcus.intro.choice.3", "params": {} } },
    { "index": 4, "text": { "key": "npc.dialogue.farewell", "params": {} } }
  ],
  "is_active": true
}
```

`choices[].index`는 대화 인스턴스 안에서만 유효한 로컬 번호다. 클라이언트는 이 값을 `dialogue_choice` 액션의 params로 되돌려 보낸다. uuid 규약의 예외이며, 선택지는 엔티티가 아니라 대화 트리의 분기이므로 uuid를 갖지 않는다.

`is_active`가 false면 대화가 종료됐다는 뜻이다. 클라이언트는 대화 창을 닫는다.

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
    "key": "combat.hit",
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
  "reason_code": "NOT_APPLICABLE"
}
```

클라이언트가 낙관적으로 구성한 버튼이 실제로는 적용 불가할 때의 응답이다. `seq`로 어느 요청이 거절됐는지 판별하고 `reason_code`로 처리를 분기한다. 사유 코드 목록은 entities.md에 정의한다.

`message`는 선택 항목이다. 사유 코드만으로 화면을 구성할 수 없을 때만 담는다. 거절 사유 자체는 코드로 전달되며 개발자용 설명은 서버 로그에만 남는다.

```json
{
  "type": "action_rejected",
  "seq": 44,
  "verb": "changename",
  "reason_code": "COOLDOWN",
  "message": {
    "key": "account.name_change_cooldown",
    "params": { "hours_left": 5.2 }
  }
}
```

이름 변경의 재시도 대기가 그런 경우다. 남은 시간을 실어야 하므로 키와 파라미터를 함께 보낸다.

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
