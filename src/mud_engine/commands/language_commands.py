"""
언어 설정 관련 명령어들
"""

import logging
from typing import List

from .base import BaseCommand, CommandResult
from ..core.types import SessionType
from ..core.localization import get_localization_manager

logger = logging.getLogger(__name__)


class LanguageCommand(BaseCommand):
    """언어 설정 명령어"""

    def __init__(self):
        super().__init__(
            name="language",
            aliases=["lang", "locale"],
            description="언어 설정을 변경합니다",
            usage="language [en|ko]"
        )

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        if not session.is_authenticated or not session.player:
            return self.create_error_result("인증되지 않은 사용자입니다.")

        localization = get_localization_manager()
        current_locale = session.player.preferred_locale

        # 인자가 없으면 현재 언어 표시

        if current_locale == "ko":
            message = f"현재 언어: 한국어 (ko)\n"
            return self.create_info_result(message)
        elif current_locale == "en":
            message = f"Current language: English (en)\n"
            return self.create_info_result(message)
        else:
            current_locale = "en"

            # 언어 설정 변경
            session.player.preferred_locale = current_locale

            # 세션의 locale도 업데이트
            session.update_locale()

            # 성공 메시지 (새로운 언어로)
            success_message = localization.get_message("language.changed", current_locale)

        return self.create_success_result(
            message=success_message,
            data={"new_language": current_locale}
        )


class HelpCommand(BaseCommand):
    """도움말 명령어 (다국어 지원)"""

    def __init__(self):
        super().__init__(
            name="help",
            aliases=["?", "commands"],
            description="도움말을 표시합니다",
            usage="help [command]"
        )

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        if not session.is_authenticated or not session.player:
            return self.create_error_result("인증되지 않은 사용자입니다.")

        localization = get_localization_manager()
        locale = session.player.preferred_locale

        # 특정 명령어 도움말
        if args:
            command_name = args[0].lower()
            # TODO: 특정 명령어 도움말 구현
            return self.create_info_result(f"Help for '{command_name}' - Not implemented yet")

        # 전체 명령어 목록
        header = localization.get_message("help.header", locale)
        footer = localization.get_message("help.footer", locale)

        # 기본 명령어들 (다국어 지원)
        if locale == "ko":
            commands = [
                "🎮 게임 명령어:",
                "  look (l)     - 주변을 둘러봅니다",
                "  go <방향>    - 지정된 방향으로 이동합니다",
                "  north (n)   - 북쪽으로 이동",
                "  south (s)   - 남쪽으로 이동",
                "  east (e)    - 동쪽으로 이동",
                "  west (w)    - 서쪽으로 이동",
                "",
                "⚔️ 전투 명령어:",
                "  attack <대상> - 몬스터를 공격합니다",
                "  defend      - 방어 자세를 취합니다",
                "  flee        - 전투에서 도망칩니다",
                "",
                "📦 아이템 명령어:",
                "  inventory (i) - 인벤토리를 확인합니다",
                "  get <아이템>  - 아이템을 줍습니다",
                "  drop <아이템> - 아이템을 떨어뜨립니다",
                "",
                "💬 소통 명령어:",
                "  say <메시지>    - 같은 방의 모든 사람에게 말합니다",
                "  whisper <플레이어> <메시지> - 귓속말을 보냅니다",
                "",
                "⚙️ 시스템 명령어:",
                "  language [en|ko] - 언어를 변경합니다",
                "  stats           - 능력치를 확인합니다",
                "  quit            - 게임을 종료합니다"
            ]
        else:
            commands = [
                "🎮 Game Commands:",
                "  look (l)     - Look around",
                "  go <dir>     - Move in specified direction",
                "  north (n)    - Move north",
                "  south (s)    - Move south",
                "  east (e)     - Move east",
                "  west (w)     - Move west",
                "",
                "⚔️ Combat Commands:",
                "  attack <target> - Attack a monster",
                "  defend         - Take defensive stance",
                "  flee           - Flee from combat",
                "",
                "📦 Item Commands:",
                "  inventory (i)   - Check your inventory",
                "  get <item>      - Pick up an item",
                "  drop <item>     - Drop an item",
                "",
                "💬 Communication:",
                "  say <message>              - Say to everyone in room",
                "  whisper <player> <message> - Send private message",
                "",
                "⚙️ System Commands:",
                "  language [en|ko] - Change language",
                "  stats           - Show your stats",
                "  quit            - Quit the game"
            ]

        message = f"{header}\n\n" + "\n".join(commands) + f"\n\n{footer}"

        return self.create_info_result(message)