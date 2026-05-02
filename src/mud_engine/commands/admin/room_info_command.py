# -*- coding: utf-8 -*-
"""방 정보 조회 명령어"""

import json
import logging
from typing import List, Optional, Tuple

from .base import AdminCommand
from ..base import CommandResult, CommandResultType
from ..utils import get_user_locale
from ...core.types import SessionType
from ...core.localization import get_localization_manager

logger = logging.getLogger(__name__)
I18N = get_localization_manager()


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
            info_lines = await self._append_monster_info(session, info_lines, room_coords)

            # enter 연결 정보 추가
            info_lines = await self._append_enter_connections(session, info_lines, room_coords)

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

    async def _append_monster_info(self, session: SessionType, info_lines: List[str], room_coords: Optional[Tuple[int, int]]) -> List[str]:
        """몬스터 정보를 info_lines에 추가"""
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

        return info_lines

    async def _append_enter_connections(self, session: SessionType, info_lines: List[str], room_coords: Optional[Tuple[int, int]]) -> List[str]:
        """enter 연결 정보를 info_lines에 추가"""
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

        return info_lines

    def get_help(self, locale: str = "en") -> str:
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
