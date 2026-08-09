# -*- coding: utf-8 -*-
"""엔티티 페이로드 직렬화

모델을 클라이언트가 소비할 dict 로 변환한다. 언어를 선택하지 않고
`{"en": ..., "ko": ...}` dict 를 그대로 담는다. 번역과 표시는 클라이언트 책임이다.

모델의 `to_dict()` 는 DB 영속화 전용 포맷이므로 여기서 쓰지 않는다.
`BaseModel.to_dict()` 가 dict 와 list 를 JSON 문자열로 만들고 name 을
`name_en`/`name_ko` 로 쪼개기 때문이다.

프로토콜 계약: docs/protocol/entities.md
"""

import json
from typing import Any, Optional

from ...game import faction_rules
from ...game.models.gameobject import GameObject
from ...game.models.player import Player
from ...game.monster import Monster

# 사용 가능 판정에 쓰이는 properties 키.
# commands/use_command.py 의 usable_keys 와 같은 목록이다.
_USABLE_KEYS = ("hp_restore", "stamina_restore", "mana_restore", "heal_amount")


def coerce_properties(raw: Any) -> dict[str, Any]:
    """properties 를 dict 로 정규화한다.

    `BaseModel.to_dict()` 가 dict 를 JSON 문자열로 만들기 때문에 문자열로
    전달되는 경우가 실제로 발생한다. 기존 판정 코드도 같은 방어를 한다.
    """
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def localized_dict(raw: Any) -> dict[str, str]:
    """언어별 dict 를 정규화한다.

    모델은 `name`/`description` 을 `Dict[str, str]` 로 보유한다.
    `name_en`/`name_ko` 속성은 존재하지 않는다.
    """
    if isinstance(raw, dict):
        return {str(k): str(v) for k, v in raw.items()}
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {}
        if isinstance(parsed, dict):
            return {str(k): str(v) for k, v in parsed.items()}
    return {}


def is_container(properties: Any) -> bool:
    """컨테이너 여부.

    commands/container_commands.py 와 use_command.py 에 중복 정의된
    `_is_container` 와 같은 판정이다.
    """
    return bool(coerce_properties(properties).get("is_container", False))


def is_readable(properties: Any) -> bool:
    """읽기 가능 여부.

    commands/read_command.py 의 `_is_readable` 과 같은 판정이다.
    `readable` 값이 비어 있지 않은 dict 일 때만 참이다.
    """
    readable = coerce_properties(properties).get("readable", {})
    if isinstance(readable, str):
        try:
            readable = json.loads(readable)
        except (json.JSONDecodeError, TypeError):
            return False
    return bool(readable) if isinstance(readable, dict) else False


def is_usable(properties: Any) -> bool:
    """사용 가능 여부.

    commands/use_command.py 의 `usable_keys` 판정과 같다.
    Lua 콜백만 가진 아이템은 이 판정으로 잡히지 않는다.
    """
    props = coerce_properties(properties)
    return any(key in props for key in _USABLE_KEYS)


def serialize_monster(
    monster: Monster,
    viewer_faction: Optional[str] = None,
    can_talk: bool = False,
) -> dict[str, Any]:
    """몬스터를 엔티티 페이로드로 변환한다.

    Args:
        monster: 대상 몬스터
        viewer_faction: 보는 플레이어의 종족. disposition 계산에 쓴다
        can_talk: 대화 스크립트 보유 여부. 호출부가 조회해 주입한다

    Returns:
        엔티티 페이로드. 레벨과 상인 여부는 포함하지 않는다
    """
    monster_type = monster.monster_type
    behavior = monster.behavior

    return {
        "id": str(monster.id),
        "kind": "monster",
        "name": localized_dict(monster.name),
        "description": localized_dict(monster.description),
        "hp": monster.current_hp,
        "max_hp": monster.max_hp,
        "armor_class": monster.stats.armor_class if monster.stats else 10,
        "attack_power": monster.stats.attack_power if monster.stats else 1,
        "faction_id": monster.faction_id,
        "disposition": faction_rules.get_disposition(viewer_faction, monster.faction_id),
        "monster_type": monster_type.value if hasattr(monster_type, "value") else str(monster_type),
        "behavior": behavior.value if hasattr(behavior, "value") else str(behavior),
        "is_alive": bool(monster.is_alive),
        "can_talk": bool(can_talk),
    }


def stack_count(properties: Any) -> int:
    """이 레코드가 나타내는 수량.

    `properties.quantity` 값이며 없으면 1이다. 현재 이 키를 사용하는 것은
    화폐(골드, 은화)뿐이고 `CurrencyManager` 가 관리한다.

    같은 종류 아이템이 여럿이면 개별 레코드로 존재하며 서버가 묶지 않는다.
    """
    raw = coerce_properties(properties).get("quantity", 1)
    if isinstance(raw, bool):
        return 1
    if isinstance(raw, (int, float)):
        return max(1, int(raw))
    return 1


def serialize_object(obj: GameObject) -> dict[str, Any]:
    """게임 오브젝트를 엔티티 페이로드로 변환한다.

    `max_stack` 은 담지 않는다. DB 에 값이 있으나 서버가 그에 따라 아무 동작도
    하지 않으므로(스택 병합이 화폐에만 구현됨) 클라이언트가 쓸 수 없다.

    Args:
        obj: 대상 오브젝트

    Returns:
        엔티티 페이로드
    """
    properties = coerce_properties(obj.properties)

    return {
        "id": str(obj.id),
        "kind": "object",
        "name": localized_dict(obj.name),
        "description": localized_dict(obj.description),
        # category 는 모델 필드가 아니라 properties 에서 읽는다.
        # GameObject.from_dict 가 DB 의 category 컬럼을 버린다.
        "category": str(properties.get("category", "misc")),
        "weight": float(obj.weight),
        "stack_count": stack_count(properties),
        "equipment_slot": obj.equipment_slot,
        "is_equipped": bool(obj.is_equipped),
        "is_container": is_container(properties),
        "is_readable": is_readable(properties),
        "is_usable": is_usable(properties),
        "template_id": properties.get("template_id"),
    }


def serialize_player(player: Player, include_vitals: bool = True) -> dict[str, Any]:
    """플레이어를 엔티티 페이로드로 변환한다.

    같은 방의 다른 플레이어를 표시할 때 쓴다. 좌표와 인벤토리는 포함하지 않는다.

    Args:
        player: 대상 플레이어
        include_vitals: HP 를 포함할지 여부
    """
    display_name = player.get_display_name()

    payload: dict[str, Any] = {
        "id": str(player.id),
        "kind": "player",
        # 플레이어 이름은 언어별로 다르지 않지만 공통 스키마를 유지한다
        "name": {"en": display_name, "ko": display_name},
        "description": {"en": "", "ko": ""},
        "username": str(player.username),
        "display_name": display_name,
        "faction_id": player.faction_id,
    }

    if include_vitals and player.stats:
        payload["hp"] = player.stats.get_current_hp()
        payload["max_hp"] = player.stats.get_secondary_stat(_hp_stat_type())

    return payload


def _hp_stat_type() -> Any:
    """StatType.HP 를 지연 임포트한다. 순환 임포트를 피하기 위한 것이다."""
    from ...game.stats import StatType

    return StatType.HP
