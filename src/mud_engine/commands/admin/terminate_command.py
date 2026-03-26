# -*- coding: utf-8 -*-
"""객체/몬스터 완전 삭제 명령어 (respawn 방지)"""

import logging
from typing import List

from .base import AdminCommand
from ..base import CommandResult, CommandResultType
from ..utils import get_user_locale
from ...core.types import SessionType
from ...core.localization import get_localization_manager

logger = logging.getLogger(__name__)
I18N = get_localization_manager()


class TerminateCommand(AdminCommand):
    """객체/몬스터 완전 삭제 명령어 (respawn 방지)"""

    def __init__(self):
        super().__init__(
            name="terminate",
            description="지정한 객체나 몬스터를 완전히 삭제하고 respawn을 방지합니다",
            aliases=["destroy", "delete"],
            usage="terminate <대상_ID_또는_번호> [reason]"
        )

    async def execute_admin(self, session: SessionType, args: List[str]) -> CommandResult:
        """terminate 명령어 실행"""
        locale = get_user_locale(session)
        if not args:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.terminate.usage", locale)
            )

        target_identifier = args[0]
        reason = " ".join(args[1:]) if len(args) > 1 else I18N.get_message("admin.terminate.default_reason", locale)

        try:
            game_engine = getattr(session, 'game_engine', None)
            if not game_engine:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message=I18N.get_message("admin.no_game_engine", locale)
                )

            current_room_id = getattr(session, 'current_room_id', None)
            if not current_room_id:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message=I18N.get_message("admin.no_current_room", locale)
                )

            # 엔티티 번호 매핑에서 대상 찾기
            entity_map = getattr(session, 'room_entity_map', {})
            target_entity = None
            target_type = None
            target_id = None

            # 숫자인 경우 엔티티 번호로 처리
            if target_identifier.isdigit():
                entity_num = int(target_identifier)
                if entity_num in entity_map:
                    target_entity = entity_map[entity_num]['entity']
                    target_type = entity_map[entity_num]['type']
                    target_id = entity_map[entity_num]['id']
                else:
                    return CommandResult(
                        result_type=CommandResultType.ERROR,
                        message=I18N.get_message("admin.terminate.entity_not_found", locale, num=entity_num)
                    )
            else:
                # ID로 직접 검색
                target_id = target_identifier

                # 몬스터 검색
                monster = await game_engine.world_manager.get_monster(target_id)
                if monster:
                    target_entity = monster
                    target_type = 'monster'
                else:
                    # 객체 검색
                    obj = await game_engine.world_manager.get_game_object(target_id)
                    if obj:
                        target_entity = obj
                        target_type = 'object'

            if not target_entity:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message=I18N.get_message("admin.terminate.target_not_found", locale, identifier=target_identifier)
                )

            # 대상 정보 확인
            target_name = target_entity.get_localized_name(locale)
            template_id = target_entity.get_property('template_id')

            # 삭제 실행
            success = False
            if target_type == 'monster':
                # 몬스터 삭제
                success = await game_engine.world_manager.delete_monster(target_id)

                # 스폰 포인트도 제거 (respawn 방지)
                if success and template_id:
                    await game_engine.world_manager.remove_spawn_point(current_room_id, template_id)
                    logger.info(f"몬스터 {target_id}의 스폰 포인트 제거됨 (방: {current_room_id}, 템플릿: {template_id})")

            elif target_type == 'object':
                # 객체 삭제
                success = await game_engine.world_manager.delete_game_object(target_id)

            if success:
                success_msg = I18N.get_message("admin.terminate.success", locale, name=target_name, id=target_id)
                if target_type == 'monster' and template_id:
                    success_msg += f"\n{I18N.get_message('admin.terminate.spawn_removed', locale)}"
                default_reason = I18N.get_message("admin.terminate.default_reason", locale)
                if reason != default_reason:
                    success_msg += f"\n{I18N.get_message('admin.terminate.reason_note', locale, reason=reason)}"

                broadcast_msg = I18N.get_message("admin.terminate.broadcast", locale, name=target_name)
                await game_engine.broadcast_to_room(
                    current_room_id,
                    {"type": "admin_action", "message": broadcast_msg},
                    exclude_session=session.session_id
                )

                await game_engine.movement_manager.send_room_info_to_player(session, current_room_id)

                logger.info(f"관리자 {session.player.username}이 {target_type} {target_id}를 삭제함 (사유: {reason})")

                return CommandResult(
                    result_type=CommandResultType.SUCCESS,
                    message=success_msg
                )
            else:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message=I18N.get_message("admin.terminate.failed", locale, name=target_name)
                )

        except Exception as e:
            logger.error(f"terminate 명령어 실행 실패: {e}")
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.terminate.error", locale, error=str(e))
            )

    def get_help(self) -> str:
        return """
🗑️ **객체/몬스터 완전 삭제 명령어**

지정한 객체나 몬스터를 완전히 삭제하고 respawn을 방지합니다.

**사용법:** `terminate <대상_ID_또는_번호> [사유]`

**별칭:** `destroy`, `delete`
**권한:** 관리자 전용

**매개변수:**
- `대상_ID_또는_번호`: 삭제할 대상의 ID 또는 방에서의 번호
- `사유` (선택사항): 삭제 사유

**예시:**
- `terminate 1` - 방의 1번 대상 삭제
- `terminate goblin_001 버그 수정` - 특정 ID의 몬스터를 사유와 함께 삭제

**주의사항:**
- 몬스터 삭제 시 해당 방의 스폰 포인트도 함께 제거됩니다
- 삭제된 대상은 더 이상 respawn되지 않습니다
- 이 작업은 되돌릴 수 없습니다
        """
