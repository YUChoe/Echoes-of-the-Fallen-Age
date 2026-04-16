"""
Lua 스크립트 로더 - NPC 대화 스크립트를 로드하고 실행

lupa 라이브러리를 통해 Lua 스크립트를 샌드박스 환경에서 실행한다.
스크립트 파일은 매 호출 시 디스크에서 읽어 핫 리로드를 지원한다.
Exchange API를 Lua 글로벌에 등록하여 대화 스크립트에서 교환 기능을 사용할 수 있다.
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .managers.exchange_manager import ExchangeManager

logger = logging.getLogger(__name__)

# lupa 타입 힌트용 (런타임에는 사용하지 않음)
LuaRuntime_T = Any
LuaTable_T = Any

# 비동기→동기 브릿지용 스레드 풀 (Exchange API 호출 전용)
_exchange_thread_pool = ThreadPoolExecutor(max_workers=1)

# silver_coin 템플릿 ID (인벤토리 목록에서 제외용)
_SILVER_TEMPLATE_ID = "silver_coin"


def _attribute_filter(obj: object, attr_name: str, is_setting: bool) -> str:
    """Lua에서 Python 객체 속성 접근을 필터링하는 샌드박스 함수.

    '_' 접두사 속성 접근을 차단하여 Python 내부 객체 보호.
    """
    if isinstance(attr_name, str) and not attr_name.startswith("_"):
        return attr_name
    raise AttributeError(f"access denied: {attr_name}")


def _run_async(coro: Any) -> Any:
    """비동기 코루틴을 동기적으로 실행하는 브릿지 함수.

    Lua 스크립트는 동기 컨텍스트에서 실행되므로,
    별도 스레드에서 새 이벤트 루프를 생성하여 비동기 함수를 호출한다.
    """
    def _run_in_thread() -> Any:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    future = _exchange_thread_pool.submit(_run_in_thread)
    return future.result(timeout=10)


class LuaScriptLoader:
    """Lua 스크립트 로더 - NPC 대화 스크립트를 로드하고 실행"""

    def __init__(self) -> None:
        self._lua: LuaRuntime_T | None = None
        self._available: bool = False
        self._exchange_manager: ExchangeManager | None = None
        try:
            from lupa import LuaRuntime  # type: ignore[import-untyped]

            self._lua = LuaRuntime(
                register_eval=False,
                attribute_filter=_attribute_filter,
            )
            self._available = True
            logger.info("LuaScriptLoader 초기화 완료 (lupa 사용 가능)")
        except ImportError:
            logger.error(
                "lupa 라이브러리를 찾을 수 없습니다. "
                "Lua 대화 스크립트가 비활성화됩니다."
            )
        except Exception as e:
            logger.error(f"LuaRuntime 초기화 실패: {e}")

    def register_exchange_api(self, exchange_manager: ExchangeManager) -> None:
        """ExchangeManager 참조를 저장하고 Lua 글로벌에 exchange 테이블 등록"""
        self._exchange_manager = exchange_manager
        if self._available and self._lua is not None:
            self._register_exchange_globals()
            logger.info("Exchange API가 Lua 글로벌에 등록됨")

    def is_available(self) -> bool:
        """lupa 라이브러리 사용 가능 여부 반환"""
        return self._available

    def load_script(self, npc_id: str) -> str | None:
        """configs/dialogues/{npc_id}.lua 파일을 읽어 문자열로 반환.

        파일 미존재 시 None 반환.
        """
        file_path = os.path.join("configs", "dialogues", f"{npc_id}.lua")
        if not os.path.exists(file_path):
            logger.info(f"Lua 스크립트 파일 없음: {file_path}")
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as fp:
                return fp.read()
        except OSError as e:
            logger.error(f"Lua 스크립트 파일 읽기 실패 [{npc_id}]: {e}")
            return None

    def execute_get_dialogue(
        self, npc_id: str, context: dict[str, Any]
    ) -> tuple[list[dict[str, str]], OrderedDict[int, dict[str, str]]] | None:
        """Lua 스크립트의 get_dialogue(ctx) 함수를 실행.

        반환: (dialogue_texts, choice_entity) 또는 None (실패 시)
        - dialogue_texts: [{"en": "...", "ko": "..."}, ...]
        - choice_entity: OrderedDict {1: {"en": "...", "ko": "..."}, ...}
        """
        if not self._available or self._lua is None:
            return None

        script_source = self.load_script(npc_id)
        if script_source is None:
            return None

        try:
            self._lua.execute(script_source)
            get_dialogue_fn = self._lua.globals().get_dialogue
            if get_dialogue_fn is None:
                logger.warning(
                    f"Lua 스크립트에 get_dialogue 함수 없음 [{npc_id}]"
                )
                return None

            lua_ctx = self._build_lua_context(context)
            lua_result = get_dialogue_fn(lua_ctx)
            if lua_result is None:
                return None

            return self._convert_lua_result(lua_result)
        except Exception as e:
            logger.error(f"Lua 스크립트 실행 오류 [{npc_id}]: {e}")
            return None

    def execute_on_choice(
        self, npc_id: str, choice: int, context: dict[str, Any]
    ) -> tuple[list[dict[str, str]], OrderedDict[int, dict[str, str]]] | None:
        """Lua 스크립트의 on_choice(choice_number, ctx) 함수를 실행.

        반환: (dialogue_texts, choice_entity) 또는 None (실패 시)
        """
        if not self._available or self._lua is None:
            return None

        script_source = self.load_script(npc_id)
        if script_source is None:
            return None

        try:
            self._lua.execute(script_source)
            on_choice_fn = self._lua.globals().on_choice
            if on_choice_fn is None:
                logger.warning(
                    f"Lua 스크립트에 on_choice 함수 없음 [{npc_id}]"
                )
                return None

            lua_ctx = self._build_lua_context(context)
            lua_result = on_choice_fn(choice, lua_ctx)
            if lua_result is None:
                return None

            return self._convert_lua_result(lua_result)
        except Exception as e:
            logger.error(f"Lua 스크립트 실행 오류 [{npc_id}]: {e}")
            return None

    def execute_on_bye(self, npc_id: str, context: dict[str, Any]) -> None:
        """Lua 스크립트의 on_bye(ctx) 콜백을 실행 (선택적).

        Lua 스크립트에 on_bye 함수가 정의되어 있으면 호출한다.
        미정의 시 무시. 반환값 없음.
        """
        if not self._available or self._lua is None:
            return

        script_source = self.load_script(npc_id)
        if script_source is None:
            return

        try:
            self._lua.execute(script_source)
            on_bye_fn = self._lua.globals().on_bye
            if on_bye_fn is None:
                return  # on_bye 미정의 → 무시

            lua_ctx = self._build_lua_context(context)
            on_bye_fn(lua_ctx)
            logger.info(f"Lua on_bye 콜백 실행 완료 [{npc_id}]")
        except Exception as e:
            logger.error(f"Lua on_bye 콜백 실행 오류 [{npc_id}]: {e}")

    def _build_lua_context(self, context: dict[str, Any]) -> LuaTable_T:
        """Python dict를 Lua 테이블로 변환하여 샌드박스 컨텍스트 생성.

        중첩 dict도 재귀적으로 Lua 테이블로 변환한다.
        """
        if self._lua is None:
            raise RuntimeError("LuaRuntime이 초기화되지 않았습니다")

        # register_eval=False이므로 execute로 테이블 생성 함수를 정의
        self._lua.execute("function newtable() return {} end")
        new_table = self._lua.globals().newtable  # type: ignore[union-attr]

        def _to_lua_table(data: Any) -> Any:
            if isinstance(data, dict):
                lua_table = new_table()
                for key, value in data.items():
                    lua_table[key] = _to_lua_table(value)
                return lua_table
            if isinstance(data, (list, tuple)):
                lua_table = new_table()
                for i, value in enumerate(data, start=1):
                    lua_table[i] = _to_lua_table(value)
                return lua_table
            return data

        return _to_lua_table(context)

    def _convert_lua_result(
        self, lua_result: LuaTable_T
    ) -> tuple[list[dict[str, str]], OrderedDict[int, dict[str, str]]]:
        """Lua 반환값(테이블)을 Python 자료구조로 변환.

        Lua 테이블 {en = "...", ko = "..."} → Python dict {"en": "...", "ko": "..."}

        반환: (dialogue_texts, choice_entity)
        """
        dialogue_texts: list[dict[str, str]] = []
        choice_entity: OrderedDict[int, dict[str, str]] = OrderedDict()

        # text 배열 변환
        lua_text = lua_result.text
        if lua_text is not None:
            for item in lua_text.values():
                text_dict = self._lua_table_to_dict(item)
                dialogue_texts.append(text_dict)

        # choices 테이블 변환
        lua_choices = lua_result.choices
        if lua_choices is not None:
            items = sorted(lua_choices.items(), key=lambda x: int(x[0]))
            for key, value in items:
                choice_dict = self._lua_table_to_dict(value)
                choice_entity[int(key)] = choice_dict

        return dialogue_texts, choice_entity

    def _lua_table_to_dict(self, lua_table: LuaTable_T) -> dict[str, str]:
        """단일 Lua 테이블 {en = "...", ko = "..."}을 Python dict로 변환."""
        result: dict[str, str] = {}
        if lua_table is None:
            return result
        try:
            for key, value in lua_table.items():
                result[str(key)] = str(value)
        except (AttributeError, TypeError):
            # Lua 테이블이 아닌 경우 빈 dict 반환
            pass
        return result

    # ── Exchange API 등록 ──────────────────────────────────

    def _register_exchange_globals(self) -> None:
        """Lua 글로벌에 exchange 테이블 등록.

        Lua에서 다음과 같이 호출 가능:
          exchange.get_npc_inventory(npc_id)
          exchange.buy_from_npc(player_id, npc_id, item_id, price)
        """
        if self._lua is None or self._exchange_manager is None:
            return

        lua = self._lua
        em = self._exchange_manager

        # Lua 테이블 생성 함수 준비
        lua.execute("function newtable() return {} end")
        new_table_fn = lua.globals().newtable

        def _to_lua(data: Any) -> Any:
            """Python 객체를 Lua 테이블로 변환"""
            if isinstance(data, dict):
                t = new_table_fn()
                for k, v in data.items():
                    t[k] = _to_lua(v)
                return t
            if isinstance(data, (list, tuple)):
                t = new_table_fn()
                for i, v in enumerate(data, start=1):
                    t[i] = _to_lua(v)
                return t
            return data

        def _make_error(error: str) -> Any:
            """실패 결과 Lua 테이블 생성"""
            t = new_table_fn()
            t["success"] = False
            t["error"] = error
            t["error_code"] = "invalid_arguments"
            return t

        def _inventory_to_lua(items: list[Any]) -> Any:
            """인벤토리 아이템 목록을 Lua 테이블로 변환.

            silver_coin은 제외한다.
            """
            result = new_table_fn()
            idx = 1
            for item in items:
                # silver_coin 제외
                if item.properties.get("template_id") == _SILVER_TEMPLATE_ID:
                    continue
                entry = new_table_fn()
                entry["id"] = str(item.id)
                # name은 다국어 dict {en: "...", ko: "..."}
                entry["name"] = _to_lua(
                    dict(item.name) if isinstance(item.name, dict) else {}
                )
                entry["category"] = str(
                    item.properties.get("category", "")
                )
                entry["weight"] = float(item.weight)
                entry["is_equipped"] = bool(item.is_equipped)
                entry["equipment_slot"] = (
                    str(item.equipment_slot) if item.equipment_slot else ""
                )
                entry["properties"] = _to_lua(
                    dict(item.properties) if isinstance(item.properties, dict)
                    else {}
                )
                result[idx] = entry
                idx += 1
            return result

        # ── 조회 함수 래퍼 ──

        def get_npc_inventory(npc_id: Any) -> Any:
            """NPC 인벤토리 목록 조회 (silver_coin 제외)"""
            if not isinstance(npc_id, str):
                return _make_error("npc_id must be a string")
            try:
                items = _run_async(
                    em._object_repo.get_objects_in_inventory(npc_id)
                )
                return _inventory_to_lua(items)
            except Exception as e:
                logger.error(f"get_npc_inventory 오류: {e}")
                return _make_error(f"Internal error: {e}")

        def get_player_inventory(player_id: Any) -> Any:
            """플레이어 인벤토리 목록 조회 (silver_coin 제외)"""
            if not isinstance(player_id, str):
                return _make_error("player_id must be a string")
            try:
                items = _run_async(
                    em._object_repo.get_objects_in_inventory(player_id)
                )
                return _inventory_to_lua(items)
            except Exception as e:
                logger.error(f"get_player_inventory 오류: {e}")
                return _make_error(f"Internal error: {e}")

        def get_npc_silver(npc_id: Any) -> Any:
            """NPC 실버 잔액 조회"""
            if not isinstance(npc_id, str):
                return _make_error("npc_id must be a string")
            try:
                return _run_async(em._currency.get_balance(npc_id))
            except Exception as e:
                logger.error(f"get_npc_silver 오류: {e}")
                return 0

        def get_player_silver(player_id: Any) -> Any:
            """플레이어 실버 잔액 조회"""
            if not isinstance(player_id, str):
                return _make_error("player_id must be a string")
            try:
                return _run_async(em._currency.get_balance(player_id))
            except Exception as e:
                logger.error(f"get_player_silver 오류: {e}")
                return 0

        # ── 교환 함수 래퍼 ──

        def buy_from_npc(
            player_id: Any, npc_id: Any,
            game_object_id: Any, price: Any,
        ) -> Any:
            """플레이어가 NPC로부터 아이템 구매"""
            # 인자 타입 검증
            if not isinstance(player_id, str):
                return _make_error("player_id must be a string")
            if not isinstance(npc_id, str):
                return _make_error("npc_id must be a string")
            if not isinstance(game_object_id, str):
                return _make_error("game_object_id must be a string")
            if not isinstance(price, (int, float)):
                return _make_error("price must be a number")
            try:
                result = _run_async(
                    em.buy_from_npc(
                        player_id, npc_id, game_object_id, int(price),
                    )
                )
                return _to_lua(dict(result))
            except Exception as e:
                logger.error(f"buy_from_npc 오류: {e}")
                return _make_error(f"Internal error: {e}")

        def sell_to_npc(
            player_id: Any, npc_id: Any,
            game_object_id: Any, price: Any,
        ) -> Any:
            """플레이어가 NPC에게 아이템 판매"""
            # 인자 타입 검증
            if not isinstance(player_id, str):
                return _make_error("player_id must be a string")
            if not isinstance(npc_id, str):
                return _make_error("npc_id must be a string")
            if not isinstance(game_object_id, str):
                return _make_error("game_object_id must be a string")
            if not isinstance(price, (int, float)):
                return _make_error("price must be a number")
            try:
                result = _run_async(
                    em.sell_to_npc(
                        player_id, npc_id, game_object_id, int(price),
                    )
                )
                return _to_lua(dict(result))
            except Exception as e:
                logger.error(f"sell_to_npc 오류: {e}")
                return _make_error(f"Internal error: {e}")

        # Lua 글로벌에 exchange 테이블 등록
        exchange_table = new_table_fn()
        exchange_table["get_npc_inventory"] = get_npc_inventory
        exchange_table["get_player_inventory"] = get_player_inventory
        exchange_table["get_npc_silver"] = get_npc_silver
        exchange_table["get_player_silver"] = get_player_silver
        exchange_table["buy_from_npc"] = buy_from_npc
        exchange_table["sell_to_npc"] = sell_to_npc
        lua.globals()["exchange"] = exchange_table
        logger.info("Exchange API Lua 글로벌 등록 완료")
