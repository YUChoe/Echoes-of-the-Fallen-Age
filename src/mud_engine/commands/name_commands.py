"""
사용자 이름 관련 명령어
"""

import logging
from datetime import datetime
from typing import List, TYPE_CHECKING

from .base import BaseCommand, CommandResult, CommandResultType
from ..core.types import SessionType

if TYPE_CHECKING:
    from ..core.game_engine import GameEngine


class ChangeNameCommand(BaseCommand):
    """사용자 이름 변경 명령어"""

    def __init__(self):
        super().__init__(
            name="changename",
            description="게임 내 표시 이름을 변경합니다 (하루에 한 번만 가능)",
            aliases=["setname", "rename"]
        )
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        """명령어 실행"""
        if not session.player:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message="로그인이 필요합니다."
            )

        # 인자 확인
        if not args:
            current_name = session.player.get_display_name()
            can_change = session.player.can_change_name()
            
            if session.player.is_admin:
                usage_msg = "사용법: changename <새로운 이름>\n관리자는 제한 없이 이름을 변경할 수 있습니다."
            elif can_change:
                usage_msg = "사용법: changename <새로운 이름>\n이름은 하루에 한 번만 변경할 수 있습니다."
            else:
                # 다음 변경 가능 시간 계산
                if session.player.last_name_change:
                    time_since_change = datetime.now() - session.player.last_name_change
                    hours_left = 24 - (time_since_change.total_seconds() / 3600)
                    usage_msg = f"사용법: changename <새로운 이름>\n⏰ 다음 이름 변경까지 {hours_left:.1f}시간 남았습니다."
                else:
                    usage_msg = "사용법: changename <새로운 이름>"
            
            await session.send_message({
                "type": "info",
                "message": f"현재 이름: {current_name}\n{usage_msg}"
            })
            return CommandResult(
                result_type=CommandResultType.INFO,
                message="이름 변경 도움말 표시"
            )

        # 새 이름 가져오기 (공백 포함 가능)
        new_name = " ".join(args).strip()

        # 이름 유효성 검사
        if not session.player.is_valid_display_name(new_name):
            await session.send_error("❌ 올바르지 않은 이름입니다. 이름은 3-20자의 한글, 영문, 숫자, 공백만 사용할 수 있습니다.")
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message="올바르지 않은 이름"
            )

        # 이름 변경 가능 여부 확인
        if not session.player.can_change_name():
            time_since_change = datetime.now() - session.player.last_name_change
            hours_left = 24 - (time_since_change.total_seconds() / 3600)
            await session.send_error(f"❌ 이름은 하루에 한 번만 변경할 수 있습니다. 다음 변경까지 {hours_left:.1f}시간 남았습니다.")
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message="이름 변경 제한"
            )

        # 이전 이름 저장
        old_name = session.player.get_display_name()

        # 이름 변경
        session.player.display_name = new_name
        if not session.player.is_admin:
            session.player.last_name_change = datetime.now()

        # 데이터베이스 업데이트
        try:
            # PlayerRepository를 통해 업데이트
            from ..game.repositories import PlayerRepository
            from ..database import get_database_manager
            
            db_manager = await get_database_manager()
            player_repo = PlayerRepository(db_manager)
            
            # Player 객체를 딕셔너리로 변환하여 업데이트
            update_data = {
                'display_name': session.player.display_name,
                'last_name_change': session.player.last_name_change.isoformat() if session.player.last_name_change else None
            }
            await player_repo.update(session.player.id, update_data)
            
            await session.send_success(f"✅ 이름이 '{old_name}'에서 '{new_name}'(으)로 변경되었습니다!")
            
            # 같은 방에 있는 다른 플레이어들에게 알림 (브로드캐스트는 생략)
            # 실제 브로드캐스트는 GameEngine을 통해야 하지만, 명령어에서는 직접 접근 불가
            
            self.logger.info(f"플레이어 {session.player.username}의 이름이 '{old_name}'에서 '{new_name}'(으)로 변경됨")
            return CommandResult(
                result_type=CommandResultType.SUCCESS,
                message=f"이름 변경: {old_name} -> {new_name}"
            )

        except Exception as e:
            self.logger.error(f"이름 변경 중 오류 발생: {e}", exc_info=True)
            await session.send_error("❌ 이름 변경 중 오류가 발생했습니다.")
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=f"이름 변경 실패: {e}"
            )


class AdminChangeNameCommand(BaseCommand):
    """관리자용 다른 플레이어 이름 변경 명령어"""

    def __init__(self):
        super().__init__(
            name="adminchangename",
            description="다른 플레이어의 이름을 변경합니다 (관리자 전용)",
            aliases=["adminrename", "forcechangename"],
            admin_only=True
        )
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        """명령어 실행"""
        # 관리자 권한 확인
        if not session.player or not session.player.is_admin:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message="❌ 관리자 권한이 필요한 명령어입니다."
            )

        # 인자 확인
        if len(args) < 2:
            await session.send_message({
                "type": "info",
                "message": "사용법: adminchangename <사용자명> <새로운 이름>"
            })
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message="인자 부족"
            )

        target_username = args[0]
        new_name = " ".join(args[1:]).strip()

        # 이름 유효성 검사
        from ..game.models import Player
        if not Player.is_valid_display_name(new_name):
            await session.send_error("❌ 올바르지 않은 이름입니다. 이름은 3-20자의 한글, 영문, 숫자, 공백만 사용할 수 있습니다.")
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message="올바르지 않은 이름"
            )

        # 대상 플레이어 찾기
        try:
            from ..game.repositories import PlayerRepository
            from ..database import get_database_manager
            from ..server.session import SessionManager
            
            db_manager = await get_database_manager()
            player_repo = PlayerRepository(db_manager)
            target_player = await player_repo.get_by_username(target_username)
            
            if not target_player:
                await session.send_error(f"❌ 플레이어 '{target_username}'을(를) 찾을 수 없습니다.")
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message="플레이어를 찾을 수 없음"
                )

            # 이전 이름 저장
            old_name = target_player.get_display_name()

            # 이름 변경
            target_player.display_name = new_name
            # 관리자가 변경하는 경우 last_name_change는 업데이트하지 않음

            # 데이터베이스 업데이트
            update_data = {
                'display_name': target_player.display_name
            }
            await player_repo.update(target_player.id, update_data)
            
            await session.send_success(f"✅ {target_username}의 이름이 '{old_name}'에서 '{new_name}'(으)로 변경되었습니다!")
            
            # 대상 플레이어가 온라인인 경우 알림 (브로드캐스트는 생략)
            # 실제 브로드캐스트는 GameEngine을 통해야 하지만, 명령어에서는 직접 접근 불가
            
            self.logger.info(f"관리자 {session.player.username}가 {target_username}의 이름을 '{old_name}'에서 '{new_name}'(으)로 변경함")
            return CommandResult(
                result_type=CommandResultType.SUCCESS,
                message=f"관리자 이름 변경: {target_username} {old_name} -> {new_name}"
            )

        except Exception as e:
            self.logger.error(f"관리자 이름 변경 중 오류 발생: {e}", exc_info=True)
            await session.send_error("❌ 이름 변경 중 오류가 발생했습니다.")
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=f"이름 변경 실패: {e}"
            )
