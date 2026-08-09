# -*- coding: utf-8 -*-
"""사교 페이로드 직렬화

접속자 목록과 채팅 메시지를 만든다. 좌표는 담지 않는다. 플레이어 위치를 다른
플레이어에게 노출하지 않기 위한 조치다.

프로토콜 계약: docs/protocol/server-to-client.md
"""

from datetime import datetime
from typing import Any, Iterable, Optional

from ...game.models.player import Player


def serialize_player_summary(player: Player) -> dict[str, Any]:
    """접속자 목록 항목을 만든다."""
    return {
        "id": str(player.id),
        "username": str(player.username),
        "display_name": player.get_display_name(),
        "faction_id": player.faction_id,
        # SQLite 는 boolean 을 정수로 저장하므로 계약대로 bool 로 맞춘다
        "is_admin": bool(player.is_admin),
    }


def build_who_result(
    players: Iterable[Player], seq: Optional[int] = None
) -> dict[str, Any]:
    """who_result 메시지를 만든다.

    `whisper` 대상 uuid 를 확보하는 경로다.
    """
    from .envelope import build

    return build(
        "who_result",
        seq=seq,
        players=[serialize_player_summary(player) for player in players],
    )


def build_chat(
    channel: str,
    sender: Player,
    message: str,
    seq: Optional[int] = None,
) -> dict[str, Any]:
    """chat 메시지를 만든다.

    채팅 본문은 번역하지 않는다. 사용자가 입력한 문장을 그대로 전달한다.

    Args:
        channel: `room` 또는 `whisper`
        sender: 발신 플레이어
        message: 본문
        seq: 발신자에게 되돌려 줄 때의 요청 번호
    """
    from .envelope import build

    return build(
        "chat",
        seq=seq,
        channel=str(channel),
        **{
            "from": {
                "id": str(sender.id),
                "display_name": sender.get_display_name(),
            }
        },
        message=str(message),
        timestamp=datetime.now().isoformat(),
    )
