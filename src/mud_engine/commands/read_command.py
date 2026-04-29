# -*- coding: utf-8 -*-
"""읽을 수 있는 아이템 읽기 명령어"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseCommand, CommandResult
from .utils import get_user_locale
from ..core.types import SessionType
from ..core.localization import get_localization_manager

logger = logging.getLogger(__name__)
I18N = get_localization_manager()

# 아이템 유형별 아이콘 매핑
READABLE_ICONS = {
    "book": "📖",
    "note": "📜",
    "scroll": "📜",
    "letter": "✉️",
}


class ReadCommand(BaseCommand):
    """읽을 수 있는 아이템의 텍스트 내용을 표시하는 명령어"""

    def __init__(self) -> None:
        super().__init__(
            name="read",
            aliases=[],
            description="읽을 수 있는 아이템의 내용을 확인합니다",
            usage="read <아이템명> [페이지번호]"
        )

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        """명령어 실행 진입점"""
        locale = get_user_locale(session)

        # 인자 검증
        if not self.validate_args(args, min_args=1):
            return self.create_error_result(
                I18N.get_message("read.usage", locale)
            )

        # 인증 확인
        if not session.is_authenticated or not session.player:
            return self.create_error_result(
                I18N.get_message("obj.unauthenticated", locale)
            )

        game_engine = getattr(session, 'game_engine', None)
        if not game_engine:
            return self.create_error_result(
                I18N.get_message("obj.no_engine", locale)
            )

        # 인자 파싱: 마지막 인자가 숫자이면 페이지 번호로 처리
        page: Optional[int] = None
        item_args = list(args)

        if len(item_args) > 1 and item_args[-1].isdigit():
            page = int(item_args[-1])
            item_args = item_args[:-1]

        item_name = " ".join(item_args).lower()

        try:
            target_item = None

            # 엔티티 번호로 검색 (숫자만 입력된 경우)
            if item_name.isdigit():
                entity_num = int(item_name)
                target_item = self._find_item_by_entity_number(
                    session, entity_num
                )

            # 이름으로 검색 (인벤토리 → 방)
            if not target_item:
                target_item = await self._find_item_by_name(
                    session, game_engine, item_name
                )

            if not target_item:
                return self.create_error_result(
                    I18N.get_message(
                        "read.not_found", locale,
                        name=" ".join(args)
                    )
                )

            # [Lua 콜백 우선 시도] 아이템 Lua 스크립트가 있으면 콜백 실행
            lua_result = self._try_lua_callback(
                session, game_engine, target_item, "read"
            )
            if lua_result is not None:
                message = lua_result.get("message", "")
                return self.create_success_result(
                    message=message,
                    data={
                        "action": "read",
                        "item_name": target_item.get_localized_name(locale),
                        "lua_callback": True,
                    }
                )

            # [기존 폴백] readable 판별
            if not self._is_readable(target_item):
                display_name = target_item.get_localized_name(locale)
                return self.create_error_result(
                    I18N.get_message(
                        "read.not_readable", locale,
                        name=display_name
                    )
                )

            # 텍스트 표시
            display_name = target_item.get_localized_name(locale)
            text, hint = self._get_readable_text(
                target_item, locale, page, display_name
            )

            # 아이콘 결정
            readable = self._get_readable_props(target_item)
            readable_type = readable.get("type", "note")
            icon = READABLE_ICONS.get(readable_type, "📜")

            # 헤더 구성
            header = I18N.get_message(
                "read.header", locale,
                icon=icon, name=display_name
            )

            # 최종 출력 조합
            output_parts = [header, "", text]
            if hint:
                output_parts.append("")
                output_parts.append(hint)

            message = "\n".join(output_parts)

            return self.create_success_result(
                message=message,
                data={
                    "action": "read",
                    "item_name": display_name,
                    "readable_type": readable_type,
                }
            )

        except Exception as e:
            logger.error(f"읽기 명령어 실행 중 오류: {e}", exc_info=True)
            return self.create_error_result(
                I18N.get_message("read.error", locale)
            )

    def _find_item_by_entity_number(
        self, session: SessionType, entity_num: int
    ) -> Optional[Any]:
        """인벤토리 엔티티 번호로 아이템 검색"""
        inventory_entity: Dict[int, Any] = getattr(session, 'inventory_entity_map', {})
        if entity_num in inventory_entity:
            return inventory_entity[entity_num]['objects'][0]
        return None

    async def _find_item_by_name(
        self, session: SessionType, game_engine: Any, item_name: str
    ) -> Optional[Any]:
        """이름으로 아이템 검색 (인벤토리 → 방 순서, 대소문자 무시 부분 일치)"""
        # 인벤토리 검색
        inventory_objects = await game_engine.world_manager.get_inventory_objects(
            session.player.id  # type: ignore[union-attr]
        )
        for obj in inventory_objects:
            obj_name_en = obj.get_localized_name('en').lower()
            obj_name_ko = obj.get_localized_name('ko').lower()
            if item_name in obj_name_en or item_name in obj_name_ko:
                return obj

        # 방 검색
        current_room_id = getattr(session, 'current_room_id', None)
        if current_room_id:
            room_objects = await game_engine.world_manager.get_room_objects(
                current_room_id
            )
            for obj in room_objects:
                obj_name_en = obj.get_localized_name('en').lower()
                obj_name_ko = obj.get_localized_name('ko').lower()
                if item_name in obj_name_en or item_name in obj_name_ko:
                    return obj

        return None

    def _is_readable(self, item: Any) -> bool:
        """아이템이 readable 속성을 가지고 있는지 확인"""
        readable = self._get_readable_props(item)
        return bool(readable)

    def _get_readable_props(self, item: Any) -> Dict[str, Any]:
        """아이템에서 readable 속성 딕셔너리를 안전하게 추출"""
        properties = getattr(item, 'properties', {})
        if isinstance(properties, str):
            try:
                properties = json.loads(properties)
            except (json.JSONDecodeError, TypeError):
                return {}
        if not isinstance(properties, dict):
            return {}
        readable = properties.get("readable", {})
        if isinstance(readable, str):
            try:
                readable = json.loads(readable)
            except (json.JSONDecodeError, TypeError):
                return {}
        return readable if isinstance(readable, dict) else {}

    def _get_readable_text(
        self, item: Any, locale: str,
        page: Optional[int], display_name: str
    ) -> Tuple[str, Optional[str]]:
        """readable 텍스트와 페이지 안내 메시지 반환"""
        readable = self._get_readable_props(item)
        hint: Optional[str] = None

        # 여러 페이지 (pages 키가 있는 경우)
        if "pages" in readable:
            pages = readable["pages"]
            if not isinstance(pages, list) or len(pages) == 0:
                return self._get_localized_content(
                    readable.get("content", {}), locale
                ), None

            total = len(pages)

            if page is None:
                # 페이지 번호 없으면 첫 페이지 + 안내
                page = 1
                if total > 1:
                    hint = I18N.get_message(
                        "read.page_hint", locale,
                        total=total, name=display_name
                    )

            # 범위 검증
            if page < 1 or page > total:
                error_msg = I18N.get_message(
                    "read.invalid_page", locale, total=total
                )
                return error_msg, None

            page_content = pages[page - 1]
            text = self._get_localized_content(page_content, locale)

            # 페이지 정보
            page_info = I18N.get_message(
                "read.page_info", locale,
                current=page, total=total
            )

            return f"{page_info}\n\n{text}", hint

        # 단일 페이지 (content 키)
        content = readable.get("content", {})
        text = self._get_localized_content(content, locale)
        return text, None

    def _get_localized_content(
        self, content: Any, locale: str
    ) -> str:
        """로케일에 맞는 텍스트 반환 (폴백 로직 포함)"""
        if not isinstance(content, dict):
            return str(content) if content else ""

        # 폴백 체인: 요청 로케일 → en → ko
        if locale in content and content[locale]:
            return str(content[locale])
        if "en" in content and content["en"]:
            return str(content["en"])
        if "ko" in content and content["ko"]:
            return str(content["ko"])

        # 아무 값이라도 반환
        for val in content.values():
            if val:
                return str(val)
        return ""

    def _try_lua_callback(
        self, session: Any, game_engine: Any,
        target_item: Any, verb: str,
    ) -> Dict[str, Any] | None:
        """아이템 Lua 콜백 시도 - 결과가 있으면 dict, 없으면 None 반환"""
        handler = getattr(game_engine, 'item_lua_callback_handler', None)
        if handler is None:
            return None

        # properties에서 template_id 추출 (dict/str 방어적 처리)
        properties = getattr(target_item, 'properties', {})
        if isinstance(properties, str):
            try:
                properties = json.loads(properties)
            except (json.JSONDecodeError, TypeError):
                properties = {}
        if not isinstance(properties, dict):
            return None

        template_id = properties.get("template_id")
        if not template_id:
            return None

        # Callback_Context 구성
        player = session.player
        context: Dict[str, Any] = {
            "player": {
                "id": str(player.id),
                "display_name": player.get_display_name(),
                "locale": player.preferred_locale,
            },
            "item": {
                "id": str(target_item.id),
                "template_id": template_id,
                "name": {
                    "en": target_item.get_localized_name("en"),
                    "ko": target_item.get_localized_name("ko"),
                },
                "properties": properties,
            },
            "session": {
                "locale": session.locale,
            },
        }

        return handler.execute_verb_callback(template_id, verb, context)
