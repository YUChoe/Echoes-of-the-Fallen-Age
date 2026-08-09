# -*- coding: utf-8 -*-
"""플레이어 상태 페이로드 직렬화

HP 의 진실은 `PlayerStats.current_values["hp"]` 이며 최대치는 체력 기반 계산값이다.
스태미나는 Player 모델이 아니라 세션이 보유하므로 호출부가 전달한다.

프로토콜 계약: docs/protocol/server-to-client.md
"""

from typing import Any, Optional

from ...game.models.player import Player
from ...game.stats import StatType

# 클라이언트에 노출하는 1차 능력치
_PRIMARY_STATS = (
    StatType.STR,
    StatType.DEX,
    StatType.INT,
    StatType.WIS,
    StatType.CON,
    StatType.CHA,
)


def serialize_stats(player: Player) -> dict[str, int]:
    """1차 능력치를 변환한다.

    장비 보너스가 포함된 값이다. 2차 능력치는 모두 계산값이므로
    클라이언트가 필요하면 별도로 노출한다.
    """
    if not player.stats:
        return {}

    return {stat.value: player.stats.get_primary_stat(stat) for stat in _PRIMARY_STATS}


def build_player_state(
    player: Player,
    room_id: Optional[str] = None,
    stamina: float = 0.0,
    max_stamina: float = 0.0,
    gold: int = 0,
    in_combat: bool = False,
    in_dialogue: bool = False,
    following: Optional[str] = None,
    seq: Optional[int] = None,
) -> dict[str, Any]:
    """player_state 메시지를 만든다.

    Args:
        player: 대상 플레이어
        room_id: 현재 방 id. 세션이 보유하므로 호출부가 전달한다
        stamina: 현재 스태미나. 세션 값이다
        max_stamina: 최대 스태미나. 세션 값이다
        gold: 화폐 합계. CurrencyManager 가 계산한 값이다
        in_combat: 전투 중 여부. 세션 상태다
        in_dialogue: 대화 중 여부. 세션 상태다
        following: 따라가는 대상 id. 세션 상태다
        seq: 클라이언트 요청에 대한 응답이면 그 번호
    """
    from .envelope import build

    stats = player.stats

    payload: dict[str, Any] = {
        "id": str(player.id),
        "username": str(player.username),
        "display_name": player.get_display_name(),
        "faction_id": player.faction_id,
        "room_id": room_id,
        "x": player.last_room_x,
        "y": player.last_room_y,
        "hp": stats.get_current_hp() if stats else 0,
        "max_hp": stats.get_secondary_stat(StatType.HP) if stats else 0,
        "stamina": round(float(stamina), 2),
        "max_stamina": round(float(max_stamina), 2),
        "gold": int(gold),
        "stats": serialize_stats(player),
        "equipment_bonuses": dict(stats.equipment_bonuses) if stats else {},
        "temporary_effects": dict(stats.temporary_effects) if stats else {},
        "in_combat": bool(in_combat),
        "in_dialogue": bool(in_dialogue),
        "following": following,
    }

    return build("player_state", seq=seq, player=payload)
