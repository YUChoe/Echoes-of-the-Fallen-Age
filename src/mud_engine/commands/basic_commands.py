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
        if not session.is_authenticated or not session.player:
            return self.create_error_result("인증되지 않은 사용자입니다.")

        # 현재 방 ID 가져오기
        current_room_id = getattr(session, 'current_room_id', None)
        if not current_room_id:
            return self.create_error_result("현재 위치를 확인할 수 없습니다.")

        # GameEngine을 통해 방 정보 조회
        game_engine = getattr(session, 'game_engine', None)
        if not game_engine:
            return self.create_error_result("게임 엔진에 접근할 수 없습니다.")

        try:
            # 방 정보 조회
            room_info = await game_engine.get_room_info(current_room_id, session.locale)
            if not room_info:
                return self.create_error_result("방 정보를 찾을 수 없습니다.")

            room = room_info['room']
            objects = room_info['objects']
            exits = room_info['exits']

            # 방 이름과 설명
            room_name = room.get_localized_name(session.locale)
            room_description = room.get_localized_description(session.locale)

            # 응답 메시지 구성
            response = f"🏰 {room_name}\n{room_description}\n"

            # 방에 있는 객체들
            if objects:
                response += "\n📦 이곳에 있는 물건들:\n"
                for obj in objects:
                    obj_name = obj.get_localized_name(session.locale)
                    response += f"• {obj_name}\n"

            # TODO: 같은 방에 있는 다른 플레이어들 표시
            response += f"\n👥 이곳에 있는 사람들:\n• {session.player.username} (당신)\n"

            # 출구 정보
            if exits:
                response += "\n🚪 출구:\n"
                for direction, target_room_id in exits.items():
                    # 목적지 방 이름 조회 (선택사항)
                    try:
                        target_room = await game_engine.world_manager.get_room(target_room_id)
                        if target_room:
                            target_name = target_room.get_localized_name(session.locale)
                            response += f"• {direction} - {target_name}\n"
                        else:
                            response += f"• {direction}\n"
                    except:
                        response += f"• {direction}\n"
            else:
                response += "\n🚪 이 방에는 출구가 없습니다.\n"

            return self.create_success_result(
                message=response.strip(),
                data={
                    "action": "look",
                    "room_id": current_room_id,
                    "room_name": room_name,
                    "players": [session.player.username],
                    "exits": list(exits.keys()) if exits else [],
                    "objects": [obj.get_localized_name(session.locale) for obj in objects]
                }
            )

        except Exception as e:
            logger.error(f"방 둘러보기 중 오류: {e}")
            return self.create_error_result("방 정보를 조회하는 중 오류가 발생했습니다.")

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


class MoveCommand(BaseCommand):
    """이동 명령어 (방향별)"""

    def __init__(self, direction: str, aliases: List[str] = None):
        self.direction = direction
        super().__init__(
            name=direction,
            aliases=aliases or [],
            description=f"{direction} 방향으로 이동합니다",
            usage=direction
        )

    async def execute(self, session: Session, args: List[str]) -> CommandResult:
        if not session.is_authenticated or not session.player:
            return self.create_error_result("인증되지 않은 사용자입니다.")

        # 현재 방 ID 가져오기 (세션에서 또는 캐릭터에서)
        current_room_id = getattr(session, 'current_room_id', None)
        if not current_room_id:
            return self.create_error_result("현재 위치를 확인할 수 없습니다.")

        # GameEngine을 통해 이동 처리
        from ..core.game_engine import GameEngine
        game_engine = getattr(session, 'game_engine', None)
        if not game_engine:
            return self.create_error_result("게임 엔진에 접근할 수 없습니다.")

        try:
            # 현재 방 정보 조회
            current_room = await game_engine.world_manager.get_room(current_room_id)
            if not current_room:
                return self.create_error_result("현재 방을 찾을 수 없습니다.")

            # 해당 방향으로 출구가 있는지 확인
            target_room_id = current_room.get_exit(self.direction)
            if not target_room_id:
                return self.create_error_result(f"{self.direction} 방향으로는 갈 수 없습니다.")

            # 목적지 방 존재 확인
            target_room = await game_engine.world_manager.get_room(target_room_id)
            if not target_room:
                return self.create_error_result("목적지 방을 찾을 수 없습니다.")

            # 플레이어 이동 처리
            success = await game_engine.move_player_to_room(session, target_room_id)
            if not success:
                return self.create_error_result("이동에 실패했습니다.")

            # 이동 성공 메시지
            room_name = target_room.get_localized_name(session.locale)
            player_message = f"🚶 {self.direction} 방향으로 이동했습니다."

            # 이전 방의 다른 플레이어들에게 알림
            leave_message = f"🚶 {session.player.username}님이 {self.direction} 방향으로 떠났습니다."

            # 새 방의 다른 플레이어들에게 알림
            enter_message = f"🚶 {session.player.username}님이 도착했습니다."

            return self.create_success_result(
                message=player_message,
                data={
                    "action": "move",
                    "direction": self.direction,
                    "from_room": current_room_id,
                    "to_room": target_room_id,
                    "room_name": room_name,
                    "leave_message": leave_message,
                    "enter_message": enter_message
                }
            )

        except Exception as e:
            logger.error(f"이동 명령어 실행 중 오류: {e}")
            return self.create_error_result("이동 중 오류가 발생했습니다.")


class GoCommand(BaseCommand):
    """go 명령어 (방향 지정)"""

    def __init__(self):
        super().__init__(
            name="go",
            aliases=["move", "walk"],
            description="지정한 방향으로 이동합니다",
            usage="go <방향>"
        )

    async def execute(self, session: Session, args: List[str]) -> CommandResult:
        if not self.validate_args(args, min_args=1):
            return self.create_error_result(
                "이동할 방향을 지정해주세요.\n사용법: go <방향>\n"
                "사용 가능한 방향: north, south, east, west, up, down, northeast, northwest, southeast, southwest"
            )

        direction = args[0].lower()
        valid_directions = {
            'north', 'south', 'east', 'west', 'up', 'down',
            'northeast', 'northwest', 'southeast', 'southwest',
            'n', 's', 'e', 'w', 'u', 'd', 'ne', 'nw', 'se', 'sw'
        }

        # 축약형을 전체 이름으로 변환
        direction_map = {
            'n': 'north', 's': 'south', 'e': 'east', 'w': 'west',
            'u': 'up', 'd': 'down', 'ne': 'northeast', 'nw': 'northwest',
            'se': 'southeast', 'sw': 'southwest'
        }

        if direction in direction_map:
            direction = direction_map[direction]

        if direction not in valid_directions:
            return self.create_error_result(
                f"'{args[0]}'은(는) 올바른 방향이 아닙니다.\n"
                "사용 가능한 방향: north, south, east, west, up, down, northeast, northwest, southeast, southwest"
            )

        # MoveCommand를 임시로 생성하여 실행
        move_command = MoveCommand(direction)
        return await move_command.execute(session, [])


class ExitsCommand(BaseCommand):
    """출구 확인 명령어"""

    def __init__(self):
        super().__init__(
            name="exits",
            aliases=["ex", "directions"],
            description="현재 방의 출구를 확인합니다",
            usage="exits"
        )

    async def execute(self, session: Session, args: List[str]) -> CommandResult:
        if not session.is_authenticated or not session.player:
            return self.create_error_result("인증되지 않은 사용자입니다.")

        # 현재 방 ID 가져오기
        current_room_id = getattr(session, 'current_room_id', None)
        if not current_room_id:
            return self.create_error_result("현재 위치를 확인할 수 없습니다.")

        # GameEngine을 통해 방 정보 조회
        from ..core.game_engine import GameEngine
        game_engine = getattr(session, 'game_engine', None)
        if not game_engine:
            return self.create_error_result("게임 엔진에 접근할 수 없습니다.")

        try:
            current_room = await game_engine.world_manager.get_room(current_room_id)
            if not current_room:
                return self.create_error_result("현재 방을 찾을 수 없습니다.")

            exits = current_room.get_available_exits()
            if not exits:
                return self.create_info_result("🚪 이 방에는 출구가 없습니다.")

            # 출구 목록 생성
            exit_list = ", ".join(exits)
            message = f"🚪 사용 가능한 출구: {exit_list}"

            return self.create_success_result(
                message=message,
                data={
                    "action": "exits",
                    "exits": exits,
                    "room_id": current_room_id
                }
            )

        except Exception as e:
            logger.error(f"출구 확인 명령어 실행 중 오류: {e}")
            return self.create_error_result("출구 정보를 확인하는 중 오류가 발생했습니다.")