"""
아이템 Lua 콜백 핸들러

아이템 동사 명령어(use, read 등) 실행 시 configs/items/{template_id}.lua
스크립트의 콜백 함수(on_use, on_read 등)를 호출하여 아이템별 커스텀 동작을 구현한다.
기존 LuaScriptLoader를 재사용하여 샌드박스 환경과 핫 리로드를 활용한다.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from .lua_script_loader import LuaScriptLoader

logger = logging.getLogger(__name__)


class ItemLuaCallbackHandler:
    """아이템 Lua 콜백 스크립트를 로드하고 실행하는 핸들러

    LuaScriptLoader 인스턴스를 주입받아 재사용하며,
    execute_verb_callback() 범용 메서드로 임의의 동사 콜백을 호출한다.
    """

    def __init__(self, lua_script_loader: LuaScriptLoader) -> None:
        """LuaScriptLoader 인스턴스를 주입받아 저장

        Args:
            lua_script_loader: 기존 NPC 대화 시스템의 LuaScriptLoader 인스턴스
        """
        self._lua_loader = lua_script_loader

    def load_item_script(self, template_id: str) -> str | None:
        """configs/items/{template_id}.lua 파일을 읽어 문자열로 반환

        매 호출 시 디스크에서 읽어 핫 리로드를 지원한다.
        파일 미존재 시 None 반환.

        Args:
            template_id: 아이템 템플릿 ID (예: "health_potion")

        Returns:
            Lua 스크립트 소스 문자열 또는 None
        """
        file_path = os.path.join("configs", "items", f"{template_id}.lua")
        if not os.path.exists(file_path):
            logger.debug(
                "아이템 Lua 스크립트 파일 없음: %s", file_path
            )
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as fp:
                return fp.read()
        except OSError as e:
            logger.error(
                "아이템 Lua 스크립트 파일 읽기 실패 [%s]: %s",
                template_id, e,
            )
            return None

    def _convert_callback_result(
        self,
        lua_result: Any,
    ) -> dict[str, Any] | None:
        """Lua 콜백 반환값(테이블)을 Python dict로 변환

        콜백은 `{message = {key = ..., params = {...}}, consume = true}` 를
        돌려준다. 서버는 문장을 만들지 않으므로 키와 치환 파라미터만 옮긴다.
        아이템 이름처럼 원본이 이중언어인 값은 params 에 dict 로 실려 나가고
        클라이언트가 현재 locale 을 고른다.

        Args:
            lua_result: Lua 콜백 함수의 반환값 (Lua 테이블 또는 None)

        Returns:
            변환된 결과 dict 또는 None (lua_result가 None인 경우)
        """
        if lua_result is None:
            return None

        try:
            fields = dict(lua_result.items())
        except (AttributeError, TypeError):
            logger.warning("아이템 콜백이 테이블이 아닌 값을 돌려줬습니다")
            return None

        message = fields.get("message")
        payload = (
            self._lua_loader.message_payload(message)
            if message is not None
            else {}
        )

        return {
            # 키가 없으면 문장 없이 진행한다. 소모 여부는 그대로 따른다
            "message": payload if payload.get("key") else None,
            "consume": bool(fields.get("consume", False)),
        }

    def execute_verb_callback(
        self,
        template_id: str | None,
        verb: str,
        context: dict[str, Any],
    ) -> dict[str, Any] | None:
        """범용 동사 콜백 실행 메서드

        template_id에 대응하는 Lua 스크립트를 로드하고,
        on_{verb}(ctx) 함수를 동적으로 호출한다.
        모든 오류 시 None을 반환하여 기존 폴백 로직이 실행되도록 한다.

        Args:
            template_id: 아이템 템플릿 ID (예: "health_potion")
            verb: 동사 이름 (예: "use", "read")
            context: 콜백 컨텍스트 (player, item, session 정보)

        Returns:
            콜백 결과 dict 또는 None (폴백 필요 시)
        """
        # template_id 유효성 확인
        if not template_id:
            logger.debug(
                "아이템 Lua 콜백 건너뜀: template_id 없음"
            )
            return None

        # lupa 사용 가능 여부 확인
        if not self._lua_loader.is_available():
            return None

        try:
            # 스크립트 소스 로드
            script_source = self.load_item_script(template_id)
            if script_source is None:
                return None

            # 스크립트 실행 (글로벌에 함수 등록)
            self._lua_loader._lua.execute(script_source)

            # on_{verb} 함수 존재 확인
            callback_name = f"on_{verb}"
            callback_fn = getattr(
                self._lua_loader._lua.globals(), callback_name, None
            )
            if callback_fn is None:
                logger.debug(
                    "아이템 Lua 스크립트에 %s 함수 없음 [%s]",
                    callback_name, template_id,
                )
                return None

            # Lua 컨텍스트 생성
            lua_ctx = self._lua_loader._build_lua_context(context)

            # 콜백 함수 호출
            lua_result = callback_fn(lua_ctx)
            if lua_result is None:
                logger.debug(
                    "아이템 Lua 콜백 nil 반환 [%s.%s]",
                    template_id, callback_name,
                )
                return None

            # 결과 변환
            converted = self._convert_callback_result(lua_result)

            logger.debug(
                "아이템 Lua 콜백 실행 완료 [%s.%s]",
                template_id, callback_name,
            )
            return converted

        except Exception as e:
            logger.error(
                "아이템 Lua 콜백 실행 오류 [%s.on_%s]: %s",
                template_id, verb, e,
            )
            return None
