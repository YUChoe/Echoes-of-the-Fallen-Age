"""Lua 스크립트에 전달할 읽기 전용 컨텍스트 빌더"""

from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .models.player import Player
    from ..server.telnet_session import TelnetSession
    from .monster import Monster
    from .dialogue import DialogueInstance

logger = logging.getLogger(__name__)


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
    ) -> dict[str, Any]:
        """Player, Session, Monster, DialogueInstance 정보를 순수 dict로 변환.

        Args:
            player: 플레이어 모델
            session: Telnet 세션
            npc: NPC/몬스터 모델
            dialogue: 대화 인스턴스

        Returns:
            순수 dict 컨텍스트 (Python 객체 참조 없음)
        """
        ctx: dict[str, Any] = {
            "player": DialogueContext._build_player_context(player),
            "session": DialogueContext._build_session_context(session),
            "npc": DialogueContext._build_npc_context(npc),
            "dialogue": DialogueContext._build_dialogue_context(dialogue),
        }
        logger.debug(f"DialogueContext 빌드 완료: dialogue_id={dialogue.id}")
        return ctx

    @staticmethod
    def _build_player_context(player: Player) -> dict[str, Any]:
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

        return {
            "username": str(player.username),
            "display_name": str(player.get_display_name()),
            "preferred_locale": str(player.preferred_locale),
            "completed_quests": list(completed_quests) if isinstance(completed_quests, list) else [],
            "quest_progress": dict(quest_progress) if isinstance(quest_progress, dict) else {},
        }

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
    def _build_npc_context(npc: Monster) -> dict[str, Any]:
        """NPC/몬스터 정보를 순수 dict로 변환"""
        # name은 이미 dict[str, str] 형태 ({"en": ..., "ko": ...})
        name_copy: dict[str, str] = {}
        if isinstance(npc.name, dict):
            name_copy = {str(k): str(v) for k, v in npc.name.items()}

        # properties 깊은 복사 (순수 dict)
        props_copy: dict[str, Any] = {}
        if isinstance(npc.properties, dict):
            props_copy = _deep_copy_dict(npc.properties)

        return {
            "id": str(npc.id),
            "name": name_copy,
            "properties": props_copy,
        }

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
