# -*- coding: utf-8 -*-
"""관리자 명령어 목록"""

import logging
from typing import List

from .base import AdminCommand
from ..base import CommandResult, CommandResultType
from ...core.types import SessionType

logger = logging.getLogger(__name__)


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

    def get_help(self, locale: str = "en") -> str:
        return """
🔧 **관리자 도움말**

관리자 전용 명령어들의 목록을 표시합니다.

**사용법:** `admin`

**별칭:** `adminhelp`, `adm`
**권한:** 관리자 전용
        """
