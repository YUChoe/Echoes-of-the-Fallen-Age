"""Lua 스크립트에 전달할 읽기 전용 컨텍스트 빌더"""

from __future__ import annotations

import logging
from typing import Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .models.player import Player
    from .models.gameobject import GameObject
    from ..server.telnet_session import TelnetSession
    from .monster import Monster
    from .dialogue import DialogueInstance
    from .managers.currency_manager import CurrencyManager
    from .game_object_repository import GameObjectRepository

logger = logging.getLogger(__name__)

# silver_coin 템플릿 ID (인벤토리 목록에서 제외 대상)
_SILVER_TEMPLATE_ID = "silver_coin"


class DialogueContext:
    """Lua 스크립트에 전달할 읽기 전용 컨텍스트 빌더

    Python 객체 참조를 전달하지 않고 순수 dict로 변환하여
    Lua 측에서 Python 내부 상태를 변경할 수 없게 한다.
    """

    @staticmethod
    def build(
        player: Player,
        session: TelnetSession,
        npc: Monster,
        dialogue: DialogueInstance,
        *,
        exchange_data: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Player, Session, Monster, DialogueInstance 정보를 순수 dict로 변환.

        Args:
            player: 플레이어 모델
            session: Telnet 세션
            npc: NPC/몬스터 모델
            dialogue: 대화 인스턴스
            exchange_data: 교환 관련 사전 조회 데이터 (Optional).
                {
                    "player_silver": int,
                    "player_inventory": list[GameObject],
                    "player_weight_limit": float,
                    "npc_silver": int,
                    "npc_inventory": list[GameObject],
                }

        Returns:
            순수 dict 컨텍스트 (Python 객체 참조 없음)
        """
        ctx: dict[str, Any] = {
            "player": DialogueContext._build_player_context(
                player, exchange_data=exchange_data,
            ),
            "session": DialogueContext._build_session_context(session),
            "npc": DialogueContext._build_npc_context(
                npc, exchange_data=exchange_data,
            ),
            "dialogue": DialogueContext._build_dialogue_context(dialogue),
        }
        logger.debug(f"DialogueContext 빌드 완료: dialogue_id={dialogue.id}")
        return ctx

    @staticmethod
    async def build_with_exchange(
        player: Player,
        session: TelnetSession,
        npc: Monster,
        dialogue: DialogueInstance,
        currency_manager: CurrencyManager,
        object_repo: GameObjectRepository,
    ) -> dict[str, Any]:
        """교환 정보를 포함한 컨텍스트 빌드 (비동기).

        CurrencyManager와 GameObjectRepository를 사용하여
        실버 잔액, 인벤토리 목록을 조회한 뒤 build()에 전달한다.
        """
        exchange_data = await DialogueContext._fetch_exchange_data(
            player_id=player.id,
            npc_id=npc.id,
            player=player,
            currency_manager=currency_manager,
            object_repo=object_repo,
        )
        return DialogueContext.build(
            player=player,
            session=session,
            npc=npc,
            dialogue=dialogue,
            exchange_data=exchange_data,
        )

    @staticmethod
    async def _fetch_exchange_data(
        player_id: str,
        npc_id: str,
        player: Player,
        currency_manager: CurrencyManager,
        object_repo: GameObjectRepository,
    ) -> dict[str, Any]:
        """교환에 필요한 데이터를 비동기로 조회.

        Returns:
            {
                "player_silver": int,
                "player_inventory": list[GameObject],  # silver_coin 제외
                "player_weight_limit": float,
                "npc_silver": int,
                "npc_inventory": list[GameObject],  # silver_coin 제외
            }
        """
        # 실버 잔액 조회
        player_silver = await currency_manager.get_balance(player_id)
        npc_silver = await currency_manager.get_balance(npc_id)

        # 인벤토리 조회 (silver_coin 제외)
        player_all = await object_repo.get_objects_in_inventory(player_id)
        npc_all = await object_repo.get_objects_in_inventory(npc_id)

        player_inventory = [
            obj for obj in player_all
            if obj.properties.get("template_id") != _SILVER_TEMPLATE_ID
        ]
        npc_inventory = [
            obj for obj in npc_all
            if obj.properties.get("template_id") != _SILVER_TEMPLATE_ID
        ]

        # 무게 제한 (carry_weight는 silver_coin 포함 전체 무게)
        carry_weight = sum(obj.weight for obj in player_all)
        weight_limit = player.get_max_carry_weight()

        return {
            "player_silver": player_silver,
            "player_inventory": player_inventory,
            "player_carry_weight": carry_weight,
            "player_weight_limit": weight_limit,
            "npc_silver": npc_silver,
            "npc_inventory": npc_inventory,
        }

    @staticmethod
    def _build_player_context(
        player: Player,
        *,
        exchange_data: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """플레이어 정보를 순수 dict로 변환"""
        # quest_progress가 JSON 문자열일 수 있으므로 안전하게 변환
        quest_progress = player.quest_progress
        if isinstance(quest_progress, str):
            import json
            try:
                quest_progress = json.loads(quest_progress)
            except (json.JSONDecodeError, TypeError):
                quest_progress = {}

        completed_quests = player.completed_quests
        if isinstance(completed_quests, str):
            import json
            try:
                completed_quests = json.loads(completed_quests)
            except (json.JSONDecodeError, TypeError):
                completed_quests = []

        result: dict[str, Any] = {
            "id": str(player.id),
            "username": str(player.username),
            "display_name": str(player.get_display_name()),
            "preferred_locale": str(player.preferred_locale),
            "completed_quests": list(completed_quests) if isinstance(completed_quests, list) else [],
            "quest_progress": dict(quest_progress) if isinstance(quest_progress, dict) else {},
        }

        # 교환 정보 추가 (exchange_data가 제공된 경우)
        if exchange_data is not None:
            inventory_objects: List[GameObject] = exchange_data.get(
                "player_inventory", [],
            )
            result["silver"] = int(exchange_data.get("player_silver", 0))
            result["carry_weight"] = float(
                exchange_data.get("player_carry_weight", 0.0),
            )
            result["weight_limit"] = float(
                exchange_data.get("player_weight_limit", 10.0),
            )
            result["inventory"] = [
                _build_item_dict(obj) for obj in inventory_objects
            ]

        return result

    @staticmethod
    def _build_session_context(session: TelnetSession) -> dict[str, Any]:
        """세션 정보를 순수 dict로 변환"""
        return {
            "session_id": str(session.session_id),
            "locale": str(session.locale),
            "current_room_id": str(session.current_room_id or ""),
            "stamina": float(session.stamina),
        }

    @staticmethod
    def _build_npc_context(
        npc: Monster,
        *,
        exchange_data: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """NPC/몬스터 정보를 순수 dict로 변환"""
        # name은 이미 dict[str, str] 형태 ({"en": ..., "ko": ...})
        name_copy: dict[str, str] = {}
        if isinstance(npc.name, dict):
            name_copy = {str(k): str(v) for k, v in npc.name.items()}

        # properties 깊은 복사 (순수 dict)
        props_copy: dict[str, Any] = {}
        if isinstance(npc.properties, dict):
            props_copy = _deep_copy_dict(npc.properties)

        result: dict[str, Any] = {
            "id": str(npc.id),
            "name": name_copy,
            "properties": props_copy,
        }

        # 교환 정보 추가 (exchange_data가 제공된 경우)
        if exchange_data is not None:
            npc_inventory: List[GameObject] = exchange_data.get(
                "npc_inventory", [],
            )
            result["silver"] = int(exchange_data.get("npc_silver", 0))
            result["inventory"] = [
                _build_item_dict(obj) for obj in npc_inventory
            ]

        return result

    @staticmethod
    def _build_dialogue_context(dialogue: DialogueInstance) -> dict[str, Any]:
        """대화 인스턴스 정보를 순수 dict로 변환"""
        # choice_entity를 순수 dict로 변환
        choice_copy: dict[int, Any] = {}
        if isinstance(dialogue.choice_entity, dict):
            for k, v in dialogue.choice_entity.items():
                if isinstance(v, dict):
                    choice_copy[int(k)] = {str(dk): str(dv) for dk, dv in v.items()}
                else:
                    choice_copy[int(k)] = str(v)

        return {
            "id": str(dialogue.id),
            "is_active": bool(dialogue.is_active),
            "choice_entity": choice_copy,
            "started_at": dialogue.started_at.isoformat(),
        }


def _build_item_dict(obj: GameObject) -> dict[str, Any]:
    """GameObject를 교환용 순수 dict로 변환.

    silver_coin은 이 함수에 전달되기 전에 필터링되어야 한다.
    """
    # name 깊은 복사
    name_copy: dict[str, str] = {}
    if isinstance(obj.name, dict):
        name_copy = {str(k): str(v) for k, v in obj.name.items()}

    # properties 깊은 복사
    props_copy: dict[str, Any] = {}
    if isinstance(obj.properties, dict):
        props_copy = _deep_copy_dict(obj.properties)

    return {
        "id": str(obj.id),
        "name": name_copy,
        "category": str(obj.properties.get("category", "")),
        "weight": float(obj.weight),
        "is_equipped": bool(obj.is_equipped),
        "equipment_slot": str(obj.equipment_slot) if obj.equipment_slot else None,
        "properties": props_copy,
    }


def _deep_copy_dict(source: dict[str, Any]) -> dict[str, Any]:
    """dict를 재귀적으로 순수 dict/list/기본 타입으로 복사"""
    result: dict[str, Any] = {}
    for k, v in source.items():
        if isinstance(v, dict):
            result[str(k)] = _deep_copy_dict(v)
        elif isinstance(v, list):
            result[str(k)] = _deep_copy_list(v)
        elif isinstance(v, (str, int, float, bool)):
            result[str(k)] = v
        elif v is None:
            result[str(k)] = None
        else:
            # 알 수 없는 타입은 문자열로 변환
            result[str(k)] = str(v)
    return result


def _deep_copy_list(source: list[Any]) -> list[Any]:
    """list를 재귀적으로 순수 list/dict/기본 타입으로 복사"""
    result: list[Any] = []
    for item in source:
        if isinstance(item, dict):
            result.append(_deep_copy_dict(item))
        elif isinstance(item, list):
            result.append(_deep_copy_list(item))
        elif isinstance(item, (str, int, float, bool)):
            result.append(item)
        elif item is None:
            result.append(None)
        else:
            result.append(str(item))
    return result
