# -*- coding: utf-8 -*-
"""관리자 전용 명령어들"""

import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from .base import BaseCommand, CommandResult, CommandResultType
from .utils import get_user_locale
from ..core.types import SessionType
from ..core.localization import get_localization_manager
from ..game.models import Room, GameObject

logger = logging.getLogger(__name__)
I18N = get_localization_manager()


class AdminCommand(BaseCommand):
    """관리자 명령어 기본 클래스"""

    def __init__(self, name: str, description: str, aliases: List[str] = None, usage: str = ""):
        super().__init__(name, aliases, description, usage, admin_only=True)
        self.admin_required = True

    def check_admin_permission(self, session: SessionType) -> bool:
        """관리자 권한 확인"""
        if not session.player or not session.player.is_admin:
            return False
        return True

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        """관리자 권한 확인 후 명령어 실행"""
        if not self.check_admin_permission(session):
            locale = get_user_locale(session)
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.permission_denied", locale)
            )

        return await self.execute_admin(session, args)

    async def execute_admin(self, session: SessionType, args: List[str]) -> CommandResult:
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

    async def execute_admin(self, session: SessionType, args: List[str]) -> CommandResult:
        """방 생성 실행"""
        locale = get_user_locale(session)
        if len(args) < 1:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.createroom.usage", locale)
            )

        room_id = args[0]
        default_desc = I18N.get_message("admin.createroom.default_desc", locale)
        room_description = " ".join(args[1:]) if len(args) > 1 else default_desc

        try:
            room_data = {
                "id": room_id,
                "description": {"ko": room_description, "en": room_description},
                "exits": {}
            }

            success = await session.game_engine.create_room_realtime(room_data, session)

            if success:
                return CommandResult(
                    result_type=CommandResultType.SUCCESS,
                    message=I18N.get_message("admin.createroom.success", locale, room_id=room_id),
                    broadcast=True,
                    broadcast_message=I18N.get_message("admin.createroom.broadcast", locale)
                )
            else:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message=I18N.get_message("admin.createroom.failed", locale)
                )

        except Exception as e:
            logger.error(f"방 생성 중 오류: {e}")
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.createroom.error", locale, error=str(e))
            )

    def get_help(self) -> str:
        return """
🏗️ **방 생성 명령어**

**사용법:** `createroom <방ID> [설명]`

**예시:**
- `createroom garden` - 기본 설명으로 방 생성
- `createroom library 조용한 도서관입니다` - 상세 설명과 함께 생성

**별칭:** `cr`, `mkroom`
**권한:** 관리자 전용
**참고:** 방 이름은 좌표로 자동 표시됩니다.
        """


class EditRoomCommand(AdminCommand):
    """방 편집 명령어"""

    def __init__(self):
        super().__init__(
            name="editroom",
            description="기존 방을 편집합니다",
            aliases=["er", "modroom"]
        )

    async def execute_admin(self, session: SessionType, args: List[str]) -> CommandResult:
        """방 편집 실행"""
        locale = get_user_locale(session)
        if len(args) < 2:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.editroom.usage", locale)
            )

        room_id = args[0]
        new_description = " ".join(args[1:])

        try:
            updates = {
                "description": {"ko": new_description, "en": new_description}
            }

            success = await session.game_engine.update_room_realtime(room_id, updates, session)

            if success:
                return CommandResult(
                    result_type=CommandResultType.SUCCESS,
                    message=I18N.get_message("admin.editroom.success", locale, room_id=room_id),
                    broadcast=True,
                    broadcast_message=I18N.get_message("admin.editroom.broadcast", locale, room_id=room_id)
                )
            else:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message=I18N.get_message("admin.editroom.failed", locale)
                )

        except Exception as e:
            logger.error(f"방 편집 중 오류: {e}")
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.editroom.error", locale, error=str(e))
            )

    def get_help(self) -> str:
        return """
🔧 **방 편집 명령어**

**사용법:** `editroom <방ID> <설명>`

**예시:**
- `editroom garden 아름다운 정원입니다` - 방 설명 변경
- `editroom library 고요한 분위기의 도서관` - 방 설명 변경

**별칭:** `er`, `modroom`
**권한:** 관리자 전용
**참고:** 방 이름은 좌표로 자동 표시되므로 설명만 편집 가능합니다.
        """


class CreateExitCommand(AdminCommand):
    """출구 생성 명령어"""

    def __init__(self):
        super().__init__(
            name="createexit",
            description="방 사이에 출구를 생성합니다",
            aliases=["ce", "mkexit"]
        )

    async def execute_admin(self, session: SessionType, args: List[str]) -> CommandResult:
        """출구 생성 실행"""
        locale = get_user_locale(session)
        if len(args) < 3:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.createexit.usage", locale)
            )

        from_room = args[0]
        direction = args[1].lower()
        to_room = args[2]

        valid_directions = ['north', 'south', 'east', 'west', 'up', 'down',
                          'northeast', 'northwest', 'southeast', 'southwest']

        if direction not in valid_directions:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.createexit.invalid_direction", locale, directions=', '.join(valid_directions))
            )

        try:
            updates = {
                "exits": {direction: to_room}
            }

            success = await session.game_engine.update_room_realtime(from_room, updates, session)

            if success:
                return CommandResult(
                    result_type=CommandResultType.SUCCESS,
                    message=I18N.get_message("admin.createexit.success", locale, from_room=from_room, to_room=to_room, direction=direction),
                    broadcast=True,
                    broadcast_message=I18N.get_message("admin.createexit.broadcast", locale)
                )
            else:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message=I18N.get_message("admin.createexit.failed", locale)
                )

        except Exception as e:
            logger.error(f"출구 생성 중 오류: {e}")
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.createexit.error", locale, error=str(e))
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

    async def execute_admin(self, session: SessionType, args: List[str]) -> CommandResult:
        """객체 생성 실행"""
        locale = get_user_locale(session)
        if len(args) < 3:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.createobject.usage", locale)
            )

        obj_id = args[0]
        obj_name = args[1]
        obj_type = args[2].lower()
        location_id = args[3] if len(args) > 3 else session.current_room_id

        valid_types = ['item', 'weapon', 'armor', 'food', 'book', 'key', 'treasure', 'furniture', 'container']

        if obj_type not in valid_types:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.createobject.invalid_type", locale, types=', '.join(valid_types))
            )

        try:
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
                    message=I18N.get_message("admin.createobject.success", locale, obj_name=obj_name, obj_id=obj_id, location_id=location_id),
                    broadcast=True,
                    broadcast_message=I18N.get_message("admin.createobject.broadcast", locale, obj_name=obj_name)
                )
            else:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message=I18N.get_message("admin.createobject.failed", locale)
                )

        except Exception as e:
            logger.error(f"객체 생성 중 오류: {e}")
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.createobject.error", locale, error=str(e))
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

    async def execute_admin(self, session: SessionType, args: List[str]) -> CommandResult:
        """플레이어 추방 실행"""
        locale = get_user_locale(session)
        if len(args) < 1:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.kick.usage", locale)
            )

        target_username = args[0]
        reason = " ".join(args[1:]) if len(args) > 1 else I18N.get_message("admin.kick.default_reason", locale)

        if target_username == session.player.username:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.kick.self", locale)
            )

        try:
            target_session = None
            for sess in session.game_engine.session_manager.get_authenticated_sessions().values():
                if sess.player and sess.player.username == target_username:
                    target_session = sess
                    break

            if not target_session:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message=I18N.get_message("admin.kick.not_found", locale, username=target_username)
                )

            if target_session.player.is_admin:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message=I18N.get_message("admin.kick.is_admin", locale)
                )

            target_locale = get_user_locale(target_session)
            await target_session.send_message({
                "type": "system_message",
                "message": I18N.get_message("admin.kick.target_msg", target_locale, reason=reason),
                "disconnect": True
            })

            await session.game_engine.session_manager.remove_session(
                target_session.session_id,
                f"Admin kick: {reason}"
            )

            return CommandResult(
                result_type=CommandResultType.SUCCESS,
                message=I18N.get_message("admin.kick.success", locale, username=target_username, reason=reason),
                broadcast=True,
                broadcast_message=I18N.get_message("admin.kick.broadcast", locale, username=target_username)
            )

        except Exception as e:
            logger.error(f"플레이어 추방 중 오류: {e}")
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.kick.error", locale, error=str(e))
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
    """좌표로 바로 이동하는 명령어"""

    def __init__(self):
        super().__init__(
            name="goto",
            description="지정한 좌표로 바로 이동합니다",
            aliases=["tp", "teleport", "warp"]
        )

    async def execute_admin(self, session: SessionType, args: List[str]) -> CommandResult:
        """좌표로 이동 실행"""
        locale = get_user_locale(session)
        if len(args) < 2:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.goto.usage", locale)
            )

        if getattr(session, 'in_combat', False):
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.in_combat", locale)
            )

        try:
            x = int(args[0])
            y = int(args[1])
        except ValueError:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.goto.invalid_coords", locale)
            )

        try:
            cursor = await session.game_engine.db_manager.execute(
                "SELECT id FROM rooms WHERE x = ? AND y = ?",
                (x, y)
            )
            room_row = await cursor.fetchone()

            if not room_row:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message=I18N.get_message("admin.goto.room_not_found", locale, x=x, y=y)
                )

            target_room_id = room_row[0]
            target_room = await session.game_engine.world_manager.get_room(target_room_id)

            if not target_room:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message=I18N.get_message("admin.goto.room_not_found", locale, x=x, y=y)
                )

            if hasattr(session, 'current_room_id') and session.current_room_id:
                await session.game_engine.broadcast_to_room(
                    session.current_room_id,
                    {
                        "type": "room_message",
                        "message": I18N.get_message("admin.goto.leave_msg", locale, username=session.player.username)
                    },
                    exclude_session=session.session_id
                )

            success = await session.game_engine.movement_manager.move_player_to_room(session, target_room_id)

            if not success:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message=I18N.get_message("admin.goto.move_failed", locale, x=x, y=y)
                )

            await session.game_engine.broadcast_to_room(
                target_room_id,
                {
                    "type": "room_message",
                    "message": I18N.get_message("admin.goto.arrive_msg", locale, username=session.player.get_display_name())
                },
                exclude_session=session.session_id
            )

            return CommandResult(
                result_type=CommandResultType.SUCCESS,
                message=I18N.get_message("admin.goto.success", locale, x=x, y=y)
            )

        except Exception as e:
            logger.error(f"방 이동 중 오류: {e}")
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.goto.error", locale, error=str(e))
            )

    def get_help(self) -> str:
        return """
✨ **순간이동 명령어**

**사용법:** `goto <x좌표> <y좌표>`

**설명:**
관리자 권한으로 지정한 좌표로 즉시 이동합니다.
이동 시 현재 방의 다른 플레이어들에게 알림이 전송됩니다.

**예시:**
- `goto 0 0` - (0, 0) 좌표로 이동
- `goto 5 7` - (5, 7) 좌표로 이동
- `goto 3 4` - (3, 4) 좌표로 이동

**별칭:** `tp`, `teleport`, `warp`
**권한:** 관리자 전용

**주의사항:**
- 좌표는 숫자로 입력해야 합니다
- 존재하지 않는 좌표를 입력하면 이동할 수 없습니다
- 이동 시 다른 플레이어들에게 순간이동 메시지가 표시됩니다
        """


class RoomInfoCommand(AdminCommand):
    """방 정보 조회 명령어"""

    def __init__(self):
        super().__init__(
            name="info",
            description="현재 방의 상세 정보를 표시합니다",
            aliases=["roominfo", "ri"]
        )

    async def execute_admin(self, session: SessionType, args: List[str]) -> CommandResult:
        """방 정보 조회 실행"""
        locale = get_user_locale(session)
        if not session.current_room_id:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.roominfo.no_room", locale)
            )

        try:
            cursor = await session.game_engine.db_manager.execute(
                "SELECT * FROM rooms WHERE id = ?",
                (session.current_room_id,)
            )
            room_row = await cursor.fetchone()

            if not room_row:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message=I18N.get_message("admin.roominfo.not_in_db", locale, room_id=session.current_room_id)
                )

            # 컬럼 이름 가져오기
            column_names = [description[0] for description in cursor.description]

            # 방 정보를 딕셔너리로 변환
            room_data = dict(zip(column_names, room_row))

            # 정보 포맷팅
            info_lines = ["🔍 방 상세 정보", ""]

            for key, value in room_data.items():
                # exits는 JSON 문자열이므로 파싱하여 표시
                if key == "exits":
                    try:
                        exits_dict = json.loads(value) if isinstance(value, str) else value
                        if exits_dict:
                            exits_str = ", ".join([f"{direction} → {target}" for direction, target in exits_dict.items()])
                            info_lines.append(f"{key}: {exits_str}")
                        else:
                            info_lines.append(f"{key}: (없음)")
                    except (json.JSONDecodeError, TypeError):
                        info_lines.append(f"{key}: {value}")
                else:
                    # None 값 처리
                    display_value = value if value is not None else "(null)"
                    info_lines.append(f"{key}: {display_value}")

            # 현재 방의 좌표 가져오기 (몬스터 정보와 enter 연결 정보에서 공통 사용)
            room_coords = None
            try:
                room_cursor = await session.game_engine.db_manager.execute(
                    "SELECT x, y FROM rooms WHERE id = ?",
                    (session.current_room_id,)
                )
                room_coords = await room_cursor.fetchone()
            except Exception as coords_error:
                logger.error(f"방 좌표 조회 중 오류: {coords_error}")

            # 방에 있는 몬스터 정보 추가
            try:

                if room_coords:
                    room_x, room_y = room_coords
                    monster_cursor = await session.game_engine.db_manager.execute(
                        "SELECT * FROM monsters WHERE x = ? AND y = ? AND is_alive = 1",
                        (room_x, room_y)
                    )
                else:
                    # 좌표를 찾을 수 없으면 빈 결과 반환
                    monster_cursor = await session.game_engine.db_manager.execute(
                        "SELECT * FROM monsters WHERE 1 = 0"
                    )
                monster_rows = await monster_cursor.fetchall()

                if monster_rows:
                    info_lines.extend(["", "🐾 방 내 몬스터 정보", ""])

                    # 몬스터 컬럼 이름 가져오기
                    monster_column_names = [description[0] for description in monster_cursor.description]

                    for i, monster_row in enumerate(monster_rows, 1):
                        monster_data = dict(zip(monster_column_names, monster_row))

                        # 몬스터 ID 단축 표시
                        short_id = monster_data['id'].split('-')[-1] if '-' in monster_data['id'] else monster_data['id']
                        info_lines.append(f"몬스터 #{i} ({short_id}):")

                        for key, value in monster_data.items():
                            if key in ['properties', 'drop_items']:
                                # JSON 필드 파싱
                                try:
                                    parsed_value = json.loads(value) if isinstance(value, str) else value
                                    if parsed_value:
                                        info_lines.append(f"  {key}: {json.dumps(parsed_value, ensure_ascii=False, indent=2)}")
                                    else:
                                        info_lines.append(f"  {key}: (없음)")
                                except (json.JSONDecodeError, TypeError):
                                    info_lines.append(f"  {key}: {value}")
                            elif key == 'name_ko':
                                # 한국어 이름 우선 표시
                                info_lines.append(f"  name: {value}")
                            elif key == 'name_en':
                                # 영어 이름은 건너뛰기 (한국어 이름으로 대체)
                                continue
                            else:
                                # None 값 처리
                                display_value = value if value is not None else "(null)"
                                info_lines.append(f"  {key}: {display_value}")

                        info_lines.append("")  # 몬스터 간 구분선
                else:
                    info_lines.extend(["", "🐾 방 내 몬스터: 없음"])

            except Exception as monster_error:
                logger.error(f"몬스터 정보 조회 중 오류: {monster_error}")
                info_lines.extend(["", f"❌ 몬스터 정보 조회 오류: {str(monster_error)}"])

            # enter 연결 정보 추가
            try:
                if room_coords:
                    room_x, room_y = room_coords
                    # 현재 방에서 나가는 enter 연결 조회
                    enter_cursor = await session.game_engine.db_manager.execute(
                        "SELECT to_x, to_y FROM room_connections WHERE from_x = ? AND from_y = ?",
                        (room_x, room_y)
                    )
                    enter_connections = await enter_cursor.fetchall()

                    # 현재 방으로 들어오는 enter 연결 조회
                    enter_in_cursor = await session.game_engine.db_manager.execute(
                        "SELECT from_x, from_y FROM room_connections WHERE to_x = ? AND to_y = ?",
                        (room_x, room_y)
                    )
                    enter_in_connections = await enter_in_cursor.fetchall()

                    if enter_connections or enter_in_connections:
                        info_lines.extend(["", "🚪 Enter 연결 정보", ""])

                        if enter_connections:
                            info_lines.append("나가는 연결:")
                            for to_x, to_y in enter_connections:
                                info_lines.append(f"  → ({to_x}, {to_y})")

                        if enter_in_connections:
                            info_lines.append("들어오는 연결:")
                            for from_x, from_y in enter_in_connections:
                                info_lines.append(f"  ← ({from_x}, {from_y})")
                    else:
                        info_lines.extend(["", "🚪 Enter 연결: 없음"])

            except Exception as enter_error:
                logger.error(f"Enter 연결 정보 조회 중 오류: {enter_error}")
                info_lines.extend(["", f"❌ Enter 연결 정보 조회 오류: {str(enter_error)}"])

            return CommandResult(
                result_type=CommandResultType.SUCCESS,
                message="\n".join(info_lines)
            )

        except Exception as e:
            logger.error(f"방 정보 조회 중 오류: {e}")
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.roominfo.error", locale, error=str(e))
            )

    def get_help(self) -> str:
        return """
🔍 **방 정보 조회 명령어**

**사용법:** `info`

**설명:**
현재 위치한 방의 데이터베이스 정보를 모두 표시합니다.
방 ID, 이름, 설명, 출구, 좌표, 생성/수정 시간 등 모든 필드를 확인할 수 있습니다.

**예시:**
- `info` - 현재 방의 상세 정보 표시

**별칭:** `roominfo`, `ri`
**권한:** 관리자 전용
        """



class AdminListCommand(AdminCommand):
    """관리자 명령어 목록"""

    def __init__(self):
        super().__init__(
            name="admin",
            description="관리자 명령어 목록을 표시합니다",
            aliases=["adminhelp", "adm"]
        )

    async def execute_admin(self, session: SessionType, args: List[str]) -> CommandResult:
        """관리자 명령어 목록 표시"""

        admin_commands = """
🔧 **관리자 명령어 목록**

**방 관리:**
- `createroom <ID> [설명]` - 새 방 생성
- `editroom <ID> <설명>` - 방 설명 편집
- `createexit <출발방> <방향> <도착방>` - 출구 생성
- `goto <x> <y>` - 지정한 좌표로 순간이동
- `info` - 현재 방의 상세 정보 표시

**객체 관리:**
- `createobject <ID> <이름> <타입> [위치]` - 객체 생성

**몬스터 관리:**
- `spawnmonster <template_id> [room_id]` - 템플릿에서 몬스터 생성
- `templates` - 사용 가능한 몬스터 템플릿 목록

**아이템 관리:**
- `spawnitem <template_id> [room_id]` - 템플릿에서 아이템 생성
- `itemtemplates` - 사용 가능한 아이템 템플릿 목록

**플레이어 관리:**
- `kick <플레이어명> [사유]` - 플레이어 추방
- `adminchangename <사용자명> <새이름>` - 플레이어 이름 변경

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


class SpawnMonsterCommand(AdminCommand):
    """템플릿에서 몬스터 생성 명령어"""

    def __init__(self):
        super().__init__(
            name="spawnmonster",
            description="템플릿에서 몬스터를 생성합니다",
            aliases=["spawn", "createmonster"],
            usage="spawnmonster <template_id> [room_id]"
        )

    async def execute_admin(self, session: SessionType, args: List[str]) -> CommandResult:
        """템플릿에서 몬스터 생성"""
        locale = get_user_locale(session)
        if not args:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.spawn.usage", locale)
            )

        template_id = args[0]
        room_id = args[1] if len(args) > 1 else session.current_room_id

        if not room_id:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.spawn.no_room", locale)
            )

        try:
            game_engine = session.game_engine
            if not game_engine:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message=I18N.get_message("admin.no_game_engine", locale)
                )

            room = await game_engine.world_manager.get_room(room_id)
            if not room:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message=I18N.get_message("admin.spawn.room_not_found", locale, room_id=room_id)
                )

            monster = await game_engine.world_manager._monster_manager._spawn_monster_from_template(
                room_id=room_id,
                template_id=template_id
            )

            if not monster:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message=I18N.get_message("admin.spawn.template_failed", locale, template_id=template_id)
                )

            coord_info = f"({room.x}, {room.y})" if hasattr(room, 'x') and hasattr(room, 'y') else room_id

            return CommandResult(
                result_type=CommandResultType.SUCCESS,
                message=I18N.get_message("admin.spawn.success", locale, name=monster.get_localized_name(locale), coord=coord_info)
            )

        except Exception as e:
            logger.error(f"몬스터 생성 실패: {e}")
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.spawn.error", locale, error=str(e))
            )

    def get_help(self) -> str:
        return """
🐉 **몬스터 생성 도움말**

템플릿을 사용하여 몬스터를 생성합니다.

**사용법:** `spawnmonster <template_id> [room_id]`

**매개변수:**
- `template_id`: 몬스터 템플릿 ID (예: template_forest_goblin)
- `room_id`: 생성할 방 ID (생략 시 현재 방)

**예시:**
- `spawnmonster template_forest_goblin` - 현재 방에 숲 고블린 생성
- `spawnmonster template_small_rat room_123` - 특정 방에 작은 쥐 생성

**별칭:** `spawn`, `createmonster`
**권한:** 관리자 전용

**사용 가능한 템플릿:**
- template_small_rat (작은 쥐)
- template_forest_goblin (숲 고블린)
- template_town_guard (마을 경비병)
- template_harbor_guide (항구 안내인)
- template_square_guard (광장 경비병)
- template_light_armored_guard (경장 경비병)
        """


class ListTemplatesCommand(AdminCommand):
    """템플릿 목록 조회 명령어"""

    def __init__(self):
        super().__init__(
            name="templates",
            description="사용 가능한 몬스터 템플릿 목록을 표시합니다",
            aliases=["listtemplates", "tmpl"]
        )

    async def execute_admin(self, session: SessionType, args: List[str]) -> CommandResult:
        """템플릿 목록 표시"""
        locale = get_user_locale(session)
        try:
            game_engine = session.game_engine
            if not game_engine:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message=I18N.get_message("admin.no_game_engine", locale)
                )

            template_loader = game_engine.world_manager._monster_manager._template_loader
            templates = template_loader.get_all_monster_templates()

            if not templates:
                return CommandResult(
                    result_type=CommandResultType.INFO,
                    message=I18N.get_message("admin.templates.empty", locale)
                )

            template_list = "📋 Monster Templates:\n\n"

            for template_id, template_data in templates.items():
                name_ko = template_data.get('name', {}).get('ko', '이름 없음')
                name_en = template_data.get('name', {}).get('en', 'No name')
                monster_type = template_data.get('monster_type', 'UNKNOWN')
                level = template_data.get('stats', {}).get('level', 1)

                template_list += f"• {template_id}\n"
                template_list += f"  {name_ko} ({name_en})\n"
                template_list += f"  type: {monster_type}, level: {level}\n\n"

            template_list += f"Total: {len(templates)} templates\n"
            template_list += "\nUsage: `spawnmonster <template_id> [room_id]`"

            return CommandResult(
                result_type=CommandResultType.SUCCESS,
                message=template_list
            )

        except Exception as e:
            logger.error(f"템플릿 목록 조회 실패: {e}")
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.templates.error", locale, error=str(e))
            )

    def get_help(self) -> str:
        return """
📋 **템플릿 목록 도움말**

현재 로드된 몬스터 템플릿 목록을 표시합니다.

**사용법:** `templates`

**별칭:** `listtemplates`, `tmpl`
**권한:** 관리자 전용

각 템플릿의 ID, 이름, 타입, 레벨 정보를 확인할 수 있습니다.
        """

class SpawnItemCommand(AdminCommand):
    """템플릿에서 아이템 생성 명령어"""

    def __init__(self):
        super().__init__(
            name="spawnitem",
            description="템플릿에서 아이템을 생성합니다",
            aliases=["createitem", "item"],
            usage="spawnitem <template_id> [room_id]"
        )

    async def execute_admin(self, session: SessionType, args: List[str]) -> CommandResult:
        """템플릿에서 아이템 생성"""
        locale = get_user_locale(session)
        if not args:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.spawnitem.usage", locale)
            )

        template_id = args[0]
        room_id = args[1] if len(args) > 1 else session.current_room_id

        if not room_id:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.spawnitem.no_room", locale)
            )

        try:
            game_engine = session.game_engine
            if not game_engine:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message=I18N.get_message("admin.no_game_engine", locale)
                )

            room = await game_engine.world_manager.get_room(room_id)
            if not room:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message=I18N.get_message("admin.spawnitem.room_not_found", locale, room_id=room_id)
                )

            from uuid import uuid4
            item_id = str(uuid4())

            template_loader = game_engine.world_manager._monster_manager._template_loader
            item = template_loader.create_item_from_template(
                template_id=template_id,
                item_id=item_id,
                location_type="room",
                location_id=room_id
            )

            if not item:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message=I18N.get_message("admin.spawnitem.template_failed", locale, template_id=template_id)
                )

            success = await game_engine.create_object_realtime(item.to_dict(), session)
            if not success:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message=I18N.get_message("admin.spawnitem.save_failed", locale)
                )

            coord_info = f"({room.x}, {room.y})" if hasattr(room, 'x') and hasattr(room, 'y') else room_id
            item_name = item.get_localized_name(locale)

            return CommandResult(
                result_type=CommandResultType.SUCCESS,
                message=I18N.get_message("admin.spawnitem.success", locale, name=item_name, coord=coord_info)
            )

        except Exception as e:
            logger.error(f"아이템 생성 실패: {e}")
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.spawnitem.error", locale, error=str(e))
            )

    def get_help(self) -> str:
        return """
📦 **아이템 생성 도움말**

템플릿을 사용하여 아이템을 생성합니다.

**사용법:** `spawnitem <template_id> [room_id]`

**매개변수:**
- `template_id`: 아이템 템플릿 ID (예: gold_coin)
- `room_id`: 생성할 방 ID (생략 시 현재 방)

**예시:**
- `spawnitem gold_coin` - 현재 방에 골드 생성
- `spawnitem essence_of_life room_123` - 특정 방에 생명의 정수 생성

**별칭:** `createitem`, `item`
**권한:** 관리자 전용

**사용 가능한 템플릿:**
- gold_coin (골드)
- essence_of_life (생명의 정수)
- 기타 configs/items/ 디렉토리의 템플릿들
        """


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

                template_list += f"• {template_id}\n"
                template_list += f"  {name_ko} ({name_en})\n"
                template_list += f"  type: {object_type}, category: {category}\n\n"

            template_list += f"Total: {len(templates)} item templates\n"
            template_list += "\nUsage: `spawnitem <template_id> [room_id]`"

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

    def get_help(self) -> str:
        return """
📦 **아이템 템플릿 목록 도움말**

현재 로드된 아이템 템플릿 목록을 표시합니다.

**사용법:** `itemtemplates`

**별칭:** `listitemtemplates`, `items`
**권한:** 관리자 전용

각 템플릿의 ID, 이름, 타입, 카테고리 정보를 확인할 수 있습니다.
        """


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
            if target_type == 'monster':
                target_name = target_entity.get_localized_name(locale)
                template_id = target_entity.get_property('template_id')
            else:
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