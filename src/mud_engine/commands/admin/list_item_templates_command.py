# -*- coding: utf-8 -*-
"""아이템 템플릿 목록 조회 명령어"""

import logging
from typing import List

from .base import AdminCommand
from ..base import CommandResult, CommandResultType
from ..utils import get_user_locale
from ...core.types import SessionType
from ...core.localization import get_localization_manager

logger = logging.getLogger(__name__)
I18N = get_localization_manager()


class ListItemTemplatesCommand(AdminCommand):
    """아이템 템플릿 목록 조회 명령어"""

    def __init__(self):
        super().__init__(
            name="itemtemplates",
            description="사용 가능한 아이템 템플릿 목록을 표시합니다",
            aliases=["listitemtemplates", "items"]
        )

    async def execute_admin(self, session: SessionType, args: List[str]) -> CommandResult:
        """아이템 템플릿 목록 표시"""
        locale = get_user_locale(session)
        try:
            game_engine = session.game_engine
            if not game_engine:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message=I18N.get_message("admin.no_game_engine", locale)
                )

            template_loader = game_engine.world_manager._monster_manager._template_loader
            templates = template_loader.get_all_item_templates()

            if not templates:
                return CommandResult(
                    result_type=CommandResultType.INFO,
                    message=I18N.get_message("admin.itemtemplates.empty", locale)
                )

            template_list = "📦 Item Templates:\n\n"

            for template_id, template_data in templates.items():
                name_ko = template_data.get('name_ko', '이름 없음')
                name_en = template_data.get('name_en', 'No name')
                object_type = template_data.get('object_type', 'item')
                category = template_data.get('category', 'misc')

                template_list += f"• {template_id}"
                template_list += f"  {name_ko} ({name_en})"
                template_list += f"  type: {object_type}, category: {category}\n"

            template_list += f"Total: {len(templates)} item templates\n"
            template_list += "\nUsage: `mkitem <template_name>`"

            return CommandResult(
                result_type=CommandResultType.SUCCESS,
                message=template_list
            )

        except Exception as e:
            logger.error(f"아이템 템플릿 목록 조회 실패: {e}")
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.itemtemplates.error", locale, error=str(e))
            )

    def get_help(self, locale: str = "en") -> str:
        return """
📦 **아이템 템플릿 목록 도움말**

현재 로드된 아이템 템플릿 목록을 표시합니다.

**사용법:** `itemtemplates`

**별칭:** `listitemtemplates`, `items`
**권한:** 관리자 전용

각 템플릿의 ID, 이름, 타입, 카테고리 정보를 확인할 수 있습니다.
        """
