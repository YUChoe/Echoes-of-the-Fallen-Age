# -*- coding: utf-8 -*-
"""액션 관리자

구조화 액션 메시지를 디스패처로 보내고 결과를 계약 메시지로 변환한다.
텍스트 명령어 경로(CommandProcessor)는 액션 디스패처로 대체되어 제거되었다.
"""

import logging
from typing import TYPE_CHECKING, Optional

from ..types import SessionType

if TYPE_CHECKING:
    from ..game_engine import GameEngine
    from ...commands.dispatcher import ActionDispatcher

logger = logging.getLogger(__name__)


class CommandManager:
    """액션 디스패치를 담당하는 매니저"""

    def __init__(self, game_engine: 'GameEngine'):
        self.game_engine = game_engine
        self.dispatcher: Optional['ActionDispatcher'] = None
        self._setup_dispatcher()

    def _setup_dispatcher(self) -> None:
        """액션 디스패처 초기화

        구조화 액션 메시지의 처리 경로다. 텍스트 명령어 경로(CommandProcessor)는
        핸들러 이전이 끝나면 제거된다.
        """
        try:
            from ...commands.actions import build_handlers
            from ...commands.dispatcher import ActionDispatcher

            self.dispatcher = ActionDispatcher(
                self.game_engine, self.game_engine.event_bus
            )
            self.dispatcher.register_all(build_handlers())
        except Exception as e:
            logger.error(f"ActionDispatcher 초기화 실패: {e}", exc_info=True)
            raise

    async def handle_action(self, session: SessionType, message: dict) -> None:
        """action 메시지를 처리하고 결과를 전송한다.

        Args:
            session: 액션을 보낸 세션
            message: 봉투 검증을 통과한 action 메시지
        """
        if not self.dispatcher:
            logger.error("ActionDispatcher가 초기화되지 않았습니다.")
            await session.send_protocol_error(
                "INTERNAL_ERROR", "dispatcher not initialised"
            )
            return

        ctx = self.dispatcher.build_context(session, message)
        result = await self.dispatcher.dispatch(ctx)

        await self._send_action_result(session, ctx, result)

    async def _send_action_result(
        self, session: SessionType, ctx, result
    ) -> None:
        """액션 결과를 계약 메시지로 변환해 전송한다.

        성공한 액션의 상태 변화는 핸들러가 직접 밀어 보낸다(room_info, inventory
        등). 여기서는 거절과 오류, 그리고 알림만 처리한다.
        """
        from ...commands.context import ActionResultType
        from ...server.serialization import action_rejected, message_payload

        if result.result_type is ActionResultType.REJECTED:
            # 거절 사유는 계약에 담을 자리가 없으므로 서버 로그에만 남긴다
            if result.message:
                logger.info(
                    f"액션 거절: {ctx.verb} -> "
                    f"{result.rejection_code} ({result.message})"
                )

            await session.send_message(
                action_rejected(
                    ctx.seq,
                    ctx.verb,
                    result.rejection_code or "NOT_APPLICABLE",
                    message_key=result.message_key,
                    params=result.params,
                    target=ctx.target,
                )
            )
            return

        if result.result_type is ActionResultType.ERROR:
            await session.send_protocol_error(
                "INTERNAL_ERROR", result.message or f"action failed: {ctx.verb}", ctx.seq
            )
            return

        # 성공 알림. 표시할 내용이 없으면 아무것도 보내지 않는다.
        # result.message 는 개발자용 사유이므로 전송하지 않는다. Lua 콜백이 만든
        # 완성 문장이 여기 실려 오며, 번역 키 전환은 Task 10 에서 다룬다.
        if result.message_key:
            await session.send_message({
                "type": "event",
                "category": "system",
                "message": message_payload(result.message_key, result.params),
            })
        elif result.message:
            logger.info(f"액션 성공 메시지 미전송: {ctx.verb} ({result.message})")

        await self._send_action_broadcast(session, result)

    async def _send_action_broadcast(self, session: SessionType, result) -> None:
        """액션의 주변 알림을 전송한다.

        번역 키를 그대로 전달하므로 수신자가 각자의 언어로 번역한다.
        """
        from ...commands.context import BroadcastScope
        from ...server.serialization import build, message_payload

        spec = result.broadcast
        if spec is None:
            return

        payload = build(
            "event",
            category=spec.category,
            message=message_payload(spec.message_key, spec.params),
        )

        if spec.scope is BroadcastScope.ALL:
            await self.game_engine.broadcast_to_all(payload)
            return

        room_id = getattr(session, 'current_room_id', None)
        if not room_id:
            return

        exclude = session.session_id if spec.exclude_actor else None
        await self.game_engine.broadcast_to_room(room_id, payload, exclude_session=exclude)
