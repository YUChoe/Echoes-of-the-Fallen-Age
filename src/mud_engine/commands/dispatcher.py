# -*- coding: utf-8 -*-
"""액션 디스패처

구조화 액션 메시지를 핸들러로 보낸다. 문자열 파싱, 별칭 해석, 숫자 변환이 없다.
클라이언트가 `verb` 와 `target` uuid 를 보내므로 해석할 문법이 존재하지 않는다.

처리 순서
    1. 인증 검사        미인증이면 NOT_AUTHENTICATED
    2. verb 조회        등록되지 않았으면 NOT_APPLICABLE
    3. 권한 검사        관리자 전용이면 PERMISSION_DENIED
    4. 상태 게이팅      전투 전용/전투 금지 판정으로 WRONG_STATE
    5. target 해석      접근 범위를 벗어나면 NOT_FOUND
    6. 핸들러 실행

프로토콜 계약: docs/protocol/client-to-server.md
"""

import logging
from typing import TYPE_CHECKING, Any, Optional

from .base import ActionHandler
from .context import ActionContext, ActionResult, error, rejected
from .resolver import EntityResolver
from ..core.event_bus import Event, EventBus, EventType
from ..core.types import SessionType

if TYPE_CHECKING:
    from ..core.game_engine import GameEngine

logger = logging.getLogger(__name__)


class ActionDispatcher:
    """verb 를 핸들러로 라우팅한다."""

    def __init__(
        self, game_engine: "GameEngine", event_bus: Optional[EventBus] = None
    ) -> None:
        self.game_engine = game_engine
        self.event_bus = event_bus
        self.handlers: dict[str, ActionHandler] = {}
        self.resolver = EntityResolver(game_engine)

        logger.info("ActionDispatcher 초기화 완료")

    # 등록 ------------------------------------------------------------------

    def register(self, handler: ActionHandler) -> None:
        """핸들러를 등록한다.

        Raises:
            ValueError: verb 가 비었거나 이미 등록된 경우
        """
        if not handler.verb:
            raise ValueError(f"{type(handler).__name__} 에 verb 가 없습니다")

        if handler.verb in self.handlers:
            raise ValueError(f"verb '{handler.verb}' 가 중복 등록되었습니다")

        self.handlers[handler.verb] = handler
        logger.debug(f"액션 등록: {handler.verb}")

    def register_all(self, handlers: list[ActionHandler]) -> None:
        """핸들러 여러 개를 등록한다."""
        for handler in handlers:
            self.register(handler)

        logger.info(f"액션 {len(self.handlers)}개 등록 완료")

    def get_handler(self, verb: str) -> Optional[ActionHandler]:
        """verb 에 대응하는 핸들러를 반환한다."""
        return self.handlers.get(verb)

    def known_verbs(self) -> list[str]:
        """등록된 verb 목록을 반환한다."""
        return sorted(self.handlers)

    # 디스패치 --------------------------------------------------------------

    async def dispatch(self, ctx: ActionContext) -> ActionResult:
        """액션 한 건을 처리한다.

        Args:
            ctx: 액션 컨텍스트. `entity` 는 이 메서드가 채운다

        Returns:
            처리 결과. 거절도 정상 반환이며 예외를 던지지 않는다
        """
        # 1. 인증 검사
        if not ctx.session.is_authenticated or not ctx.session.player:
            return rejected(
                "NOT_AUTHENTICATED", message="Authentication required"
            )

        # 2. verb 조회
        handler = self.handlers.get(ctx.verb)
        if handler is None:
            logger.warning(f"등록되지 않은 verb: {ctx.verb}")
            return rejected(
                "NOT_APPLICABLE", message=f"Unknown verb: {ctx.verb}"
            )

        # 3. 권한 검사
        if handler.admin_only and not getattr(ctx.session.player, "is_admin", False):
            logger.warning(
                f"권한 없음: {ctx.session.player.username} -> {ctx.verb}"
            )
            return rejected("PERMISSION_DENIED", message="Admin only")

        # 4. 상태 게이팅
        gate_result = self._check_state(ctx, handler)
        if gate_result is not None:
            return gate_result

        # 5. target 해석
        resolve_result = await self._resolve_target(ctx, handler)
        if resolve_result is not None:
            return resolve_result

        # 6. 핸들러 실행
        return await self._run(ctx, handler)

    # 단계별 처리 -----------------------------------------------------------

    def _check_state(
        self, ctx: ActionContext, handler: ActionHandler
    ) -> Optional[ActionResult]:
        """상태 게이팅. 통과하면 None 을 반환한다."""
        in_combat = getattr(ctx.session, "in_combat", False)

        if handler.combat_only and not in_combat:
            return rejected("WRONG_STATE", message="Only available in combat")

        if handler.forbidden_in_combat and in_combat:
            return rejected("WRONG_STATE", message="Not available in combat")

        return None

    async def _resolve_target(
        self, ctx: ActionContext, handler: ActionHandler
    ) -> Optional[ActionResult]:
        """target 을 해석해 ctx.entity 에 채운다. 통과하면 None 을 반환한다."""
        if not handler.requires_target:
            return None

        if not ctx.target:
            logger.warning(f"target 누락: {ctx.verb}")
            return rejected("TARGET_REQUIRED", message="Target uuid required")

        resolved = await self.resolver.resolve(ctx.session, ctx.target)
        if resolved is None:
            return rejected("NOT_FOUND", message="Target not in current context")

        ctx.entity = resolved
        return None

    async def _run(
        self, ctx: ActionContext, handler: ActionHandler
    ) -> ActionResult:
        """핸들러를 실행하고 예외를 결과로 변환한다."""
        await self._publish_action_event(ctx)

        try:
            result = await handler.handle(ctx)
        except Exception as e:
            logger.error(f"액션 실행 오류 ({ctx.verb}): {e}", exc_info=True)
            return error(message=f"Handler failed: {ctx.verb}")

        username = ctx.session.player.username if ctx.session.player else "?"
        logger.info(f"액션 실행: {username} -> {ctx.verb} -> {result.result_type.value}")

        return result

    async def _publish_action_event(self, ctx: ActionContext) -> None:
        """액션 수신을 이벤트로 알린다."""
        if not self.event_bus or not ctx.session.player:
            return

        data: dict[str, Any] = {
            "player_id": ctx.session.player.id,
            "username": ctx.session.player.username,
            "verb": ctx.verb,
            "target": ctx.target,
            "params": ctx.params,
            "session_id": ctx.session.session_id,
        }

        await self.event_bus.publish(
            Event(
                event_type=EventType.PLAYER_COMMAND,
                source=ctx.session.session_id,
                data=data,
            )
        )

    # 메시지 → 컨텍스트 ------------------------------------------------------

    def build_context(
        self, session: SessionType, message: dict[str, Any]
    ) -> ActionContext:
        """action 메시지를 컨텍스트로 만든다.

        형식 검증은 하지 않는다. 잘못된 타입은 디스패치 과정에서 거절된다.
        """
        params = message.get("params")
        target = message.get("target")
        seq = message.get("seq")

        return ActionContext(
            session=session,
            game_engine=self.game_engine,
            verb=str(message.get("verb", "")),
            target=target if isinstance(target, str) else None,
            params=params if isinstance(params, dict) else {},
            seq=seq if isinstance(seq, int) else None,
        )
