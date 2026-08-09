# -*- coding: utf-8 -*-
"""종족 관계 판정 규칙

플레이어를 기준으로 대상의 상대 관계(disposition)를 판정한다.
클라이언트가 방 정보를 인물, 동물, 적 구역으로 나눠 표시하는 근거가 된다.

이 판정은 `server/telnet_session.py`의 `_is_friendly_faction`과
`_is_neutral_faction`에 있던 규칙을 그대로 옮긴 것이다. 동작을 바꾸지 않는다.

상태나 데이터베이스 접근이 필요하지 않으므로 순수 함수로 둔다.

TODO: 우호도 기능 개발 시 `factions`와 `faction_relations` 테이블을 조회하는
      동적 판정으로 교체한다. 그 시점에는 동맹 관계가 반영되어 방 정보의
      인물·동물·적 분류가 달라지므로 데이터를 확인하며 진행해야 한다.
      교체 시 이 모듈을 매니저로 승격하거나 내부 구현만 바꾸면 된다.
"""

from typing import Final, Optional

# 기본 종족. players.faction_id 의 DEFAULT 값과 같다.
DEFAULT_FACTION: Final[str] = "ash_knights"

# 우호 관계 (플레이어 종족 -> 우호 종족 목록)
# 같은 종족은 아래 표와 무관하게 항상 우호로 판정한다.
_FRIENDLY_FACTIONS: Final[dict[str, list[str]]] = {
    "ash_knights": ["ash_knights"],
}

# 중립 관계 (플레이어 종족 -> 중립 종족 목록)
_NEUTRAL_FACTIONS: Final[dict[str, list[str]]] = {
    "ash_knights": ["animals"],
}

# disposition 값
FRIENDLY: Final[str] = "friendly"
NEUTRAL: Final[str] = "neutral"
HOSTILE: Final[str] = "hostile"


def is_friendly(player_faction: str, target_faction: Optional[str]) -> bool:
    """우호 관계인지 판정한다.

    Args:
        player_faction: 플레이어 종족 ID
        target_faction: 대상 종족 ID. None 이면 적대로 간주한다

    Returns:
        우호 관계이면 True
    """
    # 같은 종족이면 우호적
    if target_faction == player_faction:
        return True

    # 대상 종족이 없으면 적대적으로 간주
    if not target_faction:
        return False

    allowed = _FRIENDLY_FACTIONS.get(player_faction)
    return allowed is not None and target_faction in allowed


def is_neutral(player_faction: str, target_faction: Optional[str]) -> bool:
    """중립 관계인지 판정한다.

    Args:
        player_faction: 플레이어 종족 ID
        target_faction: 대상 종족 ID. None 이면 중립이 아니다

    Returns:
        중립 관계이면 True
    """
    if not target_faction:
        return False

    allowed = _NEUTRAL_FACTIONS.get(player_faction)
    return allowed is not None and target_faction in allowed


def get_disposition(player_faction: Optional[str], target_faction: Optional[str]) -> str:
    """플레이어 기준 대상의 상대 관계를 반환한다.

    판정 순서는 우호, 중립, 적대다. 우호와 중립에 모두 해당하는 경우
    우호가 우선한다.

    Args:
        player_faction: 플레이어 종족 ID. None 이면 기본 종족으로 간주한다
        target_faction: 대상 종족 ID

    Returns:
        `friendly`, `neutral`, `hostile` 중 하나
    """
    effective_player_faction = player_faction or DEFAULT_FACTION

    if is_friendly(effective_player_faction, target_faction):
        return FRIENDLY
    if is_neutral(effective_player_faction, target_faction):
        return NEUTRAL
    return HOSTILE
