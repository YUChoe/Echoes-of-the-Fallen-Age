# 엔티티 스키마, 번역, 거절 코드

## 엔티티 공통

모든 엔티티는 다음 필드를 갖는다.

```json
{
  "id": "49a55ff4-a1d9-4449-a72c-c664686e1102",
  "kind": "monster",
  "name": { "en": "Ash Raider", "ko": "재의 약탈자" },
  "description": { "en": "...", "ko": "..." }
}
```

| 필드 | 타입 | 설명 |
|---|---|---|
| `id` | string(uuid) | 인스턴스 uuid. 대상 지정의 유일한 키 |
| `kind` | string | `monster`, `object`, `player` |
| `name` | object | 언어별 이름. 키는 `welcome.supported_locales`의 값 |
| `description` | object | 언어별 설명 |

`name`과 `description`은 언어를 고르지 않은 dict 그대로 전달된다. 서버 모델에 이미 이 형태가 존재하므로 언어 선택 단계만 제거하면 된다. 클라이언트가 현재 locale로 값을 고르고, 없으면 `en`으로 폴백한다.

`id`는 인스턴스 단위다. 몬스터는 스폰마다 고유 uuid를 갖는다. 템플릿 식별자(`template_id`)는 별개이며 상점 거래에만 쓰인다.

## monster

NPC와 몬스터는 같은 테이블(`monsters`)로 표현된다. 별도의 NPC 테이블은 없다. 구분은 `disposition`과 `is_merchant`로 이뤄진다.

```json
{
  "id": "49a55ff4-...",
  "kind": "monster",
  "name": { "en": "Town Merchant", "ko": "마을 상인" },
  "description": { "en": "...", "ko": "..." },
  "hp": 60,
  "max_hp": 60,
  "armor_class": 12,
  "attack_power": 6,
  "faction_id": "ash_knights",
  "disposition": "friendly",
  "monster_type": "passive",
  "behavior": "stationary",
  "is_alive": true,
  "can_talk": true
}
```

| 필드 | 타입 | 설명 |
|---|---|---|
| `hp` `max_hp` | integer | `stats` JSON의 `current_hp`와 체력 기반 계산 최대치 |
| `armor_class` | integer | 방어도. 민첩 보정 기반 계산값 |
| `attack_power` | integer | 공격력. 힘 기반 계산값 |
| `faction_id` | string 또는 null | 종족. `factions.id` 참조 |
| `disposition` | string | 요청 플레이어 기준 상대 관계 |
| `monster_type` | string | `aggressive`, `passive`, `neutral` |
| `behavior` | string | `stationary`, `roaming`, `territorial`, `aggressive` |
| `is_alive` | boolean | 생존 여부 |
| `can_talk` | boolean | 대화 스크립트 보유 여부 |

레벨 개념은 제공하지 않는다. 서버 코드에서 의도적으로 제거된 개념이며 `Monster`와 `Player` 모두 level 필드가 없고 DB 컬럼도 없다. 상대적 강함을 짐작할 근거로는 `max_hp`, `armor_class`, `attack_power`를 제공한다. 이 세 값은 모두 능력치에서 계산되는 파생값이므로 별도 저장이 필요하지 않다.

상인 여부는 제공하지 않는다. 모든 캐릭터와 거래할 수 있으므로 구분이 불필요하다. 클라이언트는 `disposition`이 적대가 아닌 대상에게 거래 버튼을 표시할 수 있다.

`can_talk`은 대화 스크립트 파일의 존재 여부다. 거짓이어도 서버는 대화 시도를 거절하지 않고 침묵 응답을 돌려주므로, 클라이언트는 이 값을 버튼 표시 우선순위 판단에만 쓴다.

`disposition`은 서버가 계산한다. 값은 `friendly`, `neutral`, `hostile`이다. 판정에 `factions`와 `faction_relations` 테이블이 필요하므로 클라이언트가 계산할 수 없다. 클라이언트는 이 값으로 인물/동물/적 구역을 나눠 표시한다.

`monster_type`과 `disposition`은 다른 개념이다. `monster_type`은 몬스터 자체의 성향(선공 여부)이고 `disposition`은 요청자와의 종족 관계다. 같은 몬스터가 플레이어의 종족에 따라 다른 `disposition`을 갖는다.

`is_merchant`와 `can_talk`은 `properties` JSON에서 파생된 boolean이다. 클라이언트가 상점 버튼과 대화 버튼을 구성하는 근거다.

## object

```json
{
  "id": "b8593baf-...",
  "kind": "object",
  "name": { "en": "Health Potion", "ko": "체력 물약" },
  "description": { "en": "Restores 25 health.", "ko": "체력을 25 회복한다." },
  "category": "consumable",
  "weight": 0.3,
  "stack_count": 1,
  "equipment_slot": null,
  "is_equipped": false,
  "is_container": false,
  "is_readable": false,
  "is_usable": true,
  "template_id": "health_potion"
}
```

| 필드 | 타입 | 설명 |
|---|---|---|
| `category` | string | `weapon`, `armor`, `consumable`, `misc`. 모델에는 필드가 없고 `properties.category`에서 읽는다 |
| `weight` | number | 개당 무게 |
| `stack_count` | integer | 이 레코드가 나타내는 수량. `properties.quantity` 값이며 없으면 1 |
| `equipment_slot` | string 또는 null | `head`, `chest`, `right_hand`, `left_hand`, `feet` 등. null이면 장착 불가 |
| `is_equipped` | boolean | 장착 여부 |
| `is_container` | boolean | 다른 아이템을 담을 수 있는지 |
| `is_readable` | boolean | 읽을 수 있는지 |
| `is_usable` | boolean | 사용할 수 있는지 |
| `template_id` | string 또는 null | 템플릿 식별자. 상점 가격 조회 기준 |

`weight`는 개당 무게이므로 총 무게는 `weight × stack_count`다. 인벤토리의 `total_weight`는 서버가 계산한 값이다.

### 수량과 스택

`stack_count`는 `properties.quantity` 값이다. 현재 이 키를 사용하는 것은 화폐(골드, 은화)뿐이며 `CurrencyManager`가 관리한다. 그 밖의 아이템은 `quantity`를 갖지 않으므로 `stack_count`가 1이다.

같은 종류 아이템이 여럿 있으면 서버는 개별 엔티티로 보낸다. 체력 물약 4개는 uuid가 다른 엔티티 4개다. 클라이언트가 표시할 때 같은 `template_id`끼리 묶어 수량을 보여줄 수 있으나, 액션의 `target`은 개별 uuid를 사용한다.

`max_stack`은 제공하지 않는다. DB에 컬럼이 있고 값이 설정되어 있지만 서버가 그에 따라 아무 동작도 하지 않는다. 스택 병합 로직이 `CurrencyManager`에만 있고 일반 아이템에는 없으며 `_group_stackable_objects`도 무력화된 상태다. 클라이언트가 이 값으로 판단할 수 있는 것이 없으므로 전달하지 않는다.

수량 지정 액션(`drop`, `put`, `shop_sell`)의 `quantity` params는 화폐처럼 `stack_count`가 1을 초과하는 경우에만 의미가 있다. 그 밖의 아이템은 개별 uuid로 처리한다.

파생 boolean(`is_container`, `is_readable`, `is_usable`)은 `properties` JSON과 `category`에서 서버가 계산해 내보낸다. 클라이언트가 `properties` 원본을 해석하지 않도록 하기 위한 것이다. 이는 가용 동사 목록을 서버가 결정하는 것과는 다르다. 서버는 대상의 성질만 알려주고, 그 성질로 어떤 버튼을 만들지는 클라이언트가 판단한다.

## player

```json
{
  "id": "cf65f7f3-...",
  "kind": "player",
  "name": { "en": "나그네", "ko": "나그네" },
  "description": { "en": "", "ko": "" },
  "username": "nagne",
  "display_name": "나그네",
  "faction_id": "ash_knights",
  "hp": 45,
  "max_hp": 50
}
```

플레이어 이름은 언어별로 다르지 않지만 공통 스키마를 유지하기 위해 `name`에 같은 값을 양쪽에 넣는다. `display_name`이 설정되지 않은 계정은 `username`을 사용한다.

같은 방의 다른 플레이어에게는 좌표와 인벤토리를 노출하지 않는다.

## 번역 메시지 형식

서버는 완성된 문장을 만들지 않는다.

```json
{
  "key": "combat.hit",
  "params": {
    "target": { "en": "Ash Raider", "ko": "재의 약탈자" },
    "damage": 12
  }
}
```

`key`는 `data/translations/` 아래 9개 파일에 정의된 flat key다. 이 파일들은 Godot 클라이언트로 이관되며 서버는 더 이상 로드하지 않는다.

`params` 값의 처리:

- 스칼라(숫자, 문자열, boolean)는 그대로 치환한다.
- 오브젝트는 언어별 dict로 간주하고 현재 locale의 값을 골라 치환한다.

치환 문법은 기존 번역 파일이 사용하는 Python `str.format` 형식(`{name}`)을 유지한다. 클라이언트는 이 문법을 해석하는 치환 함수를 갖는다. 번역 파일을 그대로 재사용하기 위한 결정이다.

한국어 조사는 번역 값 안에 완성형으로 유지한다. `{item}을(를) 획득했습니다` 형태를 그대로 쓰며, 클라이언트가 앞 음절의 종성을 판별해 조사를 고르는 처리는 하지 않는다. 조사 자동 선택은 향후 개선 항목으로 남긴다.

번역 키가 클라이언트에 없으면 키 문자열 자체를 표시하고 경고를 로그에 남긴다. 서버가 새 키를 쓰기 시작했는데 클라이언트가 아직 갱신되지 않은 상황에서 화면이 비지 않도록 하기 위한 규칙이다.

## 거절 사유 코드

`action_rejected`의 `reason_code` 값이다. 클라이언트는 코드별로 다른 피드백을 제공한다.

| 코드 | 의미 | 클라이언트 처리 |
|---|---|---|
| `NOT_AUTHENTICATED` | 인증 전 액션 시도 | 로그인 화면으로 전환 |
| `NOT_FOUND` | target uuid가 현재 컨텍스트에 없음 | 방 정보 재요청(`look`) |
| `NOT_APPLICABLE` | verb를 대상에 적용할 수 없음 | 해당 버튼 제거 |
| `PERMISSION_DENIED` | 권한 부족 | 안내 표시 |
| `WRONG_STATE` | 현재 상태에서 불가 | 안내 표시 |
| `NOT_YOUR_TURN` | 전투 턴이 아님 | 턴 대기 표시 |
| `OUT_OF_RANGE` | 거리 초과 | 안내 표시 |
| `INSUFFICIENT_FUNDS` | 골드 부족 | 상점 UI에 부족액 표시 |
| `INSUFFICIENT_QUANTITY` | 수량 부족 | 수량 입력 상한 조정 |
| `INVENTORY_FULL` | 무게 초과 | 안내 표시 |
| `SLOT_OCCUPIED` | 장비 슬롯 사용 중 | 교체 확인 제안 |
| `COOLDOWN` | 재사용 대기 | 남은 시간 표시. `params`에 잔여 시간 포함 |
| `TARGET_REQUIRED` | target 누락 | 클라이언트 버그. 로그 기록 |
| `INVALID_PARAMS` | params 형식 오류 | 클라이언트 버그. 로그 기록 |
| `INTERNAL_ERROR` | 서버 내부 오류 | 재시도 안내 |

`NOT_FOUND`가 자주 발생하는 경우는 클라이언트가 낡은 방 정보를 들고 있다는 뜻이다. `entity_leave`를 놓쳤을 가능성이 있으므로 방 정보를 재동기화한다.

`NOT_APPLICABLE`은 클라이언트의 버튼 추론이 서버 규칙과 어긋났음을 뜻한다. 정상 동작 범위이며 오류가 아니다. 클라이언트는 조용히 버튼을 제거하고 사용자에게 오류로 표시하지 않는다.

## 좌표와 방향

방향은 `north`, `south`, `east`, `west` 4방향이다. 좌표계는 북쪽이 y 증가 방향이다. 미니맵 렌더링에서 y축을 위로 그릴 때 이 규약을 따른다.

| 방향 | 좌표 변화 |
|---|---|
| `north` | y + 1 |
| `south` | y - 1 |
| `east` | x + 1 |
| `west` | x - 1 |

## 지형 종류

`room_type` 값은 22종이다. 클라이언트가 아이콘과 색상을 매핑한다.

`forest`, `grassland`, `coast`, `road`, `castle`, `field`, `pasture`, `wilderness`, `town`, `water`, `hedge`, `trail`, `cave`, `crypt`, `building`, `harbour`, `cliff`, `stable`, `ruins`, `gate`, `farmland`, `unknown`

목록에 없는 값을 받으면 `unknown`으로 처리한다. 서버가 지형을 추가할 때 클라이언트 갱신을 기다리지 않아도 되게 하기 위한 규칙이다.
