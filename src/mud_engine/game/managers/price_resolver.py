# -*- coding: utf-8 -*-
"""아이템 가격 산출 모듈

item_prices DB 테이블에서 template_id 기반으로 buy_price/sell_price를 조회하고,
선택적 price_modifier를 적용하여 최종 거래 가격을 산출한다.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class PriceResolver:
    """아이템 가격 산출 모듈.

    item_prices DB 테이블에서 template_id로 buy_price/sell_price를 조회하고,
    선택적 price_modifier를 적용하여 최종 가격을 반환한다.
    """

    def __init__(self, db_manager: Any) -> None:
        """DatabaseManager를 주입받아 DB 조회에 사용한다.

        Args:
            db_manager: DatabaseManager 인스턴스
        """
        self._db = db_manager

    async def get_buy_price(
        self,
        template_id: Optional[str],
        price_modifier: Optional[float] = None,
    ) -> int:
        """아이템 구매 가격 산출 (플레이어가 NPC에게서 살 때).

        item_prices 테이블에서 template_id로 buy_price 조회.
        template_id가 테이블에 없으면 0 반환 (거래 불가).

        Args:
            template_id: 아이템 템플릿 ID
            price_modifier: 가격 조정 배율 (예: 0.9 = 10% 할인)

        Returns:
            최종 구매 가격 (int). 거래 불가 시 0.
        """
        base = await self._fetch_price(template_id, "buy_price")
        if base <= 0:
            return 0
        return self._apply_modifier(base, price_modifier)

    async def get_sell_price(
        self,
        template_id: Optional[str],
        price_modifier: Optional[float] = None,
    ) -> int:
        """아이템 판매 가격 산출 (플레이어가 NPC에게 팔 때).

        item_prices 테이블에서 template_id로 sell_price 조회.
        template_id가 테이블에 없으면 0 반환 (거래 불가).

        Args:
            template_id: 아이템 템플릿 ID
            price_modifier: 가격 조정 배율 (예: 1.1 = 10% 할증)

        Returns:
            최종 판매 가격 (int). 거래 불가 시 0.
        """
        base = await self._fetch_price(template_id, "sell_price")
        if base <= 0:
            return 0
        return self._apply_modifier(base, price_modifier)

    async def _fetch_price(
        self, template_id: Optional[str], column: str
    ) -> int:
        """item_prices 테이블에서 가격 조회.

        Args:
            template_id: 아이템 템플릿 ID
            column: 조회할 컬럼명 ("buy_price" 또는 "sell_price")

        Returns:
            가격 (int). 미존재/오류 시 0.
        """
        if not template_id:
            return 0
        try:
            cursor = await self._db.execute(
                f"SELECT {column} FROM item_prices WHERE template_id = ?",
                (template_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                return 0
            return int(row[0]) if row[0] is not None else 0
        except Exception as e:
            logger.error(
                "item_prices 조회 실패 [%s.%s]: %s",
                template_id, column, e,
            )
            return 0

    @staticmethod
    def _apply_modifier(base: int, modifier: Optional[float]) -> int:
        """기준 가격에 modifier를 적용하여 최종 가격 반환.

        Args:
            base: 기준 가격 (양수)
            modifier: 가격 조정 배율 (None이면 적용 안 함)

        Returns:
            최종 가격 (최소값 1 보장)
        """
        if modifier is not None:
            result = round(base * modifier)
        else:
            result = base
        return max(1, result)
