# -*- coding: utf-8 -*-
"""채널 식별

서버는 게임(TCP 4000)과 어드민(TCP 4001) 두 채널을 연다. 프레이밍 규약이 같고
포트만 다르므로, 클라이언트가 잘못된 채널에 붙었을 때 조용히 실패하지 않도록
서버가 채널을 명시하고 타 채널 메시지를 사유와 함께 거절한다.

`welcome` 의 `channel` 이 1차 식별자다. 클라이언트는 접속 직후 이 값으로 자신이
어느 채널에 붙었는지 확인한다.

프로토콜 계약: docs/protocol/README.md, docs/protocol/admin.md
"""

CHANNEL_GAME = "game"
CHANNEL_ADMIN = "admin"

# 게임 채널 전용 클라이언트 메시지. 어드민 채널에서 받으면 거절한다
GAME_ONLY_TYPES = frozenset(
    {
        "login",
        "logout",
        "action",
        "chat",
        "client_info",
    }
)

# 어드민 채널 전용 클라이언트 메시지. 게임 채널에서 받으면 거절한다
ADMIN_ONLY_TYPES = frozenset(
    {
        "admin_login",
        "account_create",
        "admin_list",
        "admin_get",
        "admin_create",
        "admin_update",
        "admin_delete",
        "admin_stats",
        "admin_map",
        "admin_action",
    }
)

# 두 채널 모두에서 허용되는 메시지
SHARED_TYPES = frozenset({"ping"})


def wrong_channel_detail(message_type: str, actual_channel: str) -> str:
    """타 채널 메시지 수신 시의 개발자용 설명을 만든다.

    Args:
        message_type: 수신한 메시지 타입
        actual_channel: 이 연결이 붙어 있는 채널

    Returns:
        `detail` 에 담을 영문 설명
    """
    expected = CHANNEL_ADMIN if actual_channel == CHANNEL_GAME else CHANNEL_GAME
    return (
        f"{message_type} belongs to the {expected} channel; "
        f"this connection is the {actual_channel} channel"
    )
