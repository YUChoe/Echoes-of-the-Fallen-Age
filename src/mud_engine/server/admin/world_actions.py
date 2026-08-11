# -*- coding: utf-8 -*-
"""세계 콘텐츠를 다루는 어드민 액션

몬스터·아이템 생성, 삭제, 출구 개방, 방 조회, 템플릿 목록, 스케줄러를 담당한다.
플레이어와 방 레코드를 다루는 액션은 `actions.py` 에 있다.

프로토콜 계약: docs/protocol/admin.md
"""

import logging
import uuid
from typing import Any, Optional

from ...utils.exceptions import AdminOperationError

logger = logging.getLogger(__name__)

# 좌표 이동이 성립하는 방향과 좌표 증분
DIRECTION_OFFSETS: dict[str, tuple[int, int]] = {
    "north": (0, 1),
    "south": (0, -1),
    "east": (1, 0),
    "west": (-1, 0),
}


class ActionError(AdminOperationError):
    """액션 수행을 중단시키는 거절

    `AdminManager` 가 던지는 예외와 같은 계열이므로 처리기가 한 번에 잡는다.
    """


class WorldActions:
    """세계 콘텐츠 액션 구현"""

    def __init__(self, game_engine: Any, actor: str = "unknown") -> None:
        self._engine = game_engine
        # 실행 주체. `AdminManager` 의 로그와 세계 변경 이벤트에 남는다
        self.actor = actor

    # 위치 해석 ---------------------------------------------------------------

    async def room_at(self, x: int, y: int) -> Any:
        """좌표에 있는 방을 찾는다.

        좌표가 겹치는 방이 있을 수 있으므로 첫 번째를 쓴다.

        Raises:
            ActionError: 해당 좌표에 방이 없는 경우
        """
        rooms = await self._engine.world_manager.get_rooms_in_area(x, y, 0)
        exact = [room for room in rooms if room.x == x and room.y == y]

        if not exact:
            raise ActionError("NOT_FOUND", f"no room at ({x}, {y})")

        return exact[0]

    def _template_loader(self) -> Any:
        """몬스터·아이템 템플릿 로더"""
        return self._engine.world_manager._monster_manager._template_loader

    # 액션 --------------------------------------------------------------------

    async def spawn_monster(self, params: dict[str, Any]) -> dict[str, Any]:
        """템플릿으로 몬스터를 생성한다."""
        template_id = _require_str(params, "template_id")
        room = await self.room_at(_require_int(params, "x"), _require_int(params, "y"))

        if self._template_loader().get_monster_template(template_id) is None:
            raise ActionError("NOT_FOUND", f"template_id not found: {template_id}")

        monster_manager = self._engine.world_manager._monster_manager
        monster = await monster_manager._spawn_monster_from_template(
            room.id, template_id
        )

        if monster is None:
            raise ActionError("INTERNAL_ERROR", f"spawn failed: {template_id}")

        return {"monster_id": monster.id, "room_id": room.id}

    async def spawn_item(self, params: dict[str, Any]) -> dict[str, Any]:
        """템플릿으로 아이템을 방에 생성한다."""
        template_id = _require_str(params, "template_id")
        room = await self.room_at(_require_int(params, "x"), _require_int(params, "y"))

        loader = self._template_loader()

        if loader.get_item_template(template_id) is None:
            raise ActionError("NOT_FOUND", f"template_id not found: {template_id}")

        item = loader.create_item_from_template(
            template_id, str(uuid.uuid4()), "room", room.id
        )

        if item is None:
            raise ActionError("INTERNAL_ERROR", f"item build failed: {template_id}")

        await self._engine.model_manager.game_objects.create(item.to_dict())

        return {"object_id": item.id, "room_id": room.id}

    async def terminate(self, params: dict[str, Any]) -> dict[str, Any]:
        """몬스터나 오브젝트를 완전히 삭제한다.

        같은 uuid 공간을 쓰므로 몬스터를 먼저 찾고 없으면 오브젝트를 찾는다.
        """
        target_id = _require_str(params, "target_id")
        world = self._engine.world_manager

        monster = await world.get_monster(target_id)

        if monster is not None:
            if not await world.delete_monster(target_id):
                raise ActionError("INTERNAL_ERROR", f"monster delete failed: {target_id}")
            return {"target_id": target_id, "kind": "monster"}

        obj = await world.get_game_object(target_id)

        if obj is not None:
            if not await world.delete_game_object(target_id):
                raise ActionError("INTERNAL_ERROR", f"object delete failed: {target_id}")
            return {"target_id": target_id, "kind": "object"}

        raise ActionError("NOT_FOUND", f"no monster or object: {target_id}")

    async def create_exit(self, params: dict[str, Any]) -> dict[str, Any]:
        """방향 출구를 연다.

        이 세계의 방향 이동은 좌표로 결정된다. 출구를 만든다는 것은 인접 좌표의
        방을 새로 지정하는 것이 아니라 `blocked_exits` 에서 해당 방향을 빼는
        것이다. 삭제된 `createexit` 명령어는 `rooms` 에 없는 `exits` 컬럼을
        수정하려 해서 동작하지 않았다.
        """
        from_id = _require_str(params, "from_id")
        to_id = _require_str(params, "to_id")
        direction = _require_str(params, "direction").lower()

        if direction not in DIRECTION_OFFSETS:
            raise ActionError(
                "INVALID_PARAMS",
                f"direction must be one of {', '.join(sorted(DIRECTION_OFFSETS))}",
            )

        world = self._engine.world_manager
        from_room = await world.get_room(from_id)

        if from_room is None:
            raise ActionError("NOT_FOUND", f"room not found: {from_id}")

        if from_room.x is None or from_room.y is None:
            raise ActionError("WRONG_STATE", f"room has no coordinates: {from_id}")

        dx, dy = DIRECTION_OFFSETS[direction]
        target = await self.room_at(from_room.x + dx, from_room.y + dy)

        if target.id != to_id:
            raise ActionError(
                "VALIDATION_FAILED",
                f"{direction} of {from_id} is {target.id}, not {to_id}",
            )

        blocked = [item for item in (from_room.blocked_exits or []) if item != direction]

        if len(blocked) == len(from_room.blocked_exits or []):
            return {"from_id": from_id, "direction": direction, "changed": False}

        await self._engine.admin_manager.update_room_realtime(
            from_id, {"blocked_exits": blocked}, self.actor
        )

        return {"from_id": from_id, "direction": direction, "changed": True}

    async def room_info(self, params: dict[str, Any]) -> dict[str, Any]:
        """좌표의 방과 그 안의 몬스터·오브젝트를 조회한다."""
        room = await self.room_at(_require_int(params, "x"), _require_int(params, "y"))
        world = self._engine.world_manager

        monsters = await world.get_monsters_in_room(room.id)
        objects = await world.get_room_objects(room.id)

        return {
            "room": {
                "id": room.id,
                "x": room.x,
                "y": room.y,
                "room_type": room.room_type,
                "blocked_exits": list(room.blocked_exits or []),
            },
            # 어드민은 원본 구조를 보므로 언어별 dict 를 그대로 담는다
            "monsters": [
                {"id": monster.id, "name": dict(monster.name), "is_alive": monster.is_alive}
                for monster in monsters
            ],
            "objects": [{"id": obj.id, "name": dict(obj.name)} for obj in objects],
        }

    def list_monster_templates(self, _params: dict[str, Any]) -> dict[str, Any]:
        """몬스터 템플릿 목록"""
        templates = self._template_loader().get_all_monster_templates()
        return {"templates": sorted(templates)}

    def list_item_templates(self, _params: dict[str, Any]) -> dict[str, Any]:
        """아이템 템플릿 목록"""
        templates = self._template_loader().get_all_item_templates()
        return {"templates": sorted(templates)}

    def scheduler(self, params: dict[str, Any]) -> dict[str, Any]:
        """스케줄 이벤트를 조회하거나 켜고 끈다."""
        operation = _require_str(params, "operation").lower()

        if operation not in ("list", "info", "enable", "disable"):
            raise ActionError(
                "INVALID_PARAMS", "operation must be list, info, enable or disable"
            )

        manager = self._engine.scheduler_manager

        if operation == "list":
            return {"events": manager.list_events()}

        event_name = _require_str(params, "event_name")

        if operation == "info":
            info = manager.get_event_info(event_name)
            if info is None:
                raise ActionError("NOT_FOUND", f"event not found: {event_name}")
            return {"event": info}

        changed = (
            manager.enable_event(event_name)
            if operation == "enable"
            else manager.disable_event(event_name)
        )

        if not changed:
            raise ActionError("NOT_FOUND", f"event not found: {event_name}")

        return {"event_name": event_name, "operation": operation}


def _require_str(params: dict[str, Any], name: str) -> str:
    """문자열 파라미터를 얻는다.

    Raises:
        ActionError: 없거나 문자열이 아닌 경우
    """
    value = params.get(name)

    if not isinstance(value, str) or not value:
        raise ActionError("INVALID_PARAMS", f"params.{name} must be a non-empty string")

    return value


def _require_int(params: dict[str, Any], name: str) -> int:
    """정수 파라미터를 얻는다.

    bool 은 int 의 하위 타입이므로 명시적으로 배제한다.

    Raises:
        ActionError: 없거나 정수가 아닌 경우
    """
    value = params.get(name)

    if isinstance(value, bool) or not isinstance(value, int):
        raise ActionError("INVALID_PARAMS", f"params.{name} must be an integer")

    return value


def optional_str(params: dict[str, Any], name: str, default: str = "") -> str:
    """선택 문자열 파라미터를 얻는다. 없으면 기본값."""
    value: Optional[Any] = params.get(name)
    return value if isinstance(value, str) and value else default
