# -*- coding: utf-8 -*-
"""기본 게임 명령어들"""

import logging
from typing import List

from .base import BaseCommand, CommandResult, CommandResultType
from ..server.session import Session

logger = logging.getLogger(__name__)


class SayCommand(BaseCommand):
    """말하기 명령어"""

    def __init__(self):
        super().__init__(
            name="say",
            aliases=["'"],
            description="같은 방에 있는 모든 플레이어에게 메시지를 전달합니다",
            usage="say <메시지> 또는 '<메시지>"
        )

    async def execute(self, session: Session, args: List[str]) -> CommandResult:
        if not self.validate_args(args, min_args=1):
            return self.create_error_result(
                "말할 내용을 입력해주세요.\n사용법: say <메시지>"
            )

        message = " ".join(args)
        username = session.player.username

        # 플레이어에게 확인 메시지
        player_message = f"💬 당신이 말했습니다: \"{message}\""

        # 다른 플레이어들에게 브로드캐스트할 메시지
        broadcast_message = f"💬 {username}님이 말했습니다: \"{message}\""

        return self.create_success_result(
            message=player_message,
            data={
                "action": "say",
                "speaker": username,
                "message": message
            },
            broadcast=True,
            broadcast_message=broadcast_message,
            room_only=True
        )


class TellCommand(BaseCommand):
    """귓속말 명령어"""

    def __init__(self):
        super().__init__(
            name="tell",
            aliases=["whisper", "t"],
            description="특정 플레이어에게 개인 메시지를 전달합니다",
            usage="tell <플레이어명> <메시지>"
        )

    async def execute(self, session: Session, args: List[str]) -> CommandResult:
        if not self.validate_args(args, min_args=2):
            return self.create_error_result(
                "귓속말할 플레이어와 메시지를 입력해주세요.\n사용법: tell <플레이어명> <메시지>"
            )

        target_username = args[0]
        message = " ".join(args[1:])
        sender_username = session.player.username

        # TODO: 실제로는 SessionManager를 통해 대상 플레이어를 찾아야 함
        # 현재는 기본 구현만 제공

        if target_username.lower() == sender_username.lower():
            return self.create_error_result("자기 자신에게는 귓속말할 수 없습니다.")

        # 발신자에게 확인 메시지
        sender_message = f"📨 {target_username}님에게 귓속말: \"{message}\""

        return self.create_success_result(
            message=sender_message,
            data={
                "action": "tell",
                "sender": sender_username,
                "target": target_username,
                "message": message,
                "private": True
            }
        )


class WhoCommand(BaseCommand):
    """접속자 목록 명령어"""

    def __init__(self, session_manager=None):
        super().__init__(
            name="who",
            aliases=["users", "players"],
            description="현재 접속 중인 플레이어 목록을 표시합니다",
            usage="who"
        )
        self.session_manager = session_manager

    async def execute(self, session: Session, args: List[str]) -> CommandResult:
        if not self.session_manager:
            # 기본 구현
            response = f"""
📋 접속 중인 플레이어:
• {session.player.username} (당신)

총 1명이 접속 중입니다.
            """.strip()

            return self.create_success_result(
                message=response,
                data={
                    "action": "who",
                    "player_count": 1,
                    "players": [session.player.username]
                }
            )

        # SessionManager를 통해 실제 접속자 목록 가져오기
        authenticated_sessions = self.session_manager.get_authenticated_sessions()

        if not authenticated_sessions:
            return self.create_info_result("현재 접속 중인 플레이어가 없습니다.")

        players = []
        for sess in authenticated_sessions.values():
            if sess.player:
                session_time = (sess.last_activity - sess.created_at).total_seconds()
                players.append({
                    "username": sess.player.username,
                    "session_time": int(session_time),
                    "is_self": sess.session_id == session.session_id
                })

        response = f"📋 접속 중인 플레이어 ({len(players)}명):\n"
        for player in players:
            marker = " (당신)" if player["is_self"] else ""
            response += f"• {player['username']}{marker} (접속시간: {player['session_time']}초)\n"

        return self.create_success_result(
            message=response.strip(),
            data={
                "action": "who",
                "player_count": len(players),
                "players": [p["username"] for p in players]
            }
        )


class LookCommand(BaseCommand):
    """둘러보기 명령어"""

    def __init__(self):
        super().__init__(
            name="look",
            aliases=["l", "examine"],
            description="주변을 둘러보거나 특정 대상을 자세히 살펴봅니다",
            usage="look [대상]"
        )

    async def execute(self, session: Session, args: List[str]) -> CommandResult:
        if not args:
            # 방 전체 둘러보기
            return await self._look_around(session)
        else:
            # 특정 대상 살펴보기
            target = " ".join(args)
            return await self._look_at(session, target)

    async def _look_around(self, session: Session) -> CommandResult:
        """방 전체 둘러보기"""
        # TODO: 실제로는 WorldManager를 통해 방 정보를 가져와야 함
        # 현재는 기본 구현만 제공

        username = session.player.username

        response = f"""
🏰 시작 지역
고대 문명의 잔해가 남은 신비로운 장소입니다.
주변에는 오래된 돌기둥들이 서 있고, 바닥에는 이상한 문양이 새겨져 있습니다.

👥 이곳에 있는 사람들:
• {username} (당신)

🚪 출구:
• 북쪽 (north) - 고대 유적지
• 남쪽 (south) - 숲속 오솔길
• 동쪽 (east) - 신비한 호수
        """.strip()

        return self.create_success_result(
            message=response,
            data={
                "action": "look",
                "room_id": "start_room",
                "room_name": "시작 지역",
                "players": [username],
                "exits": ["north", "south", "east"]
            }
        )

    async def _look_at(self, session: Session, target: str) -> CommandResult:
        """특정 대상 살펴보기"""
        target_lower = target.lower()

        # 자기 자신 살펴보기
        if target_lower in ["me", "myself", session.player.username.lower()]:
            response = f"""
👤 {session.player.username}
당신은 이 신비로운 세계에 발을 들인 모험가입니다.
아직 여행을 시작한 지 얼마 되지 않아 평범한 옷을 입고 있습니다.
            """.strip()

            return self.create_success_result(
                message=response,
                data={
                    "action": "look_at",
                    "target": "self",
                    "target_type": "player"
                }
            )

        # 기타 대상들
        return self.create_info_result(
            f"'{target}'을(를) 찾을 수 없습니다."
        )


class HelpCommand(BaseCommand):
    """도움말 명령어"""

    def __init__(self, command_processor=None):
        super().__init__(
            name="help",
            aliases=["?", "commands"],
            description="명령어 도움말을 표시합니다",
            usage="help [명령어]"
        )
        self.command_processor = command_processor

    async def execute(self, session: Session, args: List[str]) -> CommandResult:
        if not self.command_processor:
            return self.create_error_result("명령어 처리기가 설정되지 않았습니다.")

        if args:
            # 특정 명령어 도움말
            command_name = args[0]
            help_text = self.command_processor.get_help_text(command_name)
        else:
            # 전체 명령어 목록
            help_text = self.command_processor.get_help_text()

        return self.create_success_result(
            message=help_text,
            data={
                "action": "help",
                "command": args[0] if args else None
            }
        )


class QuitCommand(BaseCommand):
    """종료 명령어"""

    def __init__(self):
        super().__init__(
            name="quit",
            aliases=["exit", "logout"],
            description="게임을 종료합니다",
            usage="quit"
        )

    async def execute(self, session: Session, args: List[str]) -> CommandResult:
        return self.create_success_result(
            message="안전하게 게임을 종료합니다. 안녕히 가세요!",
            data={
                "action": "quit",
                "disconnect": True
            }
        )