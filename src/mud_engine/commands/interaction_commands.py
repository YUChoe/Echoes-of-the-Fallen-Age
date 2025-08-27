# -*- coding: utf-8 -*-
"""플레이어 간 상호작용 명령어들"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from .base import BaseCommand, CommandResult, CommandResultType
from ..server.session import Session
from ..core.event_bus import Event, EventType

logger = logging.getLogger(__name__)


class EmoteCommand(BaseCommand):
    """감정 표현 명령어 - 플레이어가 감정이나 행동을 표현"""

    def __init__(self):
        super().__init__(
            name="emote",
            aliases=["em", "me"],
            description="감정이나 행동을 표현합니다",
            usage="emote <행동/감정>"
        )

    async def execute(self, session: Session, args: List[str]) -> CommandResult:
        logger.debug(f"EmoteCommand 실행: 플레이어={session.player.username}, args={args}")

        if not args:
            logger.warning(f"EmoteCommand: 빈 인수 - 플레이어={session.player.username}")
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message="표현할 감정이나 행동을 입력해주세요. 예: emote 웃는다"
            )

        emote_text = " ".join(args)
        player_name = session.player.username

        logger.info(f"플레이어 감정 표현: {player_name} -> {emote_text}")

        # 이벤트 발행
        await session.game_engine.event_bus.publish(Event(
            event_type=EventType.PLAYER_EMOTE,
            source=session.session_id,
            room_id=getattr(session, 'current_room_id', None),
            data={
                "player_id": session.player.id,
                "username": player_name,
                "emote_text": emote_text,
                "session_id": session.session_id
            }
        ))

        # 방 내 모든 플레이어에게 감정 표현 전송
        emote_message = f"* {player_name} {emote_text}"

        return CommandResult(
            result_type=CommandResultType.SUCCESS,
            message=f"당신은 {emote_text}",
            broadcast=True,
            broadcast_message=emote_message,
            room_only=True
        )


class GiveCommand(BaseCommand):
    """다른 플레이어에게 아이템 주기"""

    def __init__(self):
        super().__init__(
            name="give",
            aliases=["주기"],
            description="다른 플레이어에게 아이템을 줍니다",
            usage="give <아이템명> <플레이어명>"
        )

    async def execute(self, session: Session, args: List[str]) -> CommandResult:
        logger.debug(f"GiveCommand 실행: 플레이어={session.player.username}, args={args}")

        if len(args) < 2:
            logger.warning(f"GiveCommand: 잘못된 인수 개수 - 플레이어={session.player.username}, args={args}")
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message="사용법: give <아이템명> <플레이어명>"
            )

        item_name = args[0]
        target_player_name = args[1]

        logger.info(f"아이템 주기 시도: {session.player.username} -> {target_player_name} ({item_name})")

        # 대상 플레이어 찾기 (같은 방에 있는 플레이어만)
        target_session = None
        current_room_id = getattr(session, 'current_room_id', None)

        if not current_room_id:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message="현재 방 정보를 찾을 수 없습니다."
            )

        # 같은 방에 있는 플레이어들 중에서 대상 찾기
        for other_session in session.game_engine.session_manager.get_authenticated_sessions().values():
            if (other_session.player and
                other_session.player.username.lower() == target_player_name.lower() and
                getattr(other_session, 'current_room_id', None) == current_room_id and
                other_session.session_id != session.session_id):
                target_session = other_session
                break

        if not target_session:
            logger.warning(f"GiveCommand: 대상 플레이어를 찾을 수 없음 - {target_player_name} (방: {current_room_id})")
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=f"{target_player_name}님을 이 방에서 찾을 수 없습니다."
            )

        # 플레이어 인벤토리에서 아이템 찾기
        try:
            inventory_objects = await session.game_engine.world_manager.get_inventory_objects(session.player.id)
            target_object = None

            for obj in inventory_objects:
                if obj.get_localized_name(session.locale).lower() == item_name.lower():
                    target_object = obj
                    break

            if not target_object:
                logger.warning(f"GiveCommand: 아이템을 찾을 수 없음 - {item_name} (플레이어: {session.player.username})")
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message=f"'{item_name}' 아이템을 인벤토리에서 찾을 수 없습니다."
                )

            # 아이템을 대상 플레이어의 인벤토리로 이동
            success = await session.game_engine.world_manager.move_object_to_inventory(
                target_object.id, target_session.player.id
            )

            if not success:
                logger.error(f"GiveCommand: 아이템 이동 실패 - {item_name} ({session.player.username} -> {target_player_name})")
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message="아이템 전달에 실패했습니다."
                )

            # 이벤트 발행
            await session.game_engine.event_bus.publish(Event(
                event_type=EventType.PLAYER_GIVE,
                source=session.session_id,
                room_id=current_room_id,
                data={
                    "giver_id": session.player.id,
                    "giver_name": session.player.username,
                    "receiver_id": target_session.player.id,
                    "receiver_name": target_session.player.username,
                    "item_id": target_object.id,
                    "item_name": target_object.get_localized_name(session.locale)
                }
            ))

            # 대상 플레이어에게 알림
            await target_session.send_message({
                "type": "item_received",
                "message": f"🎁 {session.player.username}님이 '{target_object.get_localized_name(target_session.locale)}'을(를) 주었습니다.",
                "item": {
                    "id": target_object.id,
                    "name": target_object.get_localized_name(target_session.locale)
                }
            })

            return CommandResult(
                result_type=CommandResultType.SUCCESS,
                message=f"'{target_object.get_localized_name(session.locale)}'을(를) {target_session.player.username}님에게 주었습니다.",
                broadcast=True,
                broadcast_message=f"🎁 {session.player.username}님이 {target_session.player.username}님에게 '{target_object.get_localized_name(session.locale)}'을(를) 주었습니다.",
                room_only=True
            )

        except Exception as e:
            logger.error(f"아이템 주기 실패: {e}", exc_info=True)
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message="아이템 전달 중 오류가 발생했습니다."
            )


class FollowCommand(BaseCommand):
    """다른 플레이어 따라가기"""

    def __init__(self):
        super().__init__(
            name="follow",
            aliases=["따라가기"],
            description="다른 플레이어를 따라갑니다",
            usage="follow <플레이어명> 또는 follow stop (따라가기 중지)"
        )

    async def execute(self, session: Session, args: List[str]) -> CommandResult:
        logger.debug(f"FollowCommand 실행: 플레이어={session.player.username}, args={args}")

        if not args:
            logger.warning(f"FollowCommand: 빈 인수 - 플레이어={session.player.username}")
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message="사용법: follow <플레이어명> 또는 follow stop"
            )

        if args[0].lower() == "stop":
            # 따라가기 중지
            if hasattr(session, 'following_player'):
                followed_player = session.following_player
                delattr(session, 'following_player')

                logger.info(f"따라가기 중지: {session.player.username} (대상: {followed_player})")
                return CommandResult(
                    result_type=CommandResultType.SUCCESS,
                    message=f"{followed_player}님 따라가기를 중지했습니다."
                )
            else:
                logger.warning(f"FollowCommand: 따라가는 플레이어 없음 - {session.player.username}")
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message="현재 따라가고 있는 플레이어가 없습니다."
                )

        target_player_name = args[0]
        current_room_id = getattr(session, 'current_room_id', None)

        if not current_room_id:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message="현재 방 정보를 찾을 수 없습니다."
            )

        # 대상 플레이어 찾기
        target_session = None
        for other_session in session.game_engine.session_manager.get_authenticated_sessions().values():
            if (other_session.player and
                other_session.player.username.lower() == target_player_name.lower() and
                getattr(other_session, 'current_room_id', None) == current_room_id and
                other_session.session_id != session.session_id):
                target_session = other_session
                break

        if not target_session:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=f"{target_player_name}님을 이 방에서 찾을 수 없습니다."
            )

        # 따라가기 설정
        session.following_player = target_session.player.username

        logger.info(f"따라가기 시작: {session.player.username} -> {target_session.player.username} (방: {current_room_id})")

        # 이벤트 발행
        await session.game_engine.event_bus.publish(Event(
            event_type=EventType.PLAYER_FOLLOW,
            source=session.session_id,
            room_id=current_room_id,
            data={
                "follower_id": session.player.id,
                "follower_name": session.player.username,
                "target_id": target_session.player.id,
                "target_name": target_session.player.username
            }
        ))

        # 대상 플레이어에게 알림
        await target_session.send_message({
            "type": "being_followed",
            "message": f"👥 {session.player.username}님이 당신을 따라가기 시작했습니다."
        })

        return CommandResult(
            result_type=CommandResultType.SUCCESS,
            message=f"{target_session.player.username}님을 따라가기 시작했습니다.",
            broadcast=True,
            broadcast_message=f"👥 {session.player.username}님이 {target_session.player.username}님을 따라가기 시작했습니다.",
            room_only=True
        )


class WhisperCommand(BaseCommand):
    """다른 플레이어에게 귓속말"""

    def __init__(self):
        super().__init__(
            name="whisper",
            aliases=["귓속말", "w"],
            description="다른 플레이어에게 귓속말을 합니다",
            usage="whisper <플레이어명> <메시지>"
        )

    async def execute(self, session: Session, args: List[str]) -> CommandResult:
        logger.debug(f"WhisperCommand 실행: 플레이어={session.player.username}, args={args}")

        if len(args) < 2:
            logger.warning(f"WhisperCommand: 잘못된 인수 개수 - 플레이어={session.player.username}, args={args}")
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message="사용법: whisper <플레이어명> <메시지>"
            )

        target_player_name = args[0]
        message = " ".join(args[1:])

        logger.info(f"귓속말 시도: {session.player.username} -> {target_player_name}")
        current_room_id = getattr(session, 'current_room_id', None)

        if not current_room_id:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message="현재 방 정보를 찾을 수 없습니다."
            )

        # 대상 플레이어 찾기 (같은 방에 있는 플레이어만)
        target_session = None
        for other_session in session.game_engine.session_manager.get_authenticated_sessions().values():
            if (other_session.player and
                other_session.player.username.lower() == target_player_name.lower() and
                getattr(other_session, 'current_room_id', None) == current_room_id and
                other_session.session_id != session.session_id):
                target_session = other_session
                break

        if not target_session:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=f"{target_player_name}님을 이 방에서 찾을 수 없습니다."
            )

        # 대상 플레이어에게 귓속말 전송
        await target_session.send_message({
            "type": "whisper_received",
            "message": f"💬 {session.player.username}님이 귓속말: {message}",
            "from": session.player.username,
            "timestamp": datetime.now().isoformat()
        })

        # 방의 다른 플레이어들에게는 귓속말이 있었다는 것만 알림
        whisper_notice = f"💭 {session.player.username}님이 {target_session.player.username}님에게 귓속말을 했습니다."

        return CommandResult(
            result_type=CommandResultType.SUCCESS,
            message=f"{target_session.player.username}님에게 귓속말: {message}",
            broadcast=True,
            broadcast_message=whisper_notice,
            room_only=True
        )


class PlayersCommand(BaseCommand):
    """현재 방에 있는 플레이어 목록 표시"""

    def __init__(self):
        super().__init__(
            name="players",
            aliases=["방사람", "here"],
            description="현재 방에 있는 플레이어들을 표시합니다",
            usage="players"
        )

    async def execute(self, session: Session, args: List[str]) -> CommandResult:
        logger.debug(f"PlayersCommand 실행: 플레이어={session.player.username}")

        current_room_id = getattr(session, 'current_room_id', None)

        if not current_room_id:
            logger.error(f"PlayersCommand: 현재 방 정보 없음 - 플레이어={session.player.username}")
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message="현재 방 정보를 찾을 수 없습니다."
            )

        # 같은 방에 있는 플레이어들 찾기
        players_in_room = []
        for other_session in session.game_engine.session_manager.get_authenticated_sessions().values():
            if (other_session.player and
                getattr(other_session, 'current_room_id', None) == current_room_id):

                player_info = {
                    "name": other_session.player.username,
                    "is_self": other_session.session_id == session.session_id,
                    "following": getattr(other_session, 'following_player', None)
                }
                players_in_room.append(player_info)

        if not players_in_room:
            logger.info(f"PlayersCommand: 빈 방 - {current_room_id}")
            return CommandResult(
                result_type=CommandResultType.SUCCESS,
                message="이 방에는 아무도 없습니다."
            )

        # 플레이어 목록 생성
        player_list = []
        for player in players_in_room:
            if player["is_self"]:
                player_text = f"👤 {player['name']} (나)"
            else:
                player_text = f"👤 {player['name']}"

            if player["following"]:
                player_text += f" (→ {player['following']}님을 따라가는 중)"

            player_list.append(player_text)

        message = f"📍 현재 방에 있는 플레이어들 ({len(players_in_room)}명):\n" + "\n".join(player_list)

        logger.info(f"PlayersCommand 완료: 방={current_room_id}, 플레이어 수={len(players_in_room)}")

        return CommandResult(
            result_type=CommandResultType.SUCCESS,
            message=message,
            data={
                "players": players_in_room,
                "room_id": current_room_id
            }
        )