# -*- coding: utf-8 -*-
"""관리자 전용 명령어들"""

import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from .base import BaseCommand, CommandResult, CommandResultType
from ..server.session import Session
from ..game.models import Room, GameObject

logger = logging.getLogger(__name__)


class AdminCommand(BaseCommand):
    """관리자 명령어 기본 클래스"""

    def __init__(self, name: str, description: str, aliases: List[str] = None, usage: str = ""):
        super().__init__(name, aliases, description, usage, admin_only=True)
        self.admin_required = True

    def check_admin_permission(self, session: Session) -> bool:
        """관리자 권한 확인"""
        if not session.player or not session.player.is_admin:
            return False
        return True

    async def execute(self, session: Session, args: List[str]) -> CommandResult:
        """관리자 권한 확인 후 명령어 실행"""
        if not self.check_admin_permission(session):
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message="❌ 관리자 권한이 필요한 명령어입니다."
            )

        return await self.execute_admin(session, args)

    async def execute_admin(self, session: Session, args: List[str]) -> CommandResult:
        """관리자 명령어 실행 (하위 클래스에서 구현)"""
        raise NotImplementedError


class CreateRoomCommand(AdminCommand):
    """실시간 방 생성 명령어"""

    def __init__(self):
        super().__init__(
            name="createroom",
            description="새로운 방을 생성합니다",
            aliases=["cr", "mkroom"]
        )

    async def execute_admin(self, session: Session, args: List[str]) -> CommandResult:
        """방 생성 실행"""
        if len(args) < 2:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message="사용법: createroom <방ID> <방이름> [설명]"
            )

        room_id = args[0]
        room_name = args[1]
        room_description = " ".join(args[2:]) if len(args) > 2 else f"{room_name}입니다."

        try:
            # 게임 엔진을 통해 방 생성
            room_data = {
                "id": room_id,
                "name": {"ko": room_name, "en": room_name},
                "description": {"ko": room_description, "en": room_description},
                "exits": {}
            }

            success = await session.game_engine.create_room_realtime(room_data, session)

            if success:
                return CommandResult(
                    result_type=CommandResultType.SUCCESS,
                    message=f"✅ 방 '{room_name}' (ID: {room_id})이 성공적으로 생성되었습니다.",
                    broadcast=True,
                    broadcast_message=f"🏗️ 관리자가 새로운 방 '{room_name}'을 생성했습니다."
                )
            else:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message="❌ 방 생성에 실패했습니다."
                )

        except Exception as e:
            logger.error(f"방 생성 중 오류: {e}")
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=f"❌ 방 생성 중 오류가 발생했습니다: {str(e)}"
            )

    def get_help(self) -> str:
        return """
🏗️ **방 생성 명령어**

**사용법:** `createroom <방ID> <방이름> [설명]`

**예시:**
- `createroom garden 정원` - 기본 설명으로 정원 방 생성
- `createroom library 도서관 조용한 도서관입니다` - 상세 설명과 함께 생성

**별칭:** `cr`, `mkroom`
**권한:** 관리자 전용
        """


class EditRoomCommand(AdminCommand):
    """방 편집 명령어"""

    def __init__(self):
        super().__init__(
            name="editroom",
            description="기존 방을 편집합니다",
            aliases=["er", "modroom"]
        )

    async def execute_admin(self, session: Session, args: List[str]) -> CommandResult:
        """방 편집 실행"""
        if len(args) < 3:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message="사용법: editroom <방ID> <속성> <값>"
            )

        room_id = args[0]
        property_name = args[1].lower()
        new_value = " ".join(args[2:])

        if property_name not in ["name", "description"]:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message="편집 가능한 속성: name, description"
            )

        try:
            # 방 편집 데이터 준비
            updates = {}
            if property_name == "name":
                updates["name"] = {"ko": new_value, "en": new_value}
            elif property_name == "description":
                updates["description"] = {"ko": new_value, "en": new_value}

            success = await session.game_engine.update_room_realtime(room_id, updates, session)

            if success:
                return CommandResult(
                    result_type=CommandResultType.SUCCESS,
                    message=f"✅ 방 {room_id}의 {property_name}이 '{new_value}'로 변경되었습니다.",
                    broadcast=True,
                    broadcast_message=f"🔧 관리자가 방 {room_id}을 수정했습니다."
                )
            else:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message="❌ 방 편집에 실패했습니다."
                )

        except Exception as e:
            logger.error(f"방 편집 중 오류: {e}")
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=f"❌ 방 편집 중 오류가 발생했습니다: {str(e)}"
            )

    def get_help(self) -> str:
        return """
🔧 **방 편집 명령어**

**사용법:** `editroom <방ID> <속성> <값>`

**편집 가능한 속성:**
- `name` - 방 이름
- `description` - 방 설명

**예시:**
- `editroom garden name 아름다운 정원` - 방 이름 변경
- `editroom library description 고요한 분위기의 도서관` - 방 설명 변경

**별칭:** `er`, `modroom`
**권한:** 관리자 전용
        """


class CreateExitCommand(AdminCommand):
    """출구 생성 명령어"""

    def __init__(self):
        super().__init__(
            name="createexit",
            description="방 사이에 출구를 생성합니다",
            aliases=["ce", "mkexit"]
        )

    async def execute_admin(self, session: Session, args: List[str]) -> CommandResult:
        """출구 생성 실행"""
        if len(args) < 3:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message="사용법: createexit <출발방ID> <방향> <도착방ID>"
            )

        from_room = args[0]
        direction = args[1].lower()
        to_room = args[2]

        # 유효한 방향인지 확인
        valid_directions = ['north', 'south', 'east', 'west', 'up', 'down',
                          'northeast', 'northwest', 'southeast', 'southwest']

        if direction not in valid_directions:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=f"유효하지 않은 방향입니다. 사용 가능한 방향: {', '.join(valid_directions)}"
            )

        try:
            # 출구 추가
            updates = {
                "exits": {direction: to_room}
            }

            success = await session.game_engine.update_room_realtime(from_room, updates, session)

            if success:
                return CommandResult(
                    result_type=CommandResultType.SUCCESS,
                    message=f"✅ {from_room}에서 {to_room}으로 가는 {direction} 출구가 생성되었습니다.",
                    broadcast=True,
                    broadcast_message=f"🚪 관리자가 새로운 출구를 생성했습니다."
                )
            else:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message="❌ 출구 생성에 실패했습니다."
                )

        except Exception as e:
            logger.error(f"출구 생성 중 오류: {e}")
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=f"❌ 출구 생성 중 오류가 발생했습니다: {str(e)}"
            )

    def get_help(self) -> str:
        return """
🚪 **출구 생성 명령어**

**사용법:** `createexit <출발방ID> <방향> <도착방ID>`

**사용 가능한 방향:**
- `north`, `south`, `east`, `west`
- `up`, `down`
- `northeast`, `northwest`, `southeast`, `southwest`

**예시:**
- `createexit garden north library` - 정원에서 북쪽으로 도서관 연결
- `createexit room_001 up room_002` - 1층에서 위쪽으로 2층 연결

**별칭:** `ce`, `mkexit`
**권한:** 관리자 전용
        """


class CreateObjectCommand(AdminCommand):
    """객체 생성 명령어"""

    def __init__(self):
        super().__init__(
            name="createobject",
            description="새로운 게임 객체를 생성합니다",
            aliases=["co", "mkobj"]
        )

    async def execute_admin(self, session: Session, args: List[str]) -> CommandResult:
        """객체 생성 실행"""
        if len(args) < 3:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message="사용법: createobject <객체ID> <객체이름> <타입> [위치ID]"
            )

        obj_id = args[0]
        obj_name = args[1]
        obj_type = args[2].lower()
        location_id = args[3] if len(args) > 3 else session.current_room_id

        # 유효한 객체 타입인지 확인
        valid_types = ['item', 'weapon', 'armor', 'food', 'book', 'key', 'treasure', 'furniture', 'container']

        if obj_type not in valid_types:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=f"유효하지 않은 객체 타입입니다. 사용 가능한 타입: {', '.join(valid_types)}"
            )

        try:
            # 객체 생성 데이터 준비
            object_data = {
                "id": obj_id,
                "name": {"ko": obj_name, "en": obj_name},
                "description": {"ko": f"{obj_name}입니다.", "en": f"This is {obj_name}."},
                "object_type": obj_type,
                "location_type": "room",
                "location_id": location_id,
                "properties": {}
            }

            success = await session.game_engine.create_object_realtime(object_data, session)

            if success:
                return CommandResult(
                    result_type=CommandResultType.SUCCESS,
                    message=f"✅ 객체 '{obj_name}' (ID: {obj_id})이 {location_id}에 생성되었습니다.",
                    broadcast=True,
                    broadcast_message=f"✨ 관리자가 새로운 객체 '{obj_name}'을 생성했습니다."
                )
            else:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message="❌ 객체 생성에 실패했습니다."
                )

        except Exception as e:
            logger.error(f"객체 생성 중 오류: {e}")
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=f"❌ 객체 생성 중 오류가 발생했습니다: {str(e)}"
            )

    def get_help(self) -> str:
        return """
✨ **객체 생성 명령어**

**사용법:** `createobject <객체ID> <객체이름> <타입> [위치ID]`

**사용 가능한 타입:**
- `item` - 일반 아이템
- `weapon` - 무기
- `armor` - 방어구
- `food` - 음식
- `book` - 책
- `key` - 열쇠
- `treasure` - 보물
- `furniture` - 가구
- `container` - 상자/컨테이너

**예시:**
- `createobject sword001 철검 weapon` - 현재 방에 철검 생성
- `createobject book001 마법서 book library` - 도서관에 마법서 생성

**별칭:** `co`, `mkobj`
**권한:** 관리자 전용
        """


class KickPlayerCommand(AdminCommand):
    """플레이어 추방 명령어"""

    def __init__(self):
        super().__init__(
            name="kick",
            description="플레이어를 서버에서 추방합니다",
            aliases=["kickplayer"]
        )

    async def execute_admin(self, session: Session, args: List[str]) -> CommandResult:
        """플레이어 추방 실행"""
        if len(args) < 1:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message="사용법: kick <플레이어명> [사유]"
            )

        target_username = args[0]
        reason = " ".join(args[1:]) if len(args) > 1 else "관리자에 의한 추방"

        # 자기 자신을 추방하려는 경우 방지
        if target_username == session.player.username:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message="❌ 자기 자신을 추방할 수 없습니다."
            )

        try:
            # 대상 플레이어 세션 찾기
            target_session = None
            for sess in session.game_engine.session_manager.get_authenticated_sessions().values():
                if sess.player and sess.player.username == target_username:
                    target_session = sess
                    break

            if not target_session:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message=f"❌ 플레이어 '{target_username}'을 찾을 수 없습니다."
                )

            # 대상이 관리자인 경우 추방 불가
            if target_session.player.is_admin:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message="❌ 다른 관리자를 추방할 수 없습니다."
                )

            # 추방 메시지 전송
            await target_session.send_message({
                "type": "system_message",
                "message": f"🚫 관리자에 의해 추방되었습니다. 사유: {reason}",
                "disconnect": True
            })

            # 세션 제거
            await session.game_engine.session_manager.remove_session(
                target_session.session_id,
                f"관리자 추방: {reason}"
            )

            return CommandResult(
                result_type=CommandResultType.SUCCESS,
                message=f"✅ 플레이어 '{target_username}'을 추방했습니다. 사유: {reason}",
                broadcast=True,
                broadcast_message=f"🚫 플레이어 '{target_username}'이 관리자에 의해 추방되었습니다."
            )

        except Exception as e:
            logger.error(f"플레이어 추방 중 오류: {e}")
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=f"❌ 플레이어 추방 중 오류가 발생했습니다: {str(e)}"
            )

    def get_help(self) -> str:
        return """
🚫 **플레이어 추방 명령어**

**사용법:** `kick <플레이어명> [사유]`

**예시:**
- `kick badplayer` - 기본 사유로 추방
- `kick spammer 스팸 행위` - 사유와 함께 추방

**주의사항:**
- 자기 자신은 추방할 수 없습니다
- 다른 관리자는 추방할 수 없습니다

**별칭:** `kickplayer`
**권한:** 관리자 전용
        """


class GotoCommand(AdminCommand):
    """방 ID로 바로 이동하는 명령어"""

    def __init__(self):
        super().__init__(
            name="goto",
            description="지정한 방 ID로 바로 이동합니다",
            aliases=["tp", "teleport", "warp"]
        )

    async def execute_admin(self, session: Session, args: List[str]) -> CommandResult:
        """방 ID로 이동 실행"""
        if len(args) < 1:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message="사용법: goto <방ID>"
            )

        target_room_id = args[0]

        try:
            # 대상 방이 존재하는지 확인
            target_room = await session.game_engine.world_manager.get_room(target_room_id)

            if not target_room:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message=f"❌ 방 ID '{target_room_id}'를 찾을 수 없습니다."
                )

            # 현재 방에서 플레이어 제거 알림
            if hasattr(session, 'current_room_id') and session.current_room_id:
                await session.game_engine.broadcast_to_room(
                    session.current_room_id,
                    {
                        "type": "room_message",
                        "message": f"✨ {session.player.username}이(가) 순간이동으로 사라졌습니다."
                    },
                    exclude_session=session.session_id
                )

            # PlayerMovementManager를 사용하여 플레이어 이동
            success = await session.game_engine.movement_manager.move_player_to_room(session, target_room_id)

            if not success:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message=f"❌ 방 '{target_room_id}'로 이동할 수 없습니다."
                )

            # 새 방에 도착 알림
            await session.game_engine.broadcast_to_room(
                target_room_id,
                {
                    "type": "room_message",
                    "message": f"✨ {session.player.username}이(가) 순간이동으로 나타났습니다."
                },
                exclude_session=session.session_id
            )

            # 방 이름 가져오기
            room_name = target_room.name.get('ko', target_room.name.get('en', '알 수 없는 방'))

            return CommandResult(
                result_type=CommandResultType.SUCCESS,
                message=f"✅ '{room_name}' (ID: {target_room_id})로 이동했습니다."
            )

        except Exception as e:
            logger.error(f"방 이동 중 오류: {e}")
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=f"❌ 방 이동 중 오류가 발생했습니다: {str(e)}"
            )

    def get_help(self) -> str:
        return """
✨ **순간이동 명령어**

**사용법:** `goto <방ID>`

**설명:**
관리자 권한으로 지정한 방 ID로 즉시 이동합니다.
이동 시 현재 방의 다른 플레이어들에게 알림이 전송됩니다.

**예시:**
- `goto town_square` - town_square 방으로 이동
- `goto forest_0_0` - forest_0_0 방으로 이동
- `goto library` - library 방으로 이동

**별칭:** `tp`, `teleport`, `warp`
**권한:** 관리자 전용

**주의사항:**
- 존재하지 않는 방 ID를 입력하면 이동할 수 없습니다
- 이동 시 다른 플레이어들에게 순간이동 메시지가 표시됩니다
        """


class AdminListCommand(AdminCommand):
    """관리자 명령어 목록"""

    def __init__(self):
        super().__init__(
            name="admin",
            description="관리자 명령어 목록을 표시합니다",
            aliases=["adminhelp", "adm"]
        )

    async def execute_admin(self, session: Session, args: List[str]) -> CommandResult:
        """관리자 명령어 목록 표시"""

        admin_commands = """
🔧 **관리자 명령어 목록**

**방 관리:**
- `createroom <ID> <이름> [설명]` - 새 방 생성
- `editroom <ID> <속성> <값>` - 방 편집
- `createexit <출발방> <방향> <도착방>` - 출구 생성
- `goto <방ID>` - 지정한 방으로 순간이동

**객체 관리:**
- `createobject <ID> <이름> <타입> [위치]` - 객체 생성

**플레이어 관리:**
- `kick <플레이어명> [사유]` - 플레이어 추방

**도움말:**
- `admin` - 이 목록 표시
- `help <명령어>` - 특정 명령어 도움말

각 명령어의 자세한 사용법은 `help <명령어>`로 확인하세요.
        """

        return CommandResult(
            result_type=CommandResultType.SUCCESS,
            message=admin_commands.strip()
        )

    def get_help(self) -> str:
        return """
🔧 **관리자 도움말**

관리자 전용 명령어들의 목록을 표시합니다.

**사용법:** `admin`

**별칭:** `adminhelp`, `adm`
**권한:** 관리자 전용
        """