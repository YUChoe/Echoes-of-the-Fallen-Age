# -*- coding: utf-8 -*-
"""사교 액션

따라가기, 감정 표현, 접속자 조회를 담당한다. 대상은 uuid 로 지정되므로 이름
매칭이 없다.
"""

import logging
from typing import Any, Optional

from ..base import ActionHandler
from ..context import (
    ActionContext,
    ActionResult,
    BroadcastSpec,
    rejected,
    success,
)
from ..resolver import EntityKind
from ...core.event_bus import Event, EventType
from ...server.serialization import build_who_result

logger = logging.getLogger(__name__)

# 선택 가능한 감정 표현. 계약이 목록에서 고르도록 규정하므로 자유 입력을 받지 않는다.
EMOTE_IDS = (
    # action
    "wave",
    "bow",
    "nod",
    "shake_head",
    "smile",
    "laugh",
    "cry",
    "sigh",
    "shrug",
    "clap",
    "dance",
    "salute",
    # report
    "path_cleared",
    "enemy_weakened",
    "all_clear",
    "incoming",
    "fire_set",
    "holding",
    "advancing",
    "under_attack",
    "traps_cleared",
    "enemy_disguised",
    # request
    "need_healing",
    "need_arrows",
    "need_help",
    "need_smith",
    "cover_me",
    "hold",
    "where_to",
    "need_scout",
    # order
    "follow_me",
    "lets_go",
    "make_way",
    "clear_path",
    "defend_here",
    "disarm_trap",
    "reinforce_attack",
    "reinforce_defence",
    # reply
    "yes",
    "no",
    "thanks",
    "welcome",
    "sorry",
    "oops",
    "hail",
    "farewell",
    "well_struck",
    "cheer",
    "well_fought",
    "acknowledged",
    "declined",
    "done",
    # role
    "i_will_fight",
    "i_will_heal",
    "i_will_scout",
    "i_will_carry",
)


class FollowHandler(ActionHandler):
    """다른 플레이어 따라가기"""

    verb = "follow"
    requires_target = True
    forbidden_in_combat = True

    async def handle(self, ctx: ActionContext) -> ActionResult:
        resolved = ctx.entity
        if resolved is None or resolved.kind is not EntityKind.PLAYER:
            return rejected("NOT_APPLICABLE", message="Target is not a player")

        target = resolved.entity

        if ctx.player_id == target.id:
            return rejected("NOT_APPLICABLE", message="Cannot follow yourself")

        # 대상 uuid 를 저장한다. 기존 구현은 username 을 저장해 이름 변경에
        # 취약했고 uuid 규약과도 어긋났다.
        ctx.session.following_player = target.id

        await self._publish_follow(ctx, target)
        await self._notify_target(ctx, target)

        return success(
            message_key="follow.started",
            params={"target": target.get_display_name()},
            broadcast=BroadcastSpec(
                message_key="follow.broadcast",
                params={
                    "username": ctx.session.player.get_display_name()
                    if ctx.session.player
                    else "",
                    "target": target.get_display_name(),
                },
                category="social",
            ),
            data={"following": target.id},
        )

    async def _publish_follow(self, ctx: ActionContext, target: Any) -> None:
        """따라가기 이벤트를 발행한다."""
        if not ctx.game_engine.event_bus or not ctx.session.player:
            return

        await ctx.game_engine.event_bus.publish(
            Event(
                event_type=EventType.PLAYER_FOLLOW,
                source=ctx.session.session_id,
                room_id=ctx.room_id,
                data={
                    "follower_id": ctx.session.player.id,
                    "follower_name": ctx.session.player.username,
                    "target_id": target.id,
                    "target_name": target.username,
                },
            )
        )

    async def _notify_target(self, ctx: ActionContext, target: Any) -> None:
        """따라가기 대상에게 알린다."""
        session = _find_session_by_player(ctx, target.id)
        if session is None:
            return

        display_name = (
            ctx.session.player.get_display_name() if ctx.session.player else ""
        )

        await session.send_message(
            {
                "type": "event",
                "category": "social",
                "message": {
                    "key": "follow.being_followed",
                    "params": {"username": display_name},
                },
            }
        )


class UnfollowHandler(ActionHandler):
    """따라가기 중단"""

    verb = "unfollow"

    async def handle(self, ctx: ActionContext) -> ActionResult:
        following = getattr(ctx.session, "following_player", None)

        if not following:
            return rejected("WRONG_STATE", message="Not following anyone")

        # 기존 구현은 delattr 을 썼는데 following_player 가 프로퍼티라
        # AttributeError 가 났다.
        ctx.session.following_player = None

        return success(
            message_key="follow.stopped",
            data={"was_following": following},
        )


class EmoteHandler(ActionHandler):
    """감정 표현

    자유 입력을 받지 않는다. 클라이언트가 목록에서 고른 id 를 보내고 문장은
    클라이언트가 번역한다.
    """

    verb = "emote"

    async def handle(self, ctx: ActionContext) -> ActionResult:
        emote_id = ctx.params.get("emote_id")

        if not isinstance(emote_id, str) or emote_id not in EMOTE_IDS:
            return rejected(
                "INVALID_PARAMS",
                params={"available": list(EMOTE_IDS)},
                message="emote_id must be one of the defined emotes",
            )

        if ctx.session.player is None:
            return rejected("NOT_AUTHENTICATED")

        display_name = ctx.session.player.get_display_name()

        if ctx.game_engine.event_bus:
            await ctx.game_engine.event_bus.publish(
                Event(
                    event_type=EventType.PLAYER_EMOTE,
                    source=ctx.session.session_id,
                    room_id=ctx.room_id,
                    data={
                        "player_id": ctx.session.player.id,
                        "username": ctx.session.player.username,
                        "emote_id": emote_id,
                        "session_id": ctx.session.session_id,
                    },
                )
            )

        return success(
            message_key=f"emote.{emote_id}.self",
            broadcast=BroadcastSpec(
                message_key=f"emote.{emote_id}.other",
                params={"username": display_name},
                category="social",
            ),
            data={"emote_id": emote_id},
        )


class WhoHandler(ActionHandler):
    """접속자 목록"""

    verb = "who"

    async def handle(self, ctx: ActionContext) -> ActionResult:
        players = [
            session.player
            for session in ctx.game_engine.session_manager.get_authenticated_sessions()
            if session.player
        ]

        await ctx.session.send_message(build_who_result(players, seq=ctx.seq))

        return success(data={"count": len(players)})


class PlayersHereHandler(ActionHandler):
    """같은 방 플레이어 목록

    `who_result` 를 방 범위로 좁혀 응답한다. 필요한 데이터가 접속자 목록과
    같아서 별도 메시지 타입을 만들지 않는다.
    """

    verb = "players_here"

    async def handle(self, ctx: ActionContext) -> ActionResult:
        if not ctx.room_id:
            return rejected("WRONG_STATE", message="No current room")

        players = [
            session.player
            for session in ctx.game_engine.session_manager.get_authenticated_sessions()
            if session.player
            and getattr(session, "current_room_id", None) == ctx.room_id
        ]

        await ctx.session.send_message(build_who_result(players, seq=ctx.seq))

        return success(data={"count": len(players)})


def _find_session_by_player(ctx: ActionContext, player_id: str) -> Optional[Any]:
    """플레이어 id 로 세션을 찾는다."""
    for session in ctx.game_engine.session_manager.get_authenticated_sessions():
        if session.player and session.player.id == player_id:
            return session
    return None


def handlers() -> list[ActionHandler]:
    """이 카테고리의 핸들러 목록"""
    return [
        FollowHandler(),
        UnfollowHandler(),
        EmoteHandler(),
        WhoHandler(),
        PlayersHereHandler(),
    ]
