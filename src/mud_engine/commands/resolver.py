# -*- coding: utf-8 -*-
"""대상 uuid 해석

클라이언트는 대상을 uuid 로 지정한다. 세션에 번호 맵을 유지하지 않으므로 요청마다
현재 컨텍스트를 조회해 uuid 가 실제로 접근 가능한 대상인지 확인한다.

접근 가능 범위를 벗어난 uuid 를 거절하는 것이 이 모듈의 핵심 책임이다. uuid 는
전역 고유하므로 단순 조회만 하면 다른 방의 엔티티도 조작할 수 있다.

프로토콜 계약: docs/protocol/entities.md
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

from ..core.types import SessionType
from ..server.serialization import is_container

if TYPE_CHECKING:
    from ..core.game_engine import GameEngine

logger = logging.getLogger(__name__)


class EntityKind(Enum):
    """해석된 대상의 종류"""

    MONSTER = "monster"
    OBJECT = "object"
    PLAYER = "player"
    COMBATANT = "combatant"


@dataclass
class ResolvedEntity:
    """해석 결과

    Attributes:
        kind: 대상 종류
        entity: 모델 인스턴스
        source: 찾은 위치. 핸들러가 소유 판정에 쓴다
            (combat/room/inventory/equipped/container/room_players)
        container_id: container 에서 찾은 경우 그 컨테이너 uuid
    """

    kind: EntityKind
    entity: Any
    source: str
    container_id: Optional[str] = None


class EntityResolver:
    """현재 컨텍스트에서 uuid 를 해석한다."""

    def __init__(self, game_engine: "GameEngine") -> None:
        self.game_engine = game_engine

    async def resolve(
        self, session: SessionType, target_id: str
    ) -> Optional[ResolvedEntity]:
        """uuid 를 현재 접근 가능한 대상으로 해석한다.

        탐색 순서는 좁은 범위부터다. 전투 중이면 참가자를 먼저 보고, 그 다음
        방, 인벤토리, 컨테이너, 같은 방 플레이어를 본다.

        Args:
            session: 요청한 세션
            target_id: 대상 uuid

        Returns:
            해석 결과. 접근 가능 범위에 없으면 None
        """
        if not target_id:
            return None

        # 1. 전투 참가자
        found = self._resolve_combatant(session, target_id)
        if found:
            return found

        room_id = getattr(session, "current_room_id", None)

        # 2. 현재 방의 몬스터
        if room_id:
            found = await self._resolve_room_monster(room_id, target_id)
            if found:
                return found

        # 3. 현재 방의 오브젝트
        if room_id:
            found = await self._resolve_room_object(room_id, target_id)
            if found:
                return found

        # 4. 플레이어 인벤토리와 장착 아이템
        if session.player:
            found = await self._resolve_inventory_object(session.player.id, target_id)
            if found:
                return found

        # 5. 접근 가능한 컨테이너 내부
        found = await self._resolve_container_item(session, room_id, target_id)
        if found:
            return found

        # 6. 같은 방의 플레이어
        if room_id:
            found = self._resolve_room_player(room_id, target_id)
            if found:
                return found

        logger.debug(f"대상 해석 실패: {target_id[-12:]} (방 {room_id})")
        return None

    # 단계별 해석 ------------------------------------------------------------

    def _resolve_combatant(
        self, session: SessionType, target_id: str
    ) -> Optional[ResolvedEntity]:
        """전투 참가자에서 찾는다."""
        if not getattr(session, "in_combat", False):
            return None

        combat_id = getattr(session, "combat_id", None)
        if not combat_id:
            return None

        combat = self.game_engine.combat_manager.get_combat(combat_id)
        if not combat:
            return None

        for combatant in combat.combatants:
            if combatant.id == target_id:
                return ResolvedEntity(
                    kind=EntityKind.COMBATANT, entity=combatant, source="combat"
                )

        return None

    async def _resolve_room_monster(
        self, room_id: str, target_id: str
    ) -> Optional[ResolvedEntity]:
        """현재 방의 몬스터에서 찾는다."""
        monsters = await self.game_engine.world_manager.get_monsters_in_room(room_id)

        for monster in monsters:
            if monster.id == target_id:
                return ResolvedEntity(
                    kind=EntityKind.MONSTER, entity=monster, source="room"
                )

        return None

    async def _resolve_room_object(
        self, room_id: str, target_id: str
    ) -> Optional[ResolvedEntity]:
        """현재 방의 오브젝트에서 찾는다."""
        objects = await self.game_engine.world_manager.get_room_objects(room_id)

        for obj in objects:
            if obj.id == target_id:
                return ResolvedEntity(
                    kind=EntityKind.OBJECT, entity=obj, source="room"
                )

        return None

    async def _resolve_inventory_object(
        self, player_id: str, target_id: str
    ) -> Optional[ResolvedEntity]:
        """인벤토리와 장착 아이템에서 찾는다."""
        world = self.game_engine.world_manager

        for obj in await world.get_inventory_objects(player_id):
            if obj.id == target_id:
                return ResolvedEntity(
                    kind=EntityKind.OBJECT, entity=obj, source="inventory"
                )

        for obj in await world.get_equipped_objects(player_id):
            if obj.id == target_id:
                return ResolvedEntity(
                    kind=EntityKind.OBJECT, entity=obj, source="equipped"
                )

        return None

    async def _resolve_container_item(
        self, session: SessionType, room_id: Optional[str], target_id: str
    ) -> Optional[ResolvedEntity]:
        """접근 가능한 컨테이너 내부에서 찾는다.

        서버가 컨테이너의 열림 상태를 유지하지 않으므로, 방과 인벤토리에 있는
        컨테이너 전부를 접근 가능한 것으로 본다.
        """
        world = self.game_engine.world_manager
        containers: list[Any] = []

        if room_id:
            containers.extend(
                obj
                for obj in await world.get_room_objects(room_id)
                if is_container(obj.properties)
            )

        if session.player:
            containers.extend(
                obj
                for obj in await world.get_inventory_objects(session.player.id)
                if is_container(obj.properties)
            )

        for container in containers:
            for item in await world.get_container_items(container.id):
                if item.id == target_id:
                    return ResolvedEntity(
                        kind=EntityKind.OBJECT,
                        entity=item,
                        source="container",
                        container_id=container.id,
                    )

        return None

    def _resolve_room_player(
        self, room_id: str, target_id: str
    ) -> Optional[ResolvedEntity]:
        """같은 방의 플레이어에서 찾는다."""
        sessions = self.game_engine.session_manager.get_authenticated_sessions()

        for other in sessions:
            if (
                other.player
                and other.player.id == target_id
                and getattr(other, "current_room_id", None) == room_id
            ):
                return ResolvedEntity(
                    kind=EntityKind.PLAYER, entity=other.player, source="room_players"
                )

        return None
