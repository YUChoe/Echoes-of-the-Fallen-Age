# -*- coding: utf-8 -*-
"""UI 관리자"""

import logging
from typing import TYPE_CHECKING, Dict, Any, List

from ..types import SessionType

if TYPE_CHECKING:
    from ..game_engine import GameEngine

logger = logging.getLogger(__name__)


class UIManager:
    """클라이언트 UI 업데이트를 담당하는 매니저"""

    def __init__(self, game_engine: 'GameEngine'):
        self.game_engine = game_engine

    async def send_ui_update(self, session: SessionType, room_info: Dict[str, Any]) -> None:
        """
        클라이언트에게 UI 업데이트 정보 전송

        Args:
            session: 세션 객체
            room_info: 방 정보
        """
        logger.debug(f"UI 업데이트 전송 시작: 플레이어={session.player.username if session.player else 'Unknown'}")

        try:
            # 출구 버튼 생성
            exit_buttons = []
            for direction, target_room_id in room_info['exits'].items():
                exit_buttons.append({
                    "type": "exit",
                    "text": self._get_direction_text(direction, session.locale),
                    "command": direction,
                    "icon": self._get_direction_icon(direction)
                })

            # 객체 버튼 생성
            object_buttons = []
            for obj in room_info['objects']:
                object_buttons.append({
                    "type": "object",
                    "text": obj.get_localized_name(session.locale),
                    "command": f"examine {obj.get_localized_name(session.locale)}",
                    "icon": self._get_object_icon(obj.object_type),
                    "actions": [
                        {"text": "조사하기", "command": f"examine {obj.get_localized_name(session.locale)}"},
                        {"text": "가져가기", "command": f"get {obj.get_localized_name(session.locale)}"}
                    ]
                })

            # 기본 액션 버튼들
            action_buttons = [
                {"type": "action", "text": "둘러보기", "command": "look", "icon": "👀"},
                {"type": "action", "text": "인벤토리", "command": "inventory", "icon": "🎒"},
                {"type": "action", "text": "접속자 목록", "command": "who", "icon": "👥"},
                {"type": "action", "text": "도움말", "command": "help", "icon": "❓"}
            ]

            # 자동완성 힌트 생성
            autocomplete_hints = self._generate_autocomplete_hints(session, room_info)

            ui_data = {
                "buttons": {
                    "exits": exit_buttons,
                    "objects": object_buttons,
                    "actions": action_buttons
                },
                "autocomplete": autocomplete_hints,
                "room_id": room_info['room'].id
            }

            await session.send_ui_update(ui_data)
            logger.debug(f"UI 업데이트 전송 완료: 플레이어={session.player.username if session.player else 'Unknown'}")

        except Exception as e:
            logger.error(f"UI 업데이트 전송 실패: {e}", exc_info=True)

    def _get_direction_text(self, direction: str, locale: str) -> str:
        """방향 텍스트 반환"""
        direction_texts = {
            'en': {
                'north': 'North', 'south': 'South', 'east': 'East', 'west': 'West',
                'up': 'Up', 'down': 'Down', 'northeast': 'Northeast', 'northwest': 'Northwest',
                'southeast': 'Southeast', 'southwest': 'Southwest'
            },
            'ko': {
                'north': '북쪽', 'south': '남쪽', 'east': '동쪽', 'west': '서쪽',
                'up': '위쪽', 'down': '아래쪽', 'northeast': '북동쪽', 'northwest': '북서쪽',
                'southeast': '남동쪽', 'southwest': '남서쪽'
            }
        }
        return direction_texts.get(locale, direction_texts['en']).get(direction, direction.title())

    def _get_direction_icon(self, direction: str) -> str:
        """방향 아이콘 반환"""
        icons = {
            'north': '⬆️', 'south': '⬇️', 'east': '➡️', 'west': '⬅️',
            'up': '🔼', 'down': '🔽', 'northeast': '↗️', 'northwest': '↖️',
            'southeast': '↘️', 'southwest': '↙️'
        }
        return icons.get(direction, '🚪')

    def _get_object_icon(self, object_type: str) -> str:
        """객체 타입별 아이콘 반환"""
        icons = {
            'item': '📦', 'weapon': '⚔️', 'armor': '🛡️', 'food': '🍎',
            'book': '📚', 'key': '🗝️', 'treasure': '💎', 'furniture': '🪑',
            'npc': '👤', 'monster': '👹', 'container': '📦'
        }
        return icons.get(object_type, '❓')

    def _generate_autocomplete_hints(self, session: SessionType, room_info: Dict[str, Any]) -> List[str]:
        """자동완성 힌트 생성"""
        hints = []

        # 기본 명령어들
        basic_commands = ['look', 'inventory', 'who', 'help', 'say', 'tell', 'quit']
        hints.extend(basic_commands)

        # 방향 명령어들
        for direction in room_info['exits'].keys():
            hints.append(direction)
            # 축약형도 추가
            if direction == 'north': hints.append('n')
            elif direction == 'south': hints.append('s')
            elif direction == 'east': hints.append('e')
            elif direction == 'west': hints.append('w')

        # 객체 관련 명령어들
        for obj in room_info['objects']:
            obj_name = obj.get_localized_name(session.locale)
            hints.extend([
                f"examine {obj_name}",
                f"get {obj_name}",
                f"look at {obj_name}"
            ])

        return sorted(list(set(hints)))