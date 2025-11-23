"""
NPC 상호작용 명령어들
"""

import logging
from typing import List, Optional

from .base import BaseCommand, CommandResult
from ..core.types import SessionType
from ..game.models import NPC, GameObject

logger = logging.getLogger(__name__)


class TalkCommand(BaseCommand):
    """NPC와 대화하는 명령어"""

    def __init__(self):
        super().__init__(
            name="talk",
            aliases=["speak", "chat"],
            description="NPC와 대화합니다",
            usage="talk <NPC이름>"
        )

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        """NPC와 대화 실행"""
        try:
            if not args:
                return self.create_error_result("누구와 대화하시겠습니까? 사용법: talk <NPC이름>")

            npc_name = " ".join(args)

            # GameEngine을 통해 NPC 조회
            game_engine = getattr(session, 'game_engine', None)
            if not game_engine:
                return self.create_error_result("게임 엔진에 접근할 수 없습니다.")

            # 현재 방의 NPC들 조회
            npcs_in_room = await game_engine.model_manager.npcs.get_npcs_in_room(session.current_room_id)

            # 이름으로 NPC 찾기
            target_npc = None
            for npc in npcs_in_room:
                if (npc_name.lower() in npc.get_localized_name(session.locale).lower() or
                    npc_name.lower() in npc.get_localized_name('en').lower() or
                    npc_name.lower() in npc.get_localized_name('ko').lower()):
                    target_npc = npc
                    break

            if not target_npc:
                return self.create_error_result(f"'{npc_name}'라는 NPC를 찾을 수 없습니다.")

            # NPC 대화 가져오기
            dialogue = target_npc.get_random_dialogue(session.locale)
            npc_display_name = target_npc.get_localized_name(session.locale)

            # 대화 메시지 생성
            message = f"{npc_display_name}: \"{dialogue}\""

            # 같은 방의 다른 플레이어들에게도 알림
            await game_engine.broadcast_to_room(
                session.current_room_id,
                {
                    "type": "room_message",
                    "message": f"{session.player.username}이(가) {npc_display_name}와(과) 대화하고 있습니다."
                },
                exclude_session=session.session_id
            )

            return self.create_success_result(message)

        except Exception as e:
            logger.error(f"대화 명령어 실행 실패: {e}", exc_info=True)
            return self.create_error_result("대화 중 오류가 발생했습니다.")


class ShopCommand(BaseCommand):
    """상점 목록을 보는 명령어"""

    def __init__(self):
        super().__init__(
            name="shop",
            aliases=["store", "list"],
            description="상점의 상품 목록을 봅니다",
            usage="shop [상인이름]"
        )

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        """상점 목록 보기 실행"""
        try:
            # GameEngine을 통해 NPC 조회
            game_engine = getattr(session, 'game_engine', None)
            if not game_engine:
                return self.create_error_result("게임 엔진에 접근할 수 없습니다.")

            # 현재 방의 상인 NPC들 조회
            npcs_in_room = await game_engine.model_manager.npcs.get_npcs_in_room(session.current_room_id)
            merchants = [npc for npc in npcs_in_room if npc.is_merchant()]

            if not merchants:
                return self.create_error_result("이 방에는 상인이 없습니다.")

            # 특정 상인 지정된 경우
            target_merchant = None
            if args:
                merchant_name = " ".join(args)
                for merchant in merchants:
                    if (merchant_name.lower() in merchant.get_localized_name(session.locale).lower() or
                        merchant_name.lower() in merchant.get_localized_name('en').lower() or
                        merchant_name.lower() in merchant.get_localized_name('ko').lower()):
                        target_merchant = merchant
                        break

                if not target_merchant:
                    return self.create_error_result(f"'{merchant_name}'라는 상인을 찾을 수 없습니다.")
            else:
                # 첫 번째 상인 선택
                target_merchant = merchants[0]

            # 상점 아이템 목록 조회
            shop_items = []
            for item_id in target_merchant.shop_inventory:
                item = await game_engine.model_manager.game_objects.get_by_id(item_id)
                if item:
                    shop_items.append(item)

            if not shop_items:
                merchant_name = target_merchant.get_localized_name(session.locale)
                return self.create_success_result(f"{merchant_name}의 상점에는 현재 판매할 상품이 없습니다.")

            # 상점 목록 메시지 생성
            merchant_name = target_merchant.get_localized_name(session.locale)
            message_lines = [f"=== {merchant_name}의 상점 ==="]

            for i, item in enumerate(shop_items, 1):
                item_name = item.get_localized_name(session.locale)
                item_price = item.get_property('price', 10)  # 기본 가격 10골드
                message_lines.append(f"{i}. {item_name} - {item_price} gold")

            message_lines.append("")
            message_lines.append("구매하려면: buy <아이템이름> [상인이름]")

            return self.create_success_result("\n".join(message_lines))

        except Exception as e:
            logger.error(f"상점 명령어 실행 실패: {e}", exc_info=True)
            return self.create_error_result("상점 목록을 불러오는 중 오류가 발생했습니다.")


class BuyCommand(BaseCommand):
    """아이템을 구매하는 명령어"""

    def __init__(self):
        super().__init__(
            name="buy",
            aliases=["purchase"],
            description="상인에게서 아이템을 구매합니다",
            usage="buy <아이템이름> [상인이름]"
        )

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        """아이템 구매 실행"""
        try:
            if not args:
                return self.create_error_result("무엇을 구매하시겠습니까? 사용법: buy <아이템이름> [상인이름]")

            # GameEngine을 통해 NPC 조회
            game_engine = getattr(session, 'game_engine', None)
            if not game_engine:
                return self.create_error_result("게임 엔진에 접근할 수 없습니다.")

            # 현재 방의 상인 NPC들 조회
            npcs_in_room = await game_engine.model_manager.npcs.get_npcs_in_room(session.current_room_id)
            merchants = [npc for npc in npcs_in_room if npc.is_merchant()]

            if not merchants:
                return self.create_error_result("이 방에는 상인이 없습니다.")

            # 플레이어 정보는 session.player에서 직접 가져옴
            if not session.player:
                return self.create_error_result("플레이어 정보를 찾을 수 없습니다.")
            player = session.player

            # 아이템 이름과 상인 이름 분리
            item_name = args[0]
            merchant_name = " ".join(args[1:]) if len(args) > 1 else None

            # 상인 찾기
            target_merchant = None
            if merchant_name:
                for merchant in merchants:
                    if (merchant_name.lower() in merchant.get_localized_name(session.locale).lower() or
                        merchant_name.lower() in merchant.get_localized_name('en').lower() or
                        merchant_name.lower() in merchant.get_localized_name('ko').lower()):
                        target_merchant = merchant
                        break

                if not target_merchant:
                    return self.create_error_result(f"'{merchant_name}'라는 상인을 찾을 수 없습니다.")
            else:
                target_merchant = merchants[0]

            # 상점에서 아이템 찾기
            target_item = None
            for item_id in target_merchant.shop_inventory:
                item = await game_engine.model_manager.game_objects.get_by_id(item_id)
                if item and (item_name.lower() in item.get_localized_name(session.locale).lower() or
                           item_name.lower() in item.get_localized_name('en').lower() or
                           item_name.lower() in item.get_localized_name('ko').lower()):
                    target_item = item
                    break

            if not target_item:
                merchant_display_name = target_merchant.get_localized_name(session.locale)
                return self.create_error_result(f"{merchant_display_name}의 상점에는 '{item_name}'이(가) 없습니다.")

            # 가격 확인
            item_price = target_item.get_property('price', 10)

            # 플레이어 골드 확인
            if not player.has_gold(item_price):
                return self.create_error_result(f"골드가 부족합니다. 필요: {item_price} gold, 보유: {player.gold} gold")

            # 인벤토리 무게 확인
            inventory_objects = await game_engine.world_manager.get_inventory_objects(session.player.id)
            if not player.can_carry_more(inventory_objects, target_item.weight):
                return self.create_error_result("인벤토리가 가득 찼습니다. 무게를 줄이고 다시 시도하세요.")

            # 아이템 복사 생성 (상점 아이템은 템플릿이므로)
            from uuid import uuid4
            new_item_data = target_item.to_dict()
            new_item_data['id'] = str(uuid4())
            new_item_data['location_type'] = 'inventory'
            new_item_data['location_id'] = session.player.id

            # 새 아이템 생성 (상점 아이템은 템플릿이므로 복사)
            new_item = GameObject.from_dict(new_item_data)
            await game_engine.model_manager.game_objects.create(new_item.to_dict())

            # 플레이어 골드 차감
            player.spend_gold(item_price)
            await game_engine.model_manager.players.update(player.id, player.to_dict_with_password())

            # 성공 메시지
            item_display_name = target_item.get_localized_name(session.locale)
            merchant_display_name = target_merchant.get_localized_name(session.locale)

            message = f"{merchant_display_name}에게서 {item_display_name}을(를) {item_price} gold에 구매했습니다."
            message += f"\n남은 골드: {player.gold} gold"

            # 같은 방의 다른 플레이어들에게도 알림
            await game_engine.broadcast_to_room(
                session.current_room_id,
                {
                    "type": "room_message",
                    "message": f"{session.player.username}이(가) {merchant_display_name}에게서 {item_display_name}을(를) 구매했습니다."
                },
                exclude_session=session.session_id
            )

            return self.create_success_result(message)

        except Exception as e:
            logger.error(f"구매 명령어 실행 실패: {e}", exc_info=True)
            return self.create_error_result("구매 중 오류가 발생했습니다.")


class SellCommand(BaseCommand):
    """아이템을 판매하는 명령어"""

    def __init__(self):
        super().__init__(
            name="sell",
            aliases=[],
            description="상인에게 아이템을 판매합니다",
            usage="sell <아이템이름> [상인이름]"
        )

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        """아이템 판매 실행"""
        try:
            if not args:
                return self.create_error_result("무엇을 판매하시겠습니까? 사용법: sell <아이템이름> [상인이름]")

            # GameEngine을 통해 NPC 조회
            game_engine = getattr(session, 'game_engine', None)
            if not game_engine:
                return self.create_error_result("게임 엔진에 접근할 수 없습니다.")

            # 현재 방의 상인 NPC들 조회
            npcs_in_room = await game_engine.model_manager.npcs.get_npcs_in_room(session.current_room_id)
            merchants = [npc for npc in npcs_in_room if npc.is_merchant()]

            if not merchants:
                return self.create_error_result("이 방에는 상인이 없습니다.")

            # 플레이어 정보는 session.player에서 직접 가져옴
            if not session.player:
                return self.create_error_result("플레이어 정보를 찾을 수 없습니다.")
            player = session.player

            # 아이템 이름과 상인 이름 분리
            item_name = args[0]
            merchant_name = " ".join(args[1:]) if len(args) > 1 else None

            # 상인 찾기
            target_merchant = None
            if merchant_name:
                for merchant in merchants:
                    if (merchant_name.lower() in merchant.get_localized_name(session.locale).lower() or
                        merchant_name.lower() in merchant.get_localized_name('en').lower() or
                        merchant_name.lower() in merchant.get_localized_name('ko').lower()):
                        target_merchant = merchant
                        break

                if not target_merchant:
                    return self.create_error_result(f"'{merchant_name}'라는 상인을 찾을 수 없습니다.")
            else:
                target_merchant = merchants[0]

            # 인벤토리에서 아이템 찾기
            inventory_objects = await game_engine.world_manager.get_inventory_objects(session.player.id)
            target_item = None

            for item in inventory_objects:
                if (item_name.lower() in item.get_localized_name(session.locale).lower() or
                    item_name.lower() in item.get_localized_name('en').lower() or
                    item_name.lower() in item.get_localized_name('ko').lower()):
                    target_item = item
                    break

            if not target_item:
                return self.create_error_result(f"인벤토리에 '{item_name}'이(가) 없습니다.")

            # 판매 가격 계산 (구매 가격의 50%)
            original_price = target_item.get_property('price', 10)
            sell_price = max(1, original_price // 2)

            # 아이템 삭제
            await game_engine.model_manager.game_objects.delete(target_item.id)

            # 플레이어 골드 증가
            player.earn_gold(sell_price)
            await game_engine.model_manager.players.update(player.id, player.to_dict_with_password())

            # 성공 메시지
            item_display_name = target_item.get_localized_name(session.locale)
            merchant_display_name = target_merchant.get_localized_name(session.locale)

            message = f"{merchant_display_name}에게 {item_display_name}을(를) {sell_price} gold에 판매했습니다."
            message += f"\n현재 골드: {player.gold} gold"

            # 같은 방의 다른 플레이어들에게도 알림
            await game_engine.broadcast_to_room(
                session.current_room_id,
                {
                    "type": "room_message",
                    "message": f"{session.player.username}이(가) {merchant_display_name}에게 {item_display_name}을(를) 판매했습니다."
                },
                exclude_session=session.session_id
            )

            return self.create_success_result(message)

        except Exception as e:
            logger.error(f"판매 명령어 실행 실패: {e}", exc_info=True)
            return self.create_error_result("판매 중 오류가 발생했습니다.")