# -*- coding: utf-8 -*-
"""계정 액션

표시 이름 변경을 담당한다. 계정 생성은 로그인 전 경로인 `register` 가 맡는다.
"""

import logging
from datetime import datetime

from ..base import ActionHandler
from ..context import ActionContext, ActionResult, error, rejected, success
from ...game.models.player import Player

logger = logging.getLogger(__name__)

# 이름 변경 제한 주기 (시간)
NAME_CHANGE_COOLDOWN_HOURS = 24.0

# 사용할 수 없는 표시 이름
RESERVED_DISPLAY_NAMES = frozenset({"SUPERADMIN"})


class ChangeNameHandler(ActionHandler):
    """표시 이름 변경. 관리자를 제외하고 하루 한 번이다."""

    verb = "changename"

    async def handle(self, ctx: ActionContext) -> ActionResult:
        player = ctx.session.player
        if player is None:
            return rejected("NOT_AUTHENTICATED")

        new_name = ctx.params.get("display_name")
        if not isinstance(new_name, str):
            return rejected(
                "INVALID_PARAMS", message="params.display_name must be a string"
            )

        new_name = new_name.strip()

        # 기존 구현의 조건이 뒤집혀 있었다:
        #   `not is_valid(...) or not "SUPERADMIN" == new_name`
        # 이는 SUPERADMIN 외의 모든 이름을 거절해 기능이 동작하지 않았다.
        if not Player.is_valid_display_name(new_name):
            return rejected("INVALID_PARAMS", message="Invalid display name")

        if new_name in RESERVED_DISPLAY_NAMES:
            return rejected("PERMISSION_DENIED", message="Reserved display name")

        if not player.is_admin and not player.can_change_name():
            hours_left = self._hours_until_next_change(player)
            # message_key 가 없으면 action_rejected 가 params 를 싣지 않는다.
            # 계약(entities.md)이 COOLDOWN 에 잔여 시간을 담도록 정하므로 키를
            # 함께 준다.
            return rejected(
                "COOLDOWN",
                message_key="account.name_change_cooldown",
                params={"hours_left": round(hours_left, 1)},
                message="Name can be changed once per day",
            )

        old_name = player.get_display_name()

        player.display_name = new_name
        if not player.is_admin:
            player.last_name_change = datetime.now()

        try:
            # 매니저를 거쳐 저장한다. 기존 구현은 PlayerRepository 를 직접 잡았다.
            await ctx.game_engine.player_manager.save_player(player)
        except Exception as e:
            logger.error(f"이름 변경 저장 실패 ({player.id}): {e}", exc_info=True)
            player.display_name = old_name
            return error(message="Failed to save display name")

        logger.info(
            f"표시 이름 변경: {player.username} '{old_name}' -> '{new_name}'"
        )

        return success(
            message_key="account.name_changed",
            params={"old_name": old_name, "new_name": new_name},
            data={"display_name": new_name},
        )

    def _hours_until_next_change(self, player: Player) -> float:
        """다음 변경까지 남은 시간을 계산한다."""
        if not player.last_name_change:
            return 0.0

        elapsed = (datetime.now() - player.last_name_change).total_seconds() / 3600
        return max(0.0, NAME_CHANGE_COOLDOWN_HOURS - elapsed)


def handlers() -> list[ActionHandler]:
    """이 카테고리의 핸들러 목록"""
    return [ChangeNameHandler()]
