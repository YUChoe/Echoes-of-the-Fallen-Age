# -*- coding: utf-8 -*-
"""어드민 실시간 액션 (`admin_action`)

계약이 규정한 14종을 처리한다. 플레이어와 방 레코드를 다루는 액션은 여기에,
세계 콘텐츠를 다루는 액션은 `world_actions.py` 에 있다.

어드민 채널은 게임 세션 상태를 바꾸는 유일한 경로다. `goto` 와 `kick` 은 대상
플레이어의 게임 세션이 있어야 하며 없으면 `PLAYER_NOT_ONLINE` 으로 거절한다.

프로토콜 계약: docs/protocol/admin.md
"""

import logging
from typing import Any, Awaitable, Callable, Optional

from ...database.table_gateway import TableGateway, TableGatewayError
from ...utils.exceptions import AdminOperationError
from ..serialization import admin_action_result
from . import audit
from .admin_session import AdminSession
from .resources import RESOURCES
from .world_actions import ActionError, WorldActions, optional_str

logger = logging.getLogger(__name__)

ActionImpl = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


class AdminActionHandlers:
    """`admin_action` 을 받아 14종 액션으로 보낸다."""

    def __init__(self, game_engine: Optional[Any] = None) -> None:
        self.game_engine = game_engine
        self._world: Optional[WorldActions] = None
        self._players: Optional[TableGateway] = None

    def register_all(self, server: Any) -> None:
        """어드민 서버에 처리기를 등록한다."""
        server.register("admin_action", self.handle)

    async def handle(self, session: AdminSession, message: dict[str, Any]) -> None:
        """`admin_action` 한 건을 처리한다."""
        seq = message.get("seq")
        action = message.get("action")
        params = message.get("params")

        if not isinstance(action, str) or not action:
            await session.send_rejected(
                "admin_action", "INVALID_PARAMS", "action must be a string", seq
            )
            return

        if params is not None and not isinstance(params, dict):
            await self._deny(
                session, action, {}, "INVALID_PARAMS", "params must be an object", seq
            )
            return

        params = params or {}

        if self.game_engine is None:
            await self._deny(
                session, action, params, "INTERNAL_ERROR",
                "game engine not initialised", seq,
            )
            return

        impl = self._resolve(action, session)

        if impl is None:
            await self._deny(
                session, action, params, "NOT_APPLICABLE",
                f"unknown action: {action}", seq,
            )
            return

        try:
            data = await impl(params)
        except AdminOperationError as e:
            # `ActionError` 와 `AdminManager` 의 실패가 같은 계열이다
            await self._deny(session, action, params, e.reason_code, e.detail, seq)
            return
        except TableGatewayError as e:
            await self._deny(
                session, action, params, "VALIDATION_FAILED", str(e), seq
            )
            return
        except Exception as e:
            logger.error(f"어드민 액션 실패: {action}: {e}", exc_info=True)
            await self._deny(session, action, params, "INTERNAL_ERROR", str(e), seq)
            return

        audit.record(
            actor=_actor(session), operation=action, changes=params
        )

        await session.send_message(admin_action_result(seq, action, True, data))

    @staticmethod
    async def _deny(
        session: AdminSession,
        action: str,
        params: dict[str, Any],
        reason_code: str,
        detail: str,
        seq: Optional[int],
    ) -> None:
        """액션을 거절하고 감사 로그에 남긴다.

        무엇을 시도했는지도 감사 대상이다.
        """
        audit.record(
            actor=_actor(session),
            operation=action,
            changes=params,
            result="rejected",
            reason_code=reason_code,
            detail=detail,
        )
        await session.send_rejected(action, reason_code, detail, seq)

    # 라우팅 ------------------------------------------------------------------

    def _resolve(self, action: str, session: AdminSession) -> Optional[ActionImpl]:
        """액션 이름을 구현으로 바꾼다."""
        world = self._world_actions(_actor(session))

        table: dict[str, ActionImpl] = {
            "goto": self._goto,
            "kick": lambda params: self._kick(session, params),
            "change_display_name": self._change_display_name,
            "create_room": lambda params: self._create_room(session, params),
            "update_room": lambda params: self._update_room(session, params),
            "validate_world": self._validate_world,
            "spawn_monster": world.spawn_monster,
            "spawn_item": world.spawn_item,
            "terminate": world.terminate,
            "create_exit": world.create_exit,
            "room_info": world.room_info,
            "list_monster_templates": _sync(world.list_monster_templates),
            "list_item_templates": _sync(world.list_item_templates),
            "scheduler": _sync(world.scheduler),
        }

        return table.get(action)

    def _world_actions(self, actor: str = "unknown") -> WorldActions:
        """세계 콘텐츠 액션 구현을 만들어 재사용한다.

        실행 주체는 요청마다 달라질 수 있으므로 매번 갱신한다.
        """
        if self._world is None:
            self._world = WorldActions(self.game_engine, actor)
        else:
            self._world.actor = actor
        return self._world

    def _player_gateway(self) -> TableGateway:
        """`players` 테이블 게이트웨이"""
        if self._players is None:
            resource = RESOURCES["players"]
            self._players = TableGateway(
                self.game_engine.db_manager, resource.table, resource.primary_key
            )
        return self._players

    def _find_game_session(self, username: str) -> Any:
        """대상 플레이어의 게임 세션을 찾는다.

        Raises:
            ActionError: 접속 중이 아닌 경우
        """
        sessions = self.game_engine.session_manager.get_authenticated_sessions()

        for session in sessions:
            if session.player and session.player.username == username:
                return session

        raise ActionError("PLAYER_NOT_ONLINE", f"player not online: {username}")

    # 액션 --------------------------------------------------------------------

    async def _goto(self, params: dict[str, Any]) -> dict[str, Any]:
        """대상 플레이어를 좌표로 이동시킨다."""
        username = _require_str(params, "target_player")
        target = self._find_game_session(username)

        world = self._world_actions()
        room = await world.room_at(_require_int(params, "x"), _require_int(params, "y"))

        moved = await self.game_engine.movement_manager.move_player_to_room(
            target, room.id
        )

        if not moved:
            raise ActionError("INTERNAL_ERROR", f"move failed: {username}")

        return {"target_player": username, "room_id": room.id}

    async def _kick(
        self, session: AdminSession, params: dict[str, Any]
    ) -> dict[str, Any]:
        """대상 플레이어를 서버에서 추방한다."""
        username = _require_str(params, "target_player")
        reason = optional_str(params, "reason", "관리자에 의해 추방")

        return await self.game_engine.admin_manager.kick_player(
            username, _actor(session), reason
        )

    async def _change_display_name(self, params: dict[str, Any]) -> dict[str, Any]:
        """대상 플레이어의 표시 이름을 바꾼다.

        접속 중이 아니어도 된다. DB 값을 바꾸는 작업이다.
        """
        username = _require_str(params, "target_player")
        display_name = _require_str(params, "display_name")

        gateway = self._player_gateway()
        rows = await gateway.list_rows(filters={"username": username}, limit=1)

        if not rows:
            raise ActionError("NOT_FOUND", f"player not found: {username}")

        updated = await gateway.update_row(
            {"id": rows[0]["id"]}, {"display_name": display_name}
        )

        if updated is None:
            raise ActionError("INTERNAL_ERROR", f"update failed: {username}")

        return {"target_player": username, "display_name": display_name}

    async def _create_room(
        self, session: AdminSession, params: dict[str, Any]
    ) -> dict[str, Any]:
        """방을 만든다. `AdminManager` 에 위임한다."""
        room_data = {
            "x": _require_int(params, "x"),
            "y": _require_int(params, "y"),
            "room_type": optional_str(params, "room_type", "unknown"),
            "description_en": optional_str(params, "description_en"),
            "description_ko": optional_str(params, "description_ko"),
        }

        return await self.game_engine.admin_manager.create_room_realtime(
            room_data, _actor(session)
        )

    async def _update_room(
        self, session: AdminSession, params: dict[str, Any]
    ) -> dict[str, Any]:
        """방을 수정한다. `AdminManager` 에 위임한다."""
        room_id = _require_str(params, "id")
        updates = params.get("values")

        if not isinstance(updates, dict) or not updates:
            raise ActionError(
                "VALIDATION_FAILED", "params.values must be a non-empty object"
            )

        return await self.game_engine.admin_manager.update_room_realtime(
            room_id, dict(updates), _actor(session)
        )

    async def _validate_world(self, _params: dict[str, Any]) -> dict[str, Any]:
        """세계 무결성을 검증하고 자동 수정한다.

        기존에 명령어로 노출되지 않았던 기능이다.
        """
        return await self.game_engine.admin_manager.validate_and_repair_world()

def _actor(session: AdminSession) -> str:
    """실행 주체 이름. `AdminManager` 의 로그와 이벤트에 남는다."""
    return session.principal.name if session.principal else "unknown"


def _sync(impl: Callable[[dict[str, Any]], dict[str, Any]]) -> ActionImpl:
    """동기 구현을 비동기 시그니처에 맞춘다."""

    async def wrapper(params: dict[str, Any]) -> dict[str, Any]:
        return impl(params)

    return wrapper


def _require_str(params: dict[str, Any], name: str) -> str:
    """문자열 파라미터를 얻는다."""
    value = params.get(name)

    if not isinstance(value, str) or not value:
        raise ActionError("INVALID_PARAMS", f"params.{name} must be a non-empty string")

    return value


def _require_int(params: dict[str, Any], name: str) -> int:
    """정수 파라미터를 얻는다."""
    value = params.get(name)

    if isinstance(value, bool) or not isinstance(value, int):
        raise ActionError("INVALID_PARAMS", f"params.{name} must be an integer")

    return value
