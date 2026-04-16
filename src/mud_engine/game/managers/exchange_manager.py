# -*- coding: utf-8 -*-
"""양방향 아이템 교환 관리 모듈

ExchangeManager는 플레이어와 NPC 간의 양방향 아이템 교환을 원자적으로 처리한다.
CurrencyManager와 GameObjectRepository를 조합하여 실버 차감/증가 및 아이템 이동을 수행하며,
중간 실패 시 보상 트랜잭션 패턴으로 롤백한다.
"""
import logging

from typing_extensions import TypedDict

from ..game_object_repository import GameObjectRepository
from ..models import GameObject
from ..player_repository import PlayerRepository
from .currency_manager import CurrencyManager

logger = logging.getLogger(__name__)


class ExchangeResult(TypedDict):
    """교환 결과 타입"""

    success: bool
    error: str  # 실패 시 사유 (빈 문자열이면 성공)
    error_code: str  # 프로그래밍용 에러 코드


def _ok() -> ExchangeResult:
    """성공 결과 생성"""
    return ExchangeResult(success=True, error="", error_code="")


def _fail(error: str, error_code: str) -> ExchangeResult:
    """실패 결과 생성"""
    return ExchangeResult(success=False, error=error, error_code=error_code)


class ExchangeManager:
    """양방향 아이템 교환 처리

    buy_from_npc / sell_to_npc 메서드를 통해 원자적 거래를 수행한다.
    실버 차감 후 아이템 이동 실패 시 보상 트랜잭션으로 롤백한다.
    """

    def __init__(
        self,
        currency_manager: CurrencyManager,
        object_repo: GameObjectRepository,
        player_repo: PlayerRepository,
    ) -> None:
        self._currency = currency_manager
        self._object_repo = object_repo
        self._player_repo = player_repo
        logger.info("ExchangeManager 초기화 완료")

    async def buy_from_npc(
        self, player_id: str, npc_id: str, game_object_id: str, price: int,
    ) -> ExchangeResult:
        """플레이어가 NPC로부터 아이템 구매.

        순서: 잔액 확인 → 아이템 존재 확인 → 무게 확인 →
              플레이어 실버 차감 → NPC 실버 증가 → 장착 해제 → 아이템 이동
        실패 시 보상 트랜잭션으로 롤백.
        """
        try:
            # 1. 아이템 존재 확인
            item = await self._object_repo.get_by_id(game_object_id)
            if not item:
                logger.debug(f"구매 실패 - 아이템 미존재: {game_object_id}")
                return _fail("아이템을 찾을 수 없습니다.", "item_not_found")

            # 아이템이 NPC 인벤토리에 있는지 확인
            if not item.is_in_inventory(npc_id):
                logger.debug(
                    f"구매 실패 - 아이템이 NPC 인벤토리에 없음: "
                    f"item={game_object_id}, npc={npc_id}"
                )
                return _fail("아이템을 찾을 수 없습니다.", "item_not_found")

            # 2. 플레이어 실버 잔액 확인
            player_balance = await self._currency.get_balance(player_id)
            if player_balance < price:
                logger.debug(
                    f"구매 실패 - 실버 부족: "
                    f"player={player_id[-12:]}, 잔액={player_balance}, 가격={price}"
                )
                return _fail("실버가 부족합니다.", "insufficient_silver")

            # 3. 무게 제한 확인
            carry_weight = await self._get_player_carry_weight(player_id)
            weight_limit = await self._get_player_weight_limit(player_id)
            if carry_weight + item.weight > weight_limit:
                logger.debug(
                    f"구매 실패 - 무게 초과: "
                    f"현재={carry_weight:.2f}, 아이템={item.weight:.2f}, "
                    f"제한={weight_limit:.2f}"
                )
                return _fail("무게 제한을 초과합니다.", "weight_exceeded")

            # 4. 플레이어 실버 차감
            spend_ok = await self._currency.spend(player_id, price)
            if not spend_ok:
                logger.error(f"구매 실패 - 실버 차감 실패: player={player_id[-12:]}")
                return _fail("실버 차감에 실패했습니다.", "insufficient_silver")

            # 5. NPC 실버 증가
            earn_ok = await self._currency.earn(npc_id, price)
            if not earn_ok:
                # 롤백: 플레이어 실버 복원
                logger.warning(
                    f"구매 롤백 - NPC 실버 증가 실패, 플레이어 실버 복원: "
                    f"npc={npc_id[-12:]}"
                )
                await self._currency.earn(player_id, price)
                return _fail("거래 처리 중 오류가 발생했습니다.", "item_not_found")

            # 6. 장착 해제 (NPC가 장착 중이면)
            if item.is_equipped:
                await self._unequip_item(item)

            # 7. 아이템을 NPC → 플레이어로 이동
            moved = await self._object_repo.move_object_to_inventory(
                game_object_id, player_id,
            )
            if not moved:
                # 롤백: 양쪽 실버 복원
                logger.warning(
                    f"구매 롤백 - 아이템 이동 실패, 실버 복원: "
                    f"item={game_object_id}"
                )
                await self._currency.earn(player_id, price)
                await self._currency.spend(npc_id, price)
                return _fail("아이템 이동에 실패했습니다.", "item_not_found")

            logger.info(
                f"구매 완료: player={player_id[-12:]}, npc={npc_id[-12:]}, "
                f"item={game_object_id[-12:]}, price={price}"
            )
            return _ok()

        except Exception as e:
            logger.error(
                f"구매 중 예외 발생: player={player_id}, npc={npc_id}, "
                f"item={game_object_id}, error={e}",
                exc_info=True,
            )
            return _fail(f"거래 처리 중 오류가 발생했습니다: {e}", "item_not_found")

    async def sell_to_npc(
        self, player_id: str, npc_id: str, game_object_id: str, price: int,
    ) -> ExchangeResult:
        """플레이어가 NPC에게 아이템 판매.

        순서: NPC 잔액 확인 → 아이템 소유 확인 → 장착 해제 →
              NPC 실버 차감 → 플레이어 실버 증가 → 아이템 이동
        실패 시 보상 트랜잭션으로 롤백.
        """
        try:
            # 1. 아이템 존재 확인
            item = await self._object_repo.get_by_id(game_object_id)
            if not item:
                logger.debug(f"판매 실패 - 아이템 미존재: {game_object_id}")
                return _fail("아이템을 찾을 수 없습니다.", "item_not_found")

            # 2. 아이템 소유 확인 (플레이어 인벤토리에 있는지)
            if not item.is_in_inventory(player_id):
                logger.debug(
                    f"판매 실패 - 아이템 소유자 불일치: "
                    f"item={game_object_id}, player={player_id}"
                )
                return _fail(
                    "해당 아이템을 소유하고 있지 않습니다.", "item_not_owned",
                )

            # 3. NPC 실버 잔액 확인
            npc_balance = await self._currency.get_balance(npc_id)
            if npc_balance < price:
                logger.debug(
                    f"판매 실패 - NPC 실버 부족: "
                    f"npc={npc_id[-12:]}, 잔액={npc_balance}, 가격={price}"
                )
                return _fail(
                    "NPC의 소지금이 부족합니다.", "npc_insufficient_silver",
                )

            # 4. 장착 해제 (플레이어가 장착 중이면)
            if item.is_equipped:
                await self._unequip_item(item)

            # 5. NPC 실버 차감
            spend_ok = await self._currency.spend(npc_id, price)
            if not spend_ok:
                logger.error(f"판매 실패 - NPC 실버 차감 실패: npc={npc_id[-12:]}")
                return _fail(
                    "NPC의 소지금이 부족합니다.", "npc_insufficient_silver",
                )

            # 6. 플레이어 실버 증가
            earn_ok = await self._currency.earn(player_id, price)
            if not earn_ok:
                # 롤백: NPC 실버 복원
                logger.warning(
                    f"판매 롤백 - 플레이어 실버 증가 실패, NPC 실버 복원: "
                    f"player={player_id[-12:]}"
                )
                await self._currency.earn(npc_id, price)
                return _fail("거래 처리 중 오류가 발생했습니다.", "item_not_found")

            # 7. 아이템을 플레이어 → NPC로 이동
            moved = await self._object_repo.move_object_to_inventory(
                game_object_id, npc_id,
            )
            if not moved:
                # 롤백: 양쪽 실버 복원
                logger.warning(
                    f"판매 롤백 - 아이템 이동 실패, 실버 복원: "
                    f"item={game_object_id}"
                )
                await self._currency.earn(npc_id, price)
                await self._currency.spend(player_id, price)
                return _fail("아이템 이동에 실패했습니다.", "item_not_found")

            logger.info(
                f"판매 완료: player={player_id[-12:]}, npc={npc_id[-12:]}, "
                f"item={game_object_id[-12:]}, price={price}"
            )
            return _ok()

        except Exception as e:
            logger.error(
                f"판매 중 예외 발생: player={player_id}, npc={npc_id}, "
                f"item={game_object_id}, error={e}",
                exc_info=True,
            )
            return _fail(f"거래 처리 중 오류가 발생했습니다: {e}", "item_not_found")

    async def _unequip_item(self, game_object: GameObject) -> None:
        """아이템 장착 해제.

        is_equipped=False로 설정하되 equipment_slot은 유지한다.
        (재장착 가능하도록)
        """
        game_object.is_equipped = False
        await self._object_repo.update(
            game_object.id, {"is_equipped": False},
        )
        logger.debug(
            f"장착 해제: item={game_object.id[-12:]}, "
            f"slot={game_object.equipment_slot}"
        )

    async def _get_player_carry_weight(self, player_id: str) -> float:
        """플레이어 현재 소지 무게 계산.

        인벤토리 내 모든 아이템의 weight 합산.
        """
        inventory = await self._object_repo.get_objects_in_inventory(player_id)
        return sum(obj.weight for obj in inventory)

    async def _get_player_weight_limit(self, player_id: str) -> float:
        """플레이어 무게 제한 조회.

        Player 모델의 get_max_carry_weight() 메서드를 사용한다.
        (기본 공식: 5 + STR * 5 kg)
        """
        player = await self._player_repo.get_by_id(player_id)
        if not player:
            logger.warning(f"플레이어 미존재, 기본 무게 제한 반환: {player_id}")
            return 10.0  # 기본값
        return player.get_max_carry_weight()
