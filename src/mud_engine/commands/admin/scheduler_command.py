# -*- coding: utf-8 -*-
"""스케줄러 관리 명령어"""

import logging
from typing import TYPE_CHECKING

from ..admin_commands import AdminCommand
from ..base import CommandResult, CommandResultType

if TYPE_CHECKING:
    from ...core.game_engine import GameEngine
    from ...core.types import SessionType

logger = logging.getLogger(__name__)


class SchedulerCommand(AdminCommand):
    """스케줄러 관리 명령어 (관리자 전용)"""

    def __init__(self):
        super().__init__(
            name="scheduler",
            description="글로벌 스케줄러 관리 (list/info/enable/disable)",
            aliases=["sched"]
        )

    async def execute_admin(self, session: 'SessionType', args: list):
        """
        스케줄러 관리 명령어 실행

        사용법:
            scheduler list - 등록된 이벤트 목록
            scheduler info <이벤트명> - 이벤트 상세 정보
            scheduler enable <이벤트명> - 이벤트 활성화
            scheduler disable <이벤트명> - 이벤트 비활성화
        """
        if not args:
            return await self._show_usage(session)

        subcommand = args[0].lower()
        game_engine = session.game_engine

        if subcommand == "list":
            return await self._list_events(session, game_engine)
        elif subcommand == "info" and len(args) >= 2:
            return await self._show_event_info(session, game_engine, args[1])
        elif subcommand == "enable" and len(args) >= 2:
            return await self._enable_event(session, game_engine, args[1])
        elif subcommand == "disable" and len(args) >= 2:
            return await self._disable_event(session, game_engine, args[1])
        else:
            return await self._show_usage(session)

    async def _show_usage(self, session: 'SessionType') -> CommandResult:
        """사용법 표시"""
        usage = """
📋 스케줄러 관리 명령어

사용법:
  scheduler list                  - 등록된 이벤트 목록
  scheduler info <이벤트명>       - 이벤트 상세 정보
  scheduler enable <이벤트명>     - 이벤트 활성화
  scheduler disable <이벤트명>    - 이벤트 비활성화

예시:
  scheduler list
  scheduler info monster_spawn
  scheduler enable monster_spawn
  scheduler disable cleanup_task
"""
        await session.send_message({
            "type": "system_message",
            "message": usage
        })
        return CommandResult(
            result_type=CommandResultType.SUCCESS,
            message="사용법 표시"
        )

    async def _list_events(self, session: 'SessionType', game_engine: 'GameEngine') -> CommandResult:
        """등록된 이벤트 목록 표시"""
        events = game_engine.scheduler_manager.list_events()

        if not events:
            await session.send_message({
                "type": "system_message",
                "message": "⚠️ 등록된 스케줄 이벤트가 없습니다."
            })
            return CommandResult(
                result_type=CommandResultType.SUCCESS,
                message="이벤트 없음"
            )

        lines = ["📋 등록된 스케줄 이벤트 목록:\n"]
        for event in events:
            status = "✅ 활성" if event["enabled"] else "❌ 비활성"
            intervals = ", ".join([f"{i}초" for i in event["intervals"]])
            lines.append(f"  • {event['name']}")
            lines.append(f"    상태: {status}")
            lines.append(f"    간격: {intervals}")
            lines.append(f"    실행: {event['run_count']}회 (오류: {event['error_count']}회)")
            if event["last_run"]:
                lines.append(f"    마지막 실행: {event['last_run']}")
            lines.append("")

        message = "\n".join(lines)
        await session.send_message({
            "type": "system_message",
            "message": message
        })
        return CommandResult(
            result_type=CommandResultType.SUCCESS,
            message=f"{len(events)}개 이벤트 조회"
        )

    async def _show_event_info(self, session: 'SessionType', game_engine: 'GameEngine', event_name: str) -> CommandResult:
        """이벤트 상세 정보 표시"""
        info = game_engine.scheduler_manager.get_event_info(event_name)

        if not info:
            await session.send_message({
                "type": "error",
                "message": f"❌ 이벤트를 찾을 수 없습니다: {event_name}"
            })
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message="이벤트 없음"
            )

        status = "✅ 활성" if info["enabled"] else "❌ 비활성"
        intervals = ", ".join([f"{i}초" for i in info["intervals"]])

        message = f"""
📊 이벤트 상세 정보: {info['name']}

상태: {status}
실행 간격: {intervals}
총 실행 횟수: {info['run_count']}회
오류 발생: {info['error_count']}회
마지막 실행: {info['last_run'] if info['last_run'] else '없음'}
"""
        await session.send_message({
            "type": "system_message",
            "message": message
        })
        return CommandResult(
            result_type=CommandResultType.SUCCESS,
            message="이벤트 정보 조회"
        )

    async def _enable_event(self, session: 'SessionType', game_engine: 'GameEngine', event_name: str) -> CommandResult:
        """이벤트 활성화"""
        success = game_engine.scheduler_manager.enable_event(event_name)

        if success:
            await session.send_message({
                "type": "success",
                "message": f"✅ 이벤트 '{event_name}'을(를) 활성화했습니다."
            })
            return CommandResult(
                result_type=CommandResultType.SUCCESS,
                message="이벤트 활성화"
            )
        else:
            await session.send_message({
                "type": "error",
                "message": f"❌ 이벤트를 찾을 수 없습니다: {event_name}"
            })
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message="이벤트 없음"
            )

    async def _disable_event(self, session: 'SessionType', game_engine: 'GameEngine', event_name: str) -> CommandResult:
        """이벤트 비활성화"""
        success = game_engine.scheduler_manager.disable_event(event_name)

        if success:
            await session.send_message({
                "type": "success",
                "message": f"✅ 이벤트 '{event_name}'을(를) 비활성화했습니다."
            })
            return CommandResult(
                result_type=CommandResultType.SUCCESS,
                message="이벤트 비활성화"
            )
        else:
            await session.send_message({
                "type": "error",
                "message": f"❌ 이벤트를 찾을 수 없습니다: {event_name}"
            })
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message="이벤트 없음"
            )
