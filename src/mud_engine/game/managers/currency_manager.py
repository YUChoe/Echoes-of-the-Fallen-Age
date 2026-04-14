# -*- coding: utf-8 -*-
"""실버 코인 화폐 관리 모듈

CurrencyManager는 silver_coin 스택의 생성, 조회, 증감, 삭제를 전담한다.
game_objects 테이블의 기존 스택 시스템(max_stack=9999)을 활용하며,
properties.template_id='silver_coin'으로 식별한다.
"""
import logging
from typing import List
from uuid import uuid4

from ..game_object_repository import GameObjectRepository
from ..models import GameObject

logger = logging.getLogger(__name__)

# 실버 코인 상수
MAX_STACK = 9999
TEMPLATE_ID = "silver_coin"
COIN_WEIGHT = 0.003


class CurrencyManager:
    """실버 코인 스택 관리"""

    def __init__(self, object_repo: GameObjectRepository) -> None:
        self._object_repo = object_repo
        logger.info("CurrencyManager 초기화 완료")

    async def get_balance(self, owner_id: str) -> int:
        """소유자의 실버 잔액 조회.

        game_objects에서 template_id='silver_coin', location_type='inventory',
        location_id=owner_id인 아이템의 properties.quantity 합산.
        없으면 0 반환.
        """
        stacks = await self._find_silver_stacks(owner_id)
        total = sum(s.properties.get("quantity", 0) for s in stacks)
        return total

    async def earn(self, owner_id: str, amount: int) -> bool:
        """소유자에게 실버 지급.

        기존 스택이 있으면 quantity 증가, 없으면 새 silver_coin 아이템 생성.
        max_stack(9999) 초과 시 추가 스택 생성.
        amount가 0 이하이면 False 반환.
        """
        if amount <= 0:
            logger.warning(f"earn 금액이 0 이하: {amount}")
            return False

        try:
            stacks = await self._find_silver_stacks(owner_id)
            remaining = amount

            # 기존 스택에 여유분 채우기
            for stack in stacks:
                if remaining <= 0:
                    break
                current_qty = stack.properties.get("quantity", 0)
                space = MAX_STACK - current_qty
                if space <= 0:
                    continue
                add = min(remaining, space)
                stack.properties["quantity"] = current_qty + add
                await self._object_repo.update(stack.id, stack.to_dict())
                remaining -= add
                logger.debug(
                    f"실버 스택 {stack.id[-12:]} 수량 증가: "
                    f"{current_qty} -> {current_qty + add}"
                )

            # 남은 금액으로 새 스택 생성
            while remaining > 0:
                qty = min(remaining, MAX_STACK)
                await self._create_silver_stack(owner_id, qty)
                remaining -= qty

            logger.info(f"실버 지급 완료: owner={owner_id[-12:]}, amount={amount}")
            return True

        except Exception as e:
            logger.error(f"실버 지급 실패 (owner={owner_id}, amount={amount}): {e}")
            return False

    async def spend(self, owner_id: str, amount: int) -> bool:
        """소유자의 실버 차감.

        잔액 부족 시 False 반환.
        quantity가 0이 되면 해당 game_object 삭제.
        amount가 0 이하이면 False 반환.
        """
        if amount <= 0:
            logger.warning(f"spend 금액이 0 이하: {amount}")
            return False

        try:
            stacks = await self._find_silver_stacks(owner_id)
            total = sum(s.properties.get("quantity", 0) for s in stacks)

            if total < amount:
                logger.debug(
                    f"실버 잔액 부족: owner={owner_id[-12:]}, "
                    f"잔액={total}, 요청={amount}"
                )
                return False

            remaining = amount

            # 스택에서 차감 (뒤에서부터 소진)
            for stack in reversed(stacks):
                if remaining <= 0:
                    break
                current_qty = stack.properties.get("quantity", 0)
                deduct = min(remaining, current_qty)
                new_qty = current_qty - deduct
                remaining -= deduct

                if new_qty <= 0:
                    # 수량 0이면 삭제
                    await self._object_repo.delete(stack.id)
                    logger.debug(f"실버 스택 삭제: {stack.id[-12:]}")
                else:
                    stack.properties["quantity"] = new_qty
                    await self._object_repo.update(stack.id, stack.to_dict())
                    logger.debug(
                        f"실버 스택 {stack.id[-12:]} 수량 감소: "
                        f"{current_qty} -> {new_qty}"
                    )

            logger.info(f"실버 차감 완료: owner={owner_id[-12:]}, amount={amount}")
            return True

        except Exception as e:
            logger.error(f"실버 차감 실패 (owner={owner_id}, amount={amount}): {e}")
            return False

    async def _find_silver_stacks(self, owner_id: str) -> List[GameObject]:
        """소유자의 silver_coin game_objects 목록 조회.

        location_type='inventory', location_id=owner_id이고
        properties.template_id='silver_coin'인 아이템을 반환한다.
        """
        try:
            inventory = await self._object_repo.get_objects_in_inventory(owner_id)
            return [
                obj for obj in inventory
                if obj.properties.get("template_id") == TEMPLATE_ID
            ]
        except Exception as e:
            logger.error(f"실버 스택 조회 실패 (owner={owner_id}): {e}")
            return []

    async def _create_silver_stack(
        self, owner_id: str, quantity: int
    ) -> GameObject:
        """새 silver_coin game_object 생성."""
        item_id = str(uuid4())
        silver = GameObject(
            id=item_id,
            name={"en": "Silver Coin", "ko": "은화"},
            description={
                "en": "A standard silver coin used for trade.",
                "ko": "거래에 사용되는 표준 은화입니다.",
            },
            location_type="inventory",
            location_id=owner_id,
            properties={
                "template_id": TEMPLATE_ID,
                "is_template": False,
                "category": "currency",
                "base_value": 1,
                "quantity": quantity,
            },
            weight=COIN_WEIGHT,
            max_stack=MAX_STACK,
            equipment_slot=None,
            is_equipped=False,
        )
        created = await self._object_repo.create(silver.to_dict())
        logger.debug(
            f"실버 스택 생성: id={item_id[-12:]}, "
            f"owner={owner_id[-12:]}, qty={quantity}"
        )
        return created
