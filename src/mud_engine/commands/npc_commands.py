"""
NPC 상호작용 명령어들
"""

import logging
from datetime import datetime
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
                return self.create_error_result("누구와 대화하시겠습니까? 사용법: talk <NPC이름 또는 번호>")

            npc_input = " ".join(args)

            # GameEngine을 통해 NPC 조회
            game_engine = getattr(session, 'game_engine', None)
            if not game_engine:
                return self.create_error_result("게임 엔진에 접근할 수 없습니다.")

            # 번호로 입력된 경우 처리
            target_entity = None
            entity_type = None

            if npc_input.isdigit():
                entity_num = int(npc_input)
                entity_map = getattr(session, 'room_entity_map', {})

                if entity_num in entity_map:
                    entity_info = entity_map[entity_num]
                    target_entity = entity_info['entity']
                    entity_type = entity_info['type']
                else:
                    return self.create_error_result(
                        f"번호 [{entity_num}]에 해당하는 대상을 찾을 수 없습니다."
                    )
            else:
                # 이름으로 검색 - NPC 먼저
                npc_name = npc_input
                npcs_in_room = await game_engine.model_manager.npcs.get_npcs_in_room(session.current_room_id)

                for npc in npcs_in_room:
                    if (npc_name.lower() in npc.get_localized_name(session.locale).lower() or
                        npc_name.lower() in npc.get_localized_name('en').lower() or
                        npc_name.lower() in npc.get_localized_name('ko').lower()):
                        target_entity = npc
                        entity_type = 'npc'
                        break

                # NPC를 못 찾았으면 몬스터 검색
                if not target_entity:
                    monsters = await game_engine.world_manager.get_monsters_in_room(session.current_room_id)
                    for monster in monsters:
                        if (npc_name.lower() in monster.get_localized_name(session.locale).lower() or
                            npc_name.lower() in monster.get_localized_name('en').lower() or
                            npc_name.lower() in monster.get_localized_name('ko').lower()):
                            target_entity = monster
                            entity_type = 'monster'
                            break

            if not target_entity:
                return self.create_error_result(f"'{npc_input}'을(를) 찾을 수 없습니다.")

            # 몬스터인 경우 우호도 확인
            if entity_type == 'monster':
                player_faction = session.player.faction_id or 'ash_knights'
                monster_faction = target_entity.faction_id

                # 우호도 확인 (같은 종족이거나 중립 이상)
                if monster_faction != player_faction:
                    # 적대적이면 대화 불가
                    if not self._is_neutral_or_friendly(player_faction, monster_faction):
                        return self.create_error_result(
                            f"{target_entity.get_localized_name(session.locale)}은(는) 적대적이어서 대화할 수 없습니다."
                        )

            target_npc = target_entity

            # 대화 가져오기
            npc_display_name = target_npc.get_localized_name(session.locale)

            # NPC인 경우 대화 내용 가져오기
            if entity_type == 'npc':
                dialogue = target_npc.get_random_dialogue(session.locale)
            else:
                # 몬스터인 경우 기본 대화
                dialogue = "..."  # 몬스터는 말을 하지 않음
                if hasattr(target_npc, 'get_random_dialogue'):
                    dialogue = target_npc.get_random_dialogue(session.locale)

            # 퀘스트 시스템 연동 (NPC인 경우만)
            quest_message = ""
            if entity_type == 'npc' and target_npc.npc_type == 'quest_giver':
                quest_message = await _handle_quest_interaction(session, target_npc, game_engine)

            # 대화 메시지 생성
            if dialogue == "...":
                message = f"{npc_display_name}은(는) 당신을 조용히 바라봅니다."
            else:
                message = f"{npc_display_name}: \"{dialogue}\""

            # 퀘스트 메시지 추가
            if quest_message:
                message += f"\n\n{quest_message}"

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

    def _is_neutral_or_friendly(self, player_faction: str, monster_faction: Optional[str]) -> bool:
        """플레이어와 몬스터 종족 간의 중립 또는 우호 관계 확인

        Args:
            player_faction: 플레이어 종족 ID
            monster_faction: 몬스터 종족 ID

        Returns:
            bool: 중립 이상이면 True
        """
        # 같은 종족이면 우호적
        if monster_faction == player_faction:
            return True

        # 몬스터 종족이 없으면 적대적으로 간주
        if not monster_faction:
            return False

        # 중립 종족 목록 (추후 DB에서 동적으로 로드 가능)
        neutral_factions: dict[str, list[str]] = {
            'ash_knights': [],  # 현재는 중립 종족 없음
        }

        # 중립 종족이면 True
        if player_faction in neutral_factions:
            if monster_faction in neutral_factions[player_faction]:
                return True

        return False


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
                merchant_input = " ".join(args)

                # 번호로 입력된 경우 처리
                if merchant_input.isdigit():
                    entity_num = int(merchant_input)
                    entity_map = getattr(session, 'room_entity_map', {})

                    if entity_num in entity_map:
                        entity_info = entity_map[entity_num]
                        if entity_info['type'] == 'npc':
                            npc = entity_info['entity']
                            if npc.is_merchant():
                                target_merchant = npc
                            else:
                                return self.create_error_result(
                                    f"[{entity_num}]은(는) 상인이 아닙니다."
                                )
                        else:
                            return self.create_error_result(
                                f"[{entity_num}]은(는) NPC가 아닙니다."
                            )
                    else:
                        return self.create_error_result(
                            f"번호 [{entity_num}]에 해당하는 대상을 찾을 수 없습니다."
                        )
                else:
                    # 이름으로 검색
                    merchant_name = merchant_input
                    for merchant in merchants:
                        if (merchant_name.lower() in merchant.get_localized_name(session.locale).lower() or
                            merchant_name.lower() in merchant.get_localized_name('en').lower() or
                            merchant_name.lower() in merchant.get_localized_name('ko').lower()):
                            target_merchant = merchant
                            break

                    if not target_merchant:
                        return self.create_error_result(f"'{merchant_name}'라는 상인을 찾을 수 없습니다.")
            else:
                # 상인을 지정하지 않은 경우 에러
                return self.create_error_result(
                    "상인을 지정해주세요.\n사용법: shop <번호 또는 상인이름>"
                )

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

async def _handle_quest_interaction(session, npc, game_engine) -> str:
        """퀘스트 NPC와의 상호작용 처리"""
        try:
            from ..game.quest import get_quest_manager

            quest_manager = get_quest_manager()
            locale = session.player.preferred_locale if session.player else "en"

            # 교회 수도사와의 상호작용
            if npc.id == "church_monk":
                return await _handle_church_monk_quest(session, game_engine, quest_manager, locale)

            return ""

        except Exception as e:
            logger.error(f"퀘스트 상호작용 처리 실패: {e}")
            return ""

async def _handle_church_monk_quest(session, game_engine, quest_manager, locale: str) -> str:
        """교회 수도사 퀘스트 처리"""
        quest_id = "tutorial_basic_equipment"

        # 플레이어의 퀘스트 상태 확인
        completed_quests = getattr(session.player, 'completed_quests', [])
        quest_progress = getattr(session.player, 'quest_progress', {})

        # 이미 완료한 퀘스트인지 확인
        if quest_id in completed_quests:
            if locale == "ko":
                return "🎉 이미 기본 장비를 받으셨군요. 모험을 즐기세요!"
            else:
                return "🎉 You already received your basic equipment. Enjoy your adventure!"

        # 진행 중인 퀘스트인지 확인
        if quest_id in quest_progress:
            # 생명의 정수 수집 확인
            essence_count = await _count_player_items(session, game_engine, "essence_of_life")

            if essence_count >= 10:
                # 퀘스트 완료 가능
                return await _complete_tutorial_quest(session, game_engine, locale)
            else:
                # 아직 수집 중
                remaining = 10 - essence_count
                if locale == "ko":
                    return f"📋 생명의 정수를 {essence_count}/10개 수집하셨군요. {remaining}개 더 필요합니다."
                else:
                    return f"📋 You have collected {essence_count}/10 Essence of Life. You need {remaining} more."
        else:
            # 새로운 퀘스트 시작
            return await _start_tutorial_quest(session, game_engine, quest_manager, locale)

async def _start_tutorial_quest(session, game_engine, quest_manager, locale: str) -> str:
        """튜토리얼 퀘스트 시작"""
        quest_id = "tutorial_basic_equipment"

        # 퀘스트 진행 상황 초기화
        if not hasattr(session.player, 'quest_progress'):
            session.player.quest_progress = {}

        session.player.quest_progress[quest_id] = {
            "status": "in_progress",
            "started_at": datetime.now().isoformat(),
            "objectives": {
                "talk_to_monk": 1,  # 이미 대화함
                "collect_essence": 0
            }
        }

        # 데이터베이스 업데이트
        try:
            from ..game.repositories import PlayerRepository
            from ..database import get_database_manager

            db_manager = await get_database_manager()
            player_repo = PlayerRepository(db_manager)

            await player_repo.update(session.player.id, {
                'quest_progress': session.player.quest_progress
            })

            logger.info(f"플레이어 {session.player.username}이 튜토리얼 퀘스트 시작")

        except Exception as e:
            logger.error(f"퀘스트 진행 상황 저장 실패: {e}")

        if locale == "ko":
            return """📜 퀘스트 시작: 기본 장비

🎯 목표: 생명의 정수 10개 수집
📍 위치: 야생 몬스터 처치 시 획득 가능

완료 후 다시 저에게 오시면 기본 장비를 드리겠습니다:
• 나무 곤봉 (무기)
• 리넨 상의 (방어구)
• 리넨 하의 (방어구)"""
        else:
            return """📜 Quest Started: Basic Equipment

🎯 Objective: Collect 10 Essence of Life
📍 Location: Obtainable by defeating monsters in the wilderness

Return to me when completed to receive basic equipment:
• Wooden Club (weapon)
• Linen Shirt (armor)
• Linen Pants (armor)"""

async def _complete_tutorial_quest(session, game_engine, locale: str) -> str:
        """튜토리얼 퀘스트 완료"""
        quest_id = "tutorial_basic_equipment"

        try:
            # 생명의 정수 10개 제거
            removed_count = await _remove_player_items(session, game_engine, "essence_of_life", 10)

            if removed_count < 10:
                if locale == "ko":
                    return f"❌ 생명의 정수가 부족합니다. ({removed_count}/10개)"
                else:
                    return f"❌ Not enough Essence of Life. ({removed_count}/10)"

            # 기본 장비 지급
            equipment_given = await _give_tutorial_equipment(session, game_engine)

            # 퀘스트 완료 처리
            if not hasattr(session.player, 'completed_quests'):
                session.player.completed_quests = []

            session.player.completed_quests.append(quest_id)

            # 진행 중인 퀘스트에서 제거
            if hasattr(session.player, 'quest_progress') and quest_id in session.player.quest_progress:
                del session.player.quest_progress[quest_id]

            # 데이터베이스 업데이트
            from ..game.repositories import PlayerRepository
            from ..database import get_database_manager

            db_manager = await get_database_manager()
            player_repo = PlayerRepository(db_manager)

            await player_repo.update(session.player.id, {
                'completed_quests': session.player.completed_quests,
                'quest_progress': session.player.quest_progress
            })

            logger.info(f"플레이어 {session.player.username}이 튜토리얼 퀘스트 완료")

            if locale == "ko":
                return f"""🎉 퀘스트 완료: 기본 장비

✅ 생명의 정수 10개를 받았습니다.
🎁 보상으로 기본 장비를 지급했습니다:
{equipment_given}

이제 모험을 시작할 준비가 되었습니다!"""
            else:
                return f"""🎉 Quest Completed: Basic Equipment

✅ Received 10 Essence of Life.
🎁 Basic equipment has been given as reward:
{equipment_given}

You are now ready to begin your adventure!"""

        except Exception as e:
            logger.error(f"튜토리얼 퀘스트 완료 처리 실패: {e}")
            if locale == "ko":
                return "❌ 퀘스트 완료 처리 중 오류가 발생했습니다."
            else:
                return "❌ An error occurred while completing the quest."

async def _count_player_items(session, game_engine, item_name: str) -> int:
        """플레이어 인벤토리에서 특정 아이템 개수 확인"""
        try:
            inventory_objects = await game_engine.world_manager.get_inventory_objects(session.player.id)
            count = 0

            for obj in inventory_objects:
                obj_name_en = obj.get_localized_name("en").lower()
                obj_name_ko = obj.get_localized_name("ko").lower()

                if (item_name.lower() in obj_name_en or
                    item_name.lower() in obj_name_ko or
                    "essence" in obj_name_en):
                    # 스택 가능한 아이템인 경우 수량 확인
                    if hasattr(obj, 'properties') and obj.properties:
                        if isinstance(obj.properties, dict):
                            count += obj.properties.get('quantity', 1)
                        else:
                            count += 1
                    else:
                        count += 1

            return count

        except Exception as e:
            logger.error(f"아이템 개수 확인 실패: {e}")
            return 0

async def _remove_player_items(session, game_engine, item_name: str, count: int) -> int:
        """플레이어 인벤토리에서 특정 아이템 제거"""
        try:
            inventory_objects = await game_engine.world_manager.get_inventory_objects(session.player.id)
            removed_count = 0

            for obj in inventory_objects:
                if removed_count >= count:
                    break

                obj_name_en = obj.get_localized_name("en").lower()
                obj_name_ko = obj.get_localized_name("ko").lower()

                if (item_name.lower() in obj_name_en or
                    item_name.lower() in obj_name_ko or
                    "essence" in obj_name_en):

                    # 아이템 제거
                    success = await game_engine.world_manager.remove_object(obj.id)
                    if success:
                        # 스택 가능한 아이템인 경우 수량 확인
                        if hasattr(obj, 'properties') and obj.properties:
                            if isinstance(obj.properties, dict):
                                removed_count += obj.properties.get('quantity', 1)
                            else:
                                removed_count += 1
                        else:
                            removed_count += 1

            return min(removed_count, count)

        except Exception as e:
            logger.error(f"아이템 제거 실패: {e}")
            return 0

async def _give_tutorial_equipment(session, game_engine) -> str:
        """튜토리얼 기본 장비 지급"""
        try:
            equipment_items = [
                "tutorial_club",
                "tutorial_linen_shirt",
                "tutorial_linen_pants"
            ]

            given_items = []

            for item_id in equipment_items:
                # 템플릿에서 아이템 복사하여 생성
                success = await _create_item_from_template(session, game_engine, item_id)
                if success:
                    # 아이템 이름 가져오기
                    template = await game_engine.world_manager.get_game_object(item_id)
                    if template:
                        item_name = template.get_localized_name(session.player.preferred_locale)
                        given_items.append(f"• {item_name}")

            return "\n".join(given_items) if given_items else "장비 지급 실패"

        except Exception as e:
            logger.error(f"튜토리얼 장비 지급 실패: {e}")
            return "장비 지급 중 오류 발생"

async def _create_item_from_template(session, game_engine, template_id: str) -> bool:
        """템플릿에서 아이템을 복사하여 플레이어에게 지급"""
        try:
            from ..game.repositories import GameObjectRepository
            from ..database import get_database_manager
            from uuid import uuid4

            # 템플릿 아이템 조회
            template = await game_engine.world_manager.get_game_object(template_id)
            if not template:
                return False

            # 새 아이템 생성 (템플릿 복사)
            new_item_data = template.to_dict()
            new_item_data['id'] = str(uuid4())
            new_item_data['location_type'] = 'inventory'
            new_item_data['location_id'] = session.player.id

            # 데이터베이스에 저장
            db_manager = await get_database_manager()
            object_repo = GameObjectRepository(db_manager)

            await object_repo.create(new_item_data)
            logger.info(f"플레이어 {session.player.username}에게 아이템 {template_id} 지급")

            return True

        except Exception as e:
            logger.error(f"템플릿에서 아이템 생성 실패: {e}")
            return False