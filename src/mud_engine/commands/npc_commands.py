"""
몬스터 상호작용 명령어들 (좌표 기반)
"""

import logging
from datetime import datetime
from typing import List, Optional

from .base import BaseCommand, CommandResult
from ..core.types import SessionType
from ..game.monster import Monster
from ..game.models import GameObject

logger = logging.getLogger(__name__)


class TalkCommand(BaseCommand):
    """몬스터와 대화하는 명령어"""

    def __init__(self):
        super().__init__(
            name="talk",
            aliases=["speak", "chat"],
            description="몬스터와 대화합니다",
            usage="talk <몬스터이름>"
        )

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        """몬스터와 대화 실행"""
        try:
            if not args:
                return self.create_error_result("누구와 대화하시겠습니까? 사용법: talk <몬스터이름>")

            monster_input = " ".join(args)

            # GameEngine을 통해 몬스터 조회
            game_engine = getattr(session, 'game_engine', None)
            if not game_engine:
                return self.create_error_result("게임 엔진에 접근할 수 없습니다.")

            # 플레이어 현재 좌표 가져오기
            current_room_id = getattr(session, 'current_room_id', None)
            if not current_room_id:
                return self.create_error_result("현재 위치를 확인할 수 없습니다.")

            current_room = await game_engine.world_manager.get_room(current_room_id)
            if not current_room or current_room.x is None or current_room.y is None:
                return self.create_error_result("현재 방의 좌표를 확인할 수 없습니다.")

            player_x, player_y = current_room.x, current_room.y

            # 몬스터 검색
            monsters = await game_engine.world_manager.get_monsters_at_coordinates(player_x, player_y)
            target_monster = None

            for monster in monsters:
                locale = session.player.preferred_locale if session.player else 'en'
                if (monster_input.lower() in monster.get_localized_name(locale).lower() or
                    monster_input.lower() in monster.get_localized_name('en').lower() or
                    monster_input.lower() in monster.get_localized_name('ko').lower()):
                    target_monster = monster
                    break

            if not target_monster:
                return self.create_error_result(f"'{monster_input}'을(를) 찾을 수 없습니다.")

            # 몬스터 우호도 확인
            player_faction = session.player.faction_id or 'ash_knights'
            monster_faction = getattr(target_monster, 'faction_id', None)

            # 중립 몬스터이거나 같은 팩션이면 대화 가능
            if monster_faction and monster_faction != 'neutral' and monster_faction != player_faction:
                locale = session.player.preferred_locale if session.player else 'en'
                return self.create_error_result(
                    f"{target_monster.get_localized_name(locale)}은(는) 적대적이어서 대화할 수 없습니다."
                )

            # 대화 가져오기
            locale = session.player.preferred_locale if session.player else 'en'
            monster_display_name = target_monster.get_localized_name(locale)

            # 몬스터 대화 내용 가져오기
            dialogue = self._get_monster_dialogue(target_monster, locale)

            # 퀘스트 시스템 연동 (특정 몬스터만)
            quest_message = ""
            if target_monster.id == 'church_monk':
                quest_message = await self._handle_quest_interaction(session, target_monster, game_engine)

            # 대화 메시지 생성
            if dialogue == "...":
                message = f"{monster_display_name}은(는) 당신을 조용히 바라봅니다."
            else:
                message = f"{monster_display_name}: \"{dialogue}\""

            # 퀘스트 메시지 추가
            if quest_message:
                message += f"\n\n{quest_message}"

            # 같은 방의 다른 플레이어들에게도 알림
            await game_engine.broadcast_to_room(
                session.current_room_id,
                {
                    "type": "room_message",
                    "message": f"{session.player.username}이(가) {monster_display_name}와(과) 대화하고 있습니다."
                },
                exclude_session=session.session_id
            )

            return self.create_success_result(message)

        except Exception as e:
            logger.error(f"대화 명령어 실행 실패: {e}", exc_info=True)
            return self.create_error_result("대화 중 오류가 발생했습니다.")

    def _get_monster_dialogue(self, monster: Monster, locale: str) -> str:
        """몬스터 대화 내용 가져오기"""
        try:
            # 몬스터의 properties에서 dialogue 정보 가져오기
            if hasattr(monster, 'properties') and monster.properties:
                properties = monster.properties
                if isinstance(properties, str):
                    import json
                    properties = json.loads(properties)

                if isinstance(properties, dict) and 'dialogue' in properties:
                    dialogue_data = properties['dialogue']
                    if isinstance(dialogue_data, dict):
                        dialogue_list = dialogue_data.get(locale, dialogue_data.get('en', ['...']))
                        if dialogue_list and isinstance(dialogue_list, list):
                            import random
                            return random.choice(dialogue_list)

            return "..."
        except Exception as e:
            logger.error(f"몬스터 대화 내용 가져오기 실패: {e}")
            return "..."

    async def _handle_quest_interaction(self, session, monster, game_engine) -> str:
        """퀘스트 몬스터와의 상호작용 처리"""
        try:
            from ..game.quest import get_quest_manager

            quest_manager = get_quest_manager()
            locale = session.player.preferred_locale if session.player else "en"

            # 교회 수도사와의 상호작용
            if monster.id == "church_monk":
                return await self._handle_church_monk_quest(session, game_engine, quest_manager, locale)

            return ""

        except Exception as e:
            logger.error(f"퀘스트 상호작용 처리 실패: {e}")
            return ""

    async def _handle_church_monk_quest(self, session, game_engine, quest_manager, locale: str) -> str:
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
            essence_count = await self._count_player_items(session, game_engine, "essence_of_life")

            if essence_count >= 10:
                # 퀘스트 완료 가능
                return await self._complete_tutorial_quest(session, game_engine, locale)
            else:
                # 아직 수집 중
                remaining = 10 - essence_count
                if locale == "ko":
                    return f"📋 생명의 정수를 {essence_count}/10개 수집하셨군요. {remaining}개 더 필요합니다."
                else:
                    return f"📋 You have collected {essence_count}/10 Essence of Life. You need {remaining} more."
        else:
            # 새로운 퀘스트 시작
            return await self._start_tutorial_quest(session, game_engine, quest_manager, locale)

    async def _start_tutorial_quest(self, session, game_engine, quest_manager, locale: str) -> str:
        """튜토리얼 퀘스트 시작"""
        quest_id = "tutorial_basic_equipment"

        # 퀘스트 진행 상황 초기화
        if not hasattr(session.player, 'quest_progress') or not isinstance(session.player.quest_progress, dict):
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
            await game_engine.model_manager.players.update(session.player.id, {
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
• Linen Trousers (armor)"""

    async def _complete_tutorial_quest(self, session, game_engine, locale: str) -> str:
        """튜토리얼 퀘스트 완료"""
        quest_id = "tutorial_basic_equipment"

        try:
            # 생명의 정수 10개 제거
            removed_count = await self._remove_player_items(session, game_engine, "essence_of_life", 10)

            if removed_count < 10:
                if locale == "ko":
                    return f"❌ 생명의 정수가 부족합니다. ({removed_count}/10개)"
                else:
                    return f"❌ Not enough Essence of Life. ({removed_count}/10)"

            # 기본 장비 지급
            equipment_given = await self._give_tutorial_equipment(session, game_engine)

            # 퀘스트 완료 처리
            if not hasattr(session.player, 'completed_quests') or not isinstance(session.player.completed_quests, list):
                session.player.completed_quests = []

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

    async def _count_player_items(self, session, game_engine, item_name: str) -> int:
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

    async def _remove_player_items(self, session, game_engine, item_name: str, count: int) -> int:
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

    async def _give_tutorial_equipment(self, session, game_engine) -> str:
        """튜토리얼 기본 장비 지급"""
        try:
            equipment_items = [
                "tutorial_club",
                "tutorial_linen_shirt",
                "tutorial_linen_trousers"
            ]

            given_items = []

            for item_id in equipment_items:
                # 템플릿에서 아이템 복사하여 생성
                success = await self._create_item_from_template(session, game_engine, item_id)
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

    async def _create_item_from_template(self, session, game_engine, template_id: str) -> bool:
        """템플릿에서 아이템을 복사하여 플레이어에게 지급"""
        try:
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
            await game_engine.model_manager.game_objects.create(new_item_data)
            logger.info(f"플레이어 {session.player.username}에게 아이템 {template_id} 지급")

            return True

        except Exception as e:
            logger.error(f"템플릿에서 아이템 생성 실패: {e}")
            return False


class TradeCommand(BaseCommand):
    """몬스터와 거래하는 명령어 (퀘스트용)"""

    def __init__(self):
        super().__init__(
            name="trade",
            aliases=["give"],
            description="몬스터와 아이템을 거래합니다",
            usage="trade <아이템이름> <몬스터이름>"
        )

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        """몬스터와 거래 실행"""
        try:
            if len(args) < 2:
                return self.create_error_result("사용법: trade <아이템이름> <몬스터이름>")

            item_name = args[0]
            monster_name = " ".join(args[1:])

            # GameEngine을 통해 몬스터 조회
            game_engine = getattr(session, 'game_engine', None)
            if not game_engine:
                return self.create_error_result("게임 엔진에 접근할 수 없습니다.")

            # 플레이어 현재 좌표 가져오기
            current_room_id = getattr(session, 'current_room_id', None)
            if not current_room_id:
                return self.create_error_result("현재 위치를 확인할 수 없습니다.")

            current_room = await game_engine.world_manager.get_room(current_room_id)
            if not current_room or current_room.x is None or current_room.y is None:
                return self.create_error_result("현재 방의 좌표를 확인할 수 없습니다.")

            player_x, player_y = current_room.x, current_room.y

            # 몬스터 찾기
            monsters = await game_engine.world_manager.get_monsters_at_coordinates(player_x, player_y)
            target_monster = None

            for monster in monsters:
                locale = session.player.preferred_locale if session.player else 'en'
                if (monster_name.lower() in monster.get_localized_name(locale).lower() or
                    monster_name.lower() in monster.get_localized_name('en').lower() or
                    monster_name.lower() in monster.get_localized_name('ko').lower()):
                    target_monster = monster
                    break

            if not target_monster:
                return self.create_error_result(f"'{monster_name}'을(를) 찾을 수 없습니다.")

            # 교회 수도사와의 거래 처리
            if target_monster.id == "church_monk":
                return await self._handle_monk_trade(session, game_engine, target_monster, item_name)

            return self.create_error_result("이 몬스터는 거래를 하지 않습니다.")

        except Exception as e:
            logger.error(f"거래 명령어 실행 실패: {e}", exc_info=True)
            return self.create_error_result("거래 중 오류가 발생했습니다.")

    async def _handle_monk_trade(self, session, game_engine, monster, item_name: str) -> CommandResult:
        """수도사와의 거래 처리"""
        try:
            locale = session.player.preferred_locale if session.player else "en"

            # 퀘스트 완료 여부 확인
            completed_quests = getattr(session.player, 'completed_quests', [])
            if "tutorial_basic_equipment" in completed_quests:
                if locale == "ko":
                    return self.create_error_result("이미 퀘스트를 완료하셨습니다. 더 이상 거래할 수 없습니다.")
                else:
                    return self.create_error_result("You have already completed the quest. No more trades available.")

            # 생명의 정수인지 확인
            if "essence" not in item_name.lower() and "정수" not in item_name:
                if locale == "ko":
                    return self.create_error_result("수도사는 생명의 정수만 받습니다.")
                else:
                    return self.create_error_result("The monk only accepts Essence of Life.")

            # 플레이어가 생명의 정수를 가지고 있는지 확인
            inventory_objects = await game_engine.world_manager.get_inventory_objects(session.player.id)
            essence_items = []

            for obj in inventory_objects:
                obj_name_en = obj.get_localized_name("en").lower()
                obj_name_ko = obj.get_localized_name("ko").lower()

                if ("essence" in obj_name_en or "정수" in obj_name_ko):
                    essence_items.append(obj)

            if not essence_items:
                if locale == "ko":
                    return self.create_error_result("생명의 정수를 가지고 있지 않습니다.")
                else:
                    return self.create_error_result("You don't have any Essence of Life.")

            # 생명의 정수 개수 확인
            total_essence = len(essence_items)

            if total_essence < 10:
                if locale == "ko":
                    return self.create_error_result(f"생명의 정수가 부족합니다. ({total_essence}/10개)")
                else:
                    return self.create_error_result(f"Not enough Essence of Life. ({total_essence}/10)")

            # 퀘스트 완료 처리
            talk_command = TalkCommand()
            result = await talk_command._complete_tutorial_quest(session, game_engine, locale)

            return self.create_success_result(result)

        except Exception as e:
            logger.error(f"수도사 거래 처리 실패: {e}")
            locale = session.player.preferred_locale if session.player else "en"
            if locale == "ko":
                return self.create_error_result("거래 처리 중 오류가 발생했습니다.")
            else:
                return self.create_error_result("An error occurred during the trade.")


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
            if not args:
                return self.create_error_result("사용법: shop list [상인이름] 또는 shop buy <아이템> [상인이름]")

            action = args[0].lower()

            # GameEngine을 통해 몬스터 조회
            game_engine = getattr(session, 'game_engine', None)
            if not game_engine:
                return self.create_error_result("게임 엔진에 접근할 수 없습니다.")

            # 플레이어 현재 좌표 가져오기
            current_room_id = getattr(session, 'current_room_id', None)
            if not current_room_id:
                return self.create_error_result("현재 위치를 확인할 수 없습니다.")

            current_room = await game_engine.world_manager.get_room(current_room_id)
            if not current_room or current_room.x is None or current_room.y is None:
                return self.create_error_result("현재 방의 좌표를 확인할 수 없습니다.")

            player_x, player_y = current_room.x, current_room.y

            locale = session.player.preferred_locale if session.player else 'en'

            if action == "list":
                # 상인 찾기 (상인 이름 지정 가능)
                merchant = await self._find_merchant(game_engine, player_x, player_y, args[1:] if len(args) > 1 else [])
                if not merchant:
                    return self.create_error_result("이 곳에는 상인이 없습니다.")
                return await self._show_shop_list(merchant, locale)
            elif action == "buy":
                if len(args) < 2:
                    return self.create_error_result("사용법: shop buy <아이템>")

                # 아이템 이름만 추출 (상인 이름은 자동으로 찾기)
                item_name = args[1]

                # 상인 찾기 (현재 위치의 모든 상인 중에서)
                merchant = await self._find_merchant(game_engine, player_x, player_y, [])
                if not merchant:
                    return self.create_error_result("이 곳에는 상인이 없습니다.")

                return await self._buy_item(session, game_engine, merchant, item_name, locale)
            else:
                return self.create_error_result("사용법: shop list 또는 shop buy <아이템>")

        except Exception as e:
            logger.error(f"상점 명령어 실행 실패: {e}", exc_info=True)
            return self.create_error_result("상점 이용 중 오류가 발생했습니다.")

    async def _find_merchant(self, game_engine, x: int, y: int, merchant_args: List[str]) -> Optional[Monster]:
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
                return self.create_error_result("이 상인은 판매할 물건이 없습니다.")

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
            message_lines.append("📦 판매 상품:")

            for i, item in enumerate(shop_items, 1):
                item_id = item.get('item_id', 'unknown')
                price = item.get('price', 0)
                currency = item.get('currency', 'gold')
                description = item.get('description', {}).get(locale, 'No description')

                # 통화 표시
                currency_symbol = "💰" if currency == "gold" else "✨" if currency == "essence_of_life" else "💎"
                currency_name = "골드" if currency == "gold" else "생명의 정수" if currency == "essence_of_life" else currency

                if price == 0:
                    price_text = "무료" if locale == "ko" else "Free"
                else:
                    price_text = f"{price} {currency_name}"

                message_lines.append(f"{i}. {item_id} - {price_text} {currency_symbol}")
                message_lines.append(f"   {description}")

            message_lines.append("")
            message_lines.append("💡 구매하려면: shop buy <아이템이름>")

            return self.create_success_result("\n".join(message_lines))

        except Exception as e:
            logger.error(f"상점 목록 표시 실패: {e}")
            return self.create_error_result("상점 목록을 불러올 수 없습니다.")

    async def _buy_item(self, session, game_engine, merchant: Monster, item_name: str, locale: str) -> CommandResult:
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
                return self.create_error_result(f"'{item_name}' 아이템을 찾을 수 없습니다.")

            item_id = target_item.get('item_id')
            price = target_item.get('price', 0)
            currency = target_item.get('currency', 'gold')
            quest_completion = target_item.get('quest_completion')

            # 퀘스트 완료 조건 확인
            if quest_completion:
                completed_quests = getattr(session.player, 'completed_quests', [])
                if quest_completion not in completed_quests:
                    if locale == "ko":
                        return self.create_error_result("이 아이템을 구매하려면 먼저 퀘스트를 완료해야 합니다.")
                    else:
                        return self.create_error_result("You must complete the quest first to purchase this item.")

            # 결제 처리
            if price > 0:
                payment_result = await self._process_payment(session, game_engine, currency, price, locale)
                if not payment_result:
                    return self.create_error_result("결제에 실패했습니다.")

            # 아이템 지급
            success = await self._give_item_to_player(session, game_engine, item_id)
            if not success:
                return self.create_error_result("아이템 지급에 실패했습니다.")

            # 성공 메시지
            currency_name = "골드" if currency == "gold" else "생명의 정수" if currency == "essence_of_life" else currency

            if price == 0:
                price_text = "무료로" if locale == "ko" else "for free"
            else:
                price_text = f"{price} {currency_name}에" if locale == "ko" else f"for {price} {currency_name}"

            # 특별한 아이템 구매 시 퀘스트 완료 처리
            if item_id == "castle_key" and quest_completion:
                await self._complete_quest(session, game_engine, quest_completion)

                if locale == "ko":
                    return self.create_success_result(f"🎉 {item_id}을(를) {price_text} 구매했습니다!\n퀘스트가 완료되었습니다!")
                else:
                    return self.create_success_result(f"🎉 Purchased {item_id} {price_text}!\nQuest completed!")

            if locale == "ko":
                return self.create_success_result(f"✅ {item_id}을(를) {price_text} 구매했습니다!")
            else:
                return self.create_success_result(f"✅ Purchased {item_id} {price_text}!")

        except Exception as e:
            logger.error(f"아이템 구매 실패: {e}")
            return self.create_error_result("구매 처리 중 오류가 발생했습니다.")

    async def _process_payment(self, session, game_engine, currency: str, amount: int, locale: str) -> bool:
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

    async def _count_player_essence(self, session, game_engine) -> int:
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

    async def _remove_player_essence(self, session, game_engine, amount: int) -> int:
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

    async def _give_item_to_player(self, session, game_engine, item_id: str) -> bool:
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

    async def _complete_quest(self, session, game_engine, quest_id: str):
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