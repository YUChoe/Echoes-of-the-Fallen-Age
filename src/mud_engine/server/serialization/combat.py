# -*- coding: utf-8 -*-
"""전투 상태 페이로드 직렬화

전투 참가자는 `Combatant` 구조를 따른다. 방 정보의 monster 엔티티와 필드가
다르다. `Combatant` 는 armor_class 를 갖지 않고 defense 를 가지며 플레이어와
몬스터가 같은 구조로 표현된다.

프로토콜 계약: docs/protocol/server-to-client.md
"""

from typing import TYPE_CHECKING, Any, Optional

from ...game.combatant import Combatant, CombatantType

if TYPE_CHECKING:
    # game.combat 은 combat_handler 를 거쳐 자신에게 돌아오는 순환 임포트가 있다.
    # 런타임에는 임포트하지 않고 타입 검사용으로만 참조한다.
    from ...game.combat import CombatInstance


def serialize_combatant(combatant: Combatant) -> dict[str, Any]:
    """전투 참가자를 변환한다.

    `Combatant.name` 은 문자열 단일 값이므로 그대로 쓰지 않는다.
    몬스터는 `data["monster"]` 의 언어별 dict 를, 플레이어는 표시 이름을
    양쪽 언어에 복제해 사용한다.
    """
    return {
        "id": str(combatant.id),
        "name": _combatant_name(combatant),
        "combatant_type": combatant.combatant_type.value,
        "hp": combatant.current_hp,
        "max_hp": combatant.max_hp,
        "attack_power": combatant.attack_power,
        "defense": combatant.defense,
        "is_defending": bool(combatant.is_defending),
        "is_alive": combatant.is_alive(),
    }


def build_combat_state(
    combat: "CombatInstance",
    viewer_id: str,
    seq: Optional[int] = None,
) -> dict[str, Any]:
    """combat_state 메시지를 만든다.

    Args:
        combat: 전투 인스턴스
        viewer_id: 요청 플레이어의 id. is_my_turn 판정과 아군 분류에 쓴다
        seq: 클라이언트 요청에 대한 응답이면 그 번호
    """
    from .envelope import build

    current = combat.get_current_combatant()
    current_turn_id = str(current.id) if current else None

    allies: list[dict[str, Any]] = []
    enemies: list[dict[str, Any]] = []

    # 현재 구현은 참가자 타입으로 아군과 적을 구분한다.
    # combat.py 에 "적대적인지 아닌지로 구분해야 함" TODO 가 있으나
    # 동작을 바꾸지 않기 위해 기존 기준을 유지한다.
    for combatant in combat.combatants:
        payload = serialize_combatant(combatant)
        if combatant.combatant_type == CombatantType.PLAYER:
            allies.append(payload)
        else:
            enemies.append(payload)

    return build(
        "combat_state",
        seq=seq,
        combat_id=str(combat.id),
        round=combat.turn_number,
        current_turn=current_turn_id,
        is_my_turn=current_turn_id == str(viewer_id),
        turn_order=[str(cid) for cid in combat.turn_order],
        allies=allies,
        enemies=enemies,
        is_over=not combat.is_active,
    )


def _combatant_name(combatant: Combatant) -> dict[str, str]:
    """참가자 이름을 언어별 dict 로 만든다."""
    from .entity import localized_dict

    if combatant.combatant_type == CombatantType.MONSTER:
        monster = (combatant.data or {}).get("monster")
        if monster is not None:
            names = localized_dict(getattr(monster, "name", None))
            if names:
                return names

    # 플레이어이거나 몬스터 이름을 얻을 수 없는 경우
    name = str(combatant.name)
    return {"en": name, "ko": name}
