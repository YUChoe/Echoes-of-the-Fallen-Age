# -*- coding: utf-8 -*-
"""상인과 거래하는 명령어"""

import logging
from typing import List, Optional

from ...commands.base import BaseCommand, CommandResult
from ...core.localization import get_localization_manager
from ...core.types import SessionType
from ...game.monster import Monster

logger = logging.getLogger(__name__)

I18N = get_localization_manager()


class ShopCommand(BaseCommand):
    """상인과 거래하는 명령어"""

    def __init__(self):
        super().__init__(
            name="shop",
            aliases=["buy", "purchase", "store"],
            description="상인과 거래합니다",
            usage="shop [list|buy <아이템>] [상인이름]"
        )

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        """상인과 거래 실행"""
        try:
            locale = session.player.preferred_locale if session.player else 'en'

            if not args:
                return self.create_error_result(I18N.get_message("npc.shop.usage", locale))

            action = args[0].lower()

            # GameEngine을 통해 몬스터 조회
            game_engine = getattr(session, 'game_engine', None)
            if not game_engine:
                return self.create_error_result(I18N.get_message("npc.shop.no_engine", locale))

            # 플레이어 현재 좌표 가져오기
            current_room_id = getattr(session, 'current_room_id', None)
            if not current_room_id:
                return self.create_error_result(I18N.get_message("npc.shop.no_location", locale))

            current_room = await game_engine.world_manager.get_room(current_room_id)
            if not current_room or current_room.x is None or current_room.y is None:
                return self.create_error_result(I18N.get_message("npc.shop.no_room_coords", locale))

            player_x, player_y = current_room.x, current_room.y

            if action == "list":
                # 상인 찾기 (상인 이름 지정 가능)
                merchant = await self._find_merchant(game_engine, player_x, player_y, args[1:] if len(args) > 1 else [])
                if not merchant:
                    return self.create_error_result(I18N.get_message("npc.shop.no_merchant", locale))
                return await self._show_shop_list(merchant, locale)
            elif action == "buy":
                if len(args) < 2:
                    return self.create_error_result(I18N.get_message("npc.shop.buy_usage", locale))

                # 아이템 이름만 추출 (상인 이름은 자동으로 찾기)
                item_name = args[1]

                # 상인 찾기 (현재 위치의 모든 상인 중에서)
                merchant = await self._find_merchant(game_engine, player_x, player_y, [])
                if not merchant:
                    return self.create_error_result(I18N.get_message("npc.shop.no_merchant", locale))

                return await self._buy_item(session, game_engine, merchant, item_name, locale)
            else:
                return self.create_error_result(I18N.get_message("npc.shop.invalid_action", locale))

        except Exception as e:
            logger.error(f"상점 명령어 실행 실패: {e}", exc_info=True)
            locale = session.player.preferred_locale if session.player else 'en'
            return self.create_error_result(I18N.get_message("npc.shop.error", locale))

    async def _find_merchant(self, game_engine, x: int, y: int, merchant_args: List[str]) -> Optional[Monster]:  # type: ignore[no-untyped-def]
        """상인 몬스터 찾기"""
        try:
            monsters = await game_engine.world_manager.get_monsters_at_coordinates(x, y)

            for monster in monsters:
                # 몬스터가 상인인지 확인
                if not self._is_merchant(monster):
                    continue

                # 특정 상인을 지정했다면 이름 매칭
                if merchant_args:
                    merchant_name = " ".join(merchant_args)
                    monster_name_en = monster.get_localized_name('en').lower()
                    monster_name_ko = monster.get_localized_name('ko').lower()

                    if (merchant_name.lower() not in monster_name_en and
                        merchant_name.lower() not in monster_name_ko):
                        continue

                return monster

            return None

        except Exception as e:
            logger.error(f"상인 찾기 실패: {e}")
            return None

    def _is_merchant(self, monster: Monster) -> bool:
        """몬스터가 상인인지 확인"""
        try:
            if hasattr(monster, 'properties') and monster.properties:
                properties = monster.properties
                if isinstance(properties, str):
                    import json
                    properties = json.loads(properties)

                if isinstance(properties, dict):
                    return 'merchant_type' in properties or 'shop_items' in properties

            return False

        except Exception as e:
            logger.error(f"상인 확인 실패: {e}")
            return False

    async def _show_shop_list(self, merchant: Monster, locale: str) -> CommandResult:
        """상점 목록 표시"""
        try:
            properties = merchant.properties
            if isinstance(properties, str):
                import json
                properties = json.loads(properties)

            shop_name = properties.get('shop_name', {}).get(locale, 'Shop')
            greeting = properties.get('greeting', {}).get(locale, ['Welcome to my shop!'])
            shop_items = properties.get('shop_items', [])

            if not shop_items:
                return self.create_error_result(I18N.get_message("npc.shop.no_items", locale))

            # 상점 목록 생성
            message_lines = [
                f"🏪 {shop_name}",
                "=" * 50
            ]

            # 인사말 추가
            if isinstance(greeting, list) and greeting:
                import random
                message_lines.append(f'"{random.choice(greeting)}"')
                message_lines.append("")

            # 상품 목록
            message_lines.append(I18N.get_message("npc.shop.list_header", locale))

            for i, item in enumerate(shop_items, 1):
                item_id = item.get('item_id', 'unknown')
                price = item.get('price', 0)
                currency = item.get('currency', 'gold')
                description = item.get('description', {}).get(locale, 'No description')

                # 통화 표시
                currency_symbol = "💰" if currency == "gold" else "✨" if currency == "essence_of_life" else "💎"
                currency_name = "골드" if currency == "gold" else "생명의 정수" if currency == "essence_of_life" else currency

                if price == 0:
                    price_text = I18N.get_message("npc.shop.price_free", locale)
                else:
                    price_text = f"{price} {currency_name}"

                message_lines.append(f"{i}. {item_id} - {price_text} {currency_symbol}")
                message_lines.append(f"   {description}")

            message_lines.append("")
            message_lines.append(I18N.get_message("npc.shop.list_hint", locale))

            return self.create_success_result("\n".join(message_lines))

        except Exception as e:
            logger.error(f"상점 목록 표시 실패: {e}")
            return self.create_error_result(I18N.get_message("npc.shop.list_error", locale))

    async def _buy_item(self, session, game_engine, merchant: Monster, item_name: str, locale: str) -> CommandResult:  # type: ignore[no-untyped-def]
        """아이템 구매"""
        try:
            properties = merchant.properties
            if isinstance(properties, str):
                import json
                properties = json.loads(properties)

            shop_items = properties.get('shop_items', [])

            # 아이템 찾기
            target_item = None
            for item in shop_items:
                if item_name.lower() in item.get('item_id', '').lower():
                    target_item = item
                    break

            if not target_item:
                return self.create_error_result(
                    I18N.get_message("npc.shop.item_not_found", locale, item_name=item_name)
                )

            item_id = target_item.get('item_id')
            price = target_item.get('price', 0)
            currency = target_item.get('currency', 'gold')
            quest_completion = target_item.get('quest_completion')

            # 퀘스트 완료 조건 확인
            if quest_completion:
                completed_quests = getattr(session.player, 'completed_quests', [])
                if quest_completion not in completed_quests:
                    return self.create_error_result(
                        I18N.get_message("npc.shop.quest_required", locale)
                    )

            # 결제 처리
            if price > 0:
                payment_result = await self._process_payment(session, game_engine, currency, price, locale)
                if not payment_result:
                    return self.create_error_result(I18N.get_message("npc.shop.payment_failed", locale))

            # 아이템 지급
            success = await self._give_item_to_player(session, game_engine, item_id)
            if not success:
                return self.create_error_result(I18N.get_message("npc.shop.give_item_failed", locale))

            # 성공 메시지
            currency_name = "골드" if currency == "gold" else "생명의 정수" if currency == "essence_of_life" else currency

            if price == 0:
                price_text = I18N.get_message("npc.shop.price_free", locale)
            else:
                price_text = f"{price} {currency_name}"

            # 특별한 아이템 구매 시 퀘스트 완료 처리
            if item_id == "castle_key" and quest_completion:
                await self._complete_quest(session, game_engine, quest_completion)

                return self.create_success_result(
                    I18N.get_message("npc.shop.purchase_quest_complete", locale,
                                     item_id=item_id, price_text=price_text)
                )

            return self.create_success_result(
                I18N.get_message("npc.shop.purchase_success", locale,
                                 item_id=item_id, price_text=price_text)
            )

        except Exception as e:
            logger.error(f"아이템 구매 실패: {e}")
            return self.create_error_result(I18N.get_message("npc.shop.buy_error", locale))

    async def _process_payment(self, session, game_engine, currency: str, amount: int, locale: str) -> bool:  # type: ignore[no-untyped-def]
        """결제 처리"""
        try:
            if currency == "gold":
                # 골드 결제 - 현재 보상 시스템 재개발 중으로 비활성화
                logger.warning("골드 결제 시스템은 현재 비활성화되어 있습니다.")
                return False

            elif currency == "essence_of_life":
                # 생명의 정수 결제
                essence_count = await self._count_player_essence(session, game_engine)
                if essence_count < amount:
                    return False

                removed = await self._remove_player_essence(session, game_engine, amount)
                return removed >= amount

            return False

        except Exception as e:
            logger.error(f"결제 처리 실패: {e}")
            return False

    async def _count_player_essence(self, session, game_engine) -> int:  # type: ignore[no-untyped-def]
        """플레이어의 생명의 정수 개수 확인"""
        try:
            inventory_objects = await game_engine.world_manager.get_inventory_objects(session.player.id)
            count = 0

            for obj in inventory_objects:
                obj_name_en = obj.get_localized_name("en").lower()
                obj_name_ko = obj.get_localized_name("ko").lower()

                if "essence" in obj_name_en or "정수" in obj_name_ko:
                    count += 1

            return count

        except Exception as e:
            logger.error(f"생명의 정수 개수 확인 실패: {e}")
            return 0

    async def _remove_player_essence(self, session, game_engine, amount: int) -> int:  # type: ignore[no-untyped-def]
        """플레이어의 생명의 정수 제거"""
        try:
            inventory_objects = await game_engine.world_manager.get_inventory_objects(session.player.id)
            removed_count = 0

            for obj in inventory_objects:
                if removed_count >= amount:
                    break

                obj_name_en = obj.get_localized_name("en").lower()
                obj_name_ko = obj.get_localized_name("ko").lower()

                if "essence" in obj_name_en or "정수" in obj_name_ko:
                    success = await game_engine.world_manager.remove_object(obj.id)
                    if success:
                        removed_count += 1

            return removed_count

        except Exception as e:
            logger.error(f"생명의 정수 제거 실패: {e}")
            return 0

    async def _give_item_to_player(self, session, game_engine, item_id: str) -> bool:  # type: ignore[no-untyped-def]
        """플레이어에게 아이템 지급"""
        try:
            from uuid import uuid4

            # 템플릿 아이템 조회
            template = await game_engine.world_manager.get_game_object(item_id)
            if not template:
                return False

            # 새 아이템 생성
            new_item_data = template.to_dict()
            new_item_data['id'] = str(uuid4())
            new_item_data['location_type'] = 'inventory'
            new_item_data['location_id'] = session.player.id

            # 데이터베이스에 저장
            await game_engine.model_manager.game_objects.create(new_item_data)
            logger.info(f"플레이어 {session.player.username}에게 아이템 {item_id} 지급")

            return True

        except Exception as e:
            logger.error(f"아이템 지급 실패: {e}")
            return False

    async def _complete_quest(self, session, game_engine, quest_id: str) -> None:  # type: ignore[no-untyped-def]
        """퀘스트 완료 처리"""
        try:
            if not hasattr(session.player, 'completed_quests') or not isinstance(session.player.completed_quests, list):
                session.player.completed_quests = []

            if quest_id not in session.player.completed_quests:
                session.player.completed_quests.append(quest_id)

                # 진행 중인 퀘스트에서 제거
                if (hasattr(session.player, 'quest_progress') and
                    isinstance(session.player.quest_progress, dict) and
                    quest_id in session.player.quest_progress):
                    del session.player.quest_progress[quest_id]

                # 데이터베이스 업데이트
                await game_engine.model_manager.players.update(session.player.id, {
                    'completed_quests': session.player.completed_quests,
                    'quest_progress': session.player.quest_progress
                })

                logger.info(f"플레이어 {session.player.username}이 퀘스트 {quest_id} 완료")

        except Exception as e:
            logger.error(f"퀘스트 완료 처리 실패: {e}")
