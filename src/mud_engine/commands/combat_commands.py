# -*- coding: utf-8 -*-
"""전투 관련 명령어들 - 턴제 전투 시스템"""

import logging
from datetime import datetime
from typing import List, Optional

from .base import BaseCommand, CommandResult, CommandResultType
from ..core.types import SessionType
from ..game.combat import CombatAction, CombatInstance
from ..game.combat_handler import CombatHandler
from ..server.ansi_colors import ANSIColors

logger = logging.getLogger(__name__)


class AttackCommand(BaseCommand):
    """공격 명령어 - 턴제 전투"""

    def __init__(self, combat_handler: CombatHandler):
        super().__init__(
            name="attack",
            aliases=["att", "kill", "fight"],
            description="몬스터를 공격합니다",
            usage="attack <몬스터명>"
        )
        self.combat_handler = combat_handler

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        if not session.is_authenticated or not session.player:
            return self.create_error_result("인증되지 않은 사용자입니다.")

        # 전투 중인 경우 - 공격 액션 실행
        if getattr(session, 'in_combat', False):
            return await self._execute_combat_attack(session)

        # 전투 시작
        if not self.validate_args(args, min_args=1):
            return self.create_error_result(
                "공격할 대상을 지정해주세요.\n사용법: attack <몬스터명>"
            )

        return await self._start_combat(session, args)

    async def _start_combat(self, session: SessionType, args: List[str]) -> CommandResult:
        """새로운 전투 시작"""
        target_input = " ".join(args)
        current_room_id = getattr(session, 'current_room_id', None)

        if not current_room_id:
            return self.create_error_result("현재 위치를 확인할 수 없습니다.")

        try:
            game_engine = getattr(session, 'game_engine', None)
            if not game_engine:
                return self.create_error_result("게임 엔진에 접근할 수 없습니다.")

            # 번호로 입력된 경우 처리
            target_monster = None
            if target_input.isdigit():
                entity_num = int(target_input)
                entity_map = getattr(session, 'room_entity_map', {})
                
                if entity_num in entity_map:
                    entity_info = entity_map[entity_num]
                    if entity_info['type'] == 'monster':
                        target_monster = entity_info['entity']
                    else:
                        return self.create_error_result(
                            f"[{entity_num}]은(는) 몬스터가 아닙니다."
                        )
                else:
                    return self.create_error_result(
                        f"번호 [{entity_num}]에 해당하는 대상을 찾을 수 없습니다."
                    )
            else:
                # 이름으로 검색
                target_name = target_input.lower()
                monsters = await game_engine.world_manager.get_monsters_in_room(current_room_id)

                for monster in monsters:
                    if not monster.is_alive:
                        continue

                    monster_name_ko = monster.get_localized_name('ko').lower()
                    monster_name_en = monster.get_localized_name('en').lower()

                    if target_name in monster_name_ko or target_name in monster_name_en:
                        target_monster = monster
                        break

            if not target_monster:
                return self.create_error_result(
                    f"'{target_input}'라는 몬스터를 찾을 수 없습니다."
                )

            # 전투 인스턴스 생성
            combat = await self.combat_handler.start_combat(
                session.player,
                target_monster,
                current_room_id
            )

            # 세션 상태 업데이트
            session.in_combat = True
            session.original_room_id = current_room_id
            session.combat_id = combat.id
            session.current_room_id = f"combat_{combat.id}"  # 전투 인스턴스로 이동

            monster_name = target_monster.get_localized_name('ko')
            
            # 몬스터가 선공이면 자동으로 턴 처리
            current = combat.get_current_combatant()
            from ..game.combat import CombatantType
            if current and current.combatant_type == CombatantType.MONSTER:
                logger.info(f"몬스터 선공 - 자동 턴 처리 시작")
                await self._process_monster_turns(combat)
                
                # 전투 종료 확인
                if combat.is_combat_over():
                    return await self._end_combat(session, combat, {})
            
            # 전투 시작 메시지 (몬스터 턴 처리 후)
            from ..core.localization import get_localization_manager
            localization = get_localization_manager()
            locale = session.player.preferred_locale if session.player else "en"
            
            start_message = f"""
{ANSIColors.RED}{localization.get_message("combat.start", locale, monster=monster_name)}{ANSIColors.RESET}

{self._get_combat_status_message(combat, locale)}

{self._get_turn_message(combat, session.player.id, locale)}
"""

            return self.create_success_result(
                message=start_message.strip(),
                data={
                    "action": "combat_start",
                    "combat_id": combat.id,
                    "combat_status": combat.to_dict()
                }
            )

        except Exception as e:
            logger.error(f"전투 시작 중 오류: {e}", exc_info=True)
            return self.create_error_result("전투 시작 중 오류가 발생했습니다.")

    async def _execute_combat_attack(self, session: SessionType) -> CommandResult:
        """전투 중 공격 액션 실행"""
        combat_id = getattr(session, 'combat_id', None)
        if not combat_id:
            return self.create_error_result("전투 정보를 찾을 수 없습니다.")

        combat = self.combat_handler.combat_manager.get_combat(combat_id)
        if not combat or not combat.is_active:
            return self.create_error_result("전투를 찾을 수 없거나 이미 종료되었습니다.")

        # 현재 턴 확인
        current_combatant = combat.get_current_combatant()
        if not current_combatant or current_combatant.id != session.player.id:
            return self.create_error_result("당신의 턴이 아닙니다.")

        # 공격 대상 선택 (첫 번째 생존 몬스터)
        alive_monsters = combat.get_alive_monsters()
        if not alive_monsters:
            return self.create_error_result("공격할 몬스터가 없습니다.")

        target = alive_monsters[0]

        # 공격 실행
        result = await self.combat_handler.process_player_action(
            combat_id,
            session.player.id,
            CombatAction.ATTACK,
            target.id
        )

        if not result.get('success'):
            return self.create_error_result(result.get('message', '공격 실패'))

        # 전투 종료 확인
        if result.get('combat_over'):
            return await self._end_combat(session, combat, result)

        # 몬스터 턴 자동 처리
        monster_messages = []
        while combat.is_active and not combat.is_combat_over():
            current = combat.get_current_combatant()
            if not current:
                break

            # 플레이어 턴이면 중단
            from ..game.combat import CombatantType
            if current.combatant_type == CombatantType.PLAYER:
                break

            # 몬스터 턴 처리
            monster_result = await self.combat_handler.process_monster_turn(combat.id)
            if monster_result.get('success') and monster_result.get('message'):
                monster_messages.append(monster_result['message'])
            
            # 전투 종료 확인
            if monster_result.get('combat_over'):
                return await self._end_combat(session, combat, monster_result)

        # 전투 종료 재확인
        if combat.is_combat_over():
            result_end = await self._end_combat(session, combat, {})
            return result_end

        # 다음 턴 메시지
        locale = session.player.preferred_locale if session.player else "ko"
        message = f"{result.get('message', '')}\n"
        
        # 몬스터 턴 메시지 추가
        if monster_messages:
            message += "\n" + "\n".join(monster_messages) + "\n"
        
        message += "\n" + self._get_combat_status_message(combat, locale)
        message += "\n\n"
        message += self._get_turn_message(combat, session.player.id, locale)

        return self.create_success_result(
            message=message,
            data={
                "action": "combat_action_result",
                "combat_status": combat.to_dict()
            }
        )

    async def _process_monster_turns(self, combat: CombatInstance) -> None:
        """몬스터 턴들을 자동으로 처리"""
        while combat.is_active and not combat.is_combat_over():
            current = combat.get_current_combatant()
            if not current:
                break

            # 플레이어 턴이면 중단
            from ..game.combat import CombatantType
            if current.combatant_type == CombatantType.PLAYER:
                break

            # 몬스터 턴 처리
            await self.combat_handler.process_monster_turn(combat.id)

    async def _end_combat(
        self,
        session: SessionType,
        combat: CombatInstance,
        result: dict
    ) -> CommandResult:
        """전투 종료 처리"""
        winners = combat.get_winners()
        rewards = result.get('rewards', {'experience': 0, 'gold': 0, 'items': [], 'dropped_items': []})

        # 승리/패배 메시지
        from ..game.combat import CombatantType
        from ..core.localization import get_localization_manager
        localization = get_localization_manager()
        locale = session.player.preferred_locale if session.player else "en"
        
        player_won = any(w.combatant_type == CombatantType.PLAYER for w in winners)

        if player_won:
            # 보상 지급
            game_engine = getattr(session, 'game_engine', None)
            
            # 골드 지급
            if rewards['gold'] > 0:
                session.player.earn_gold(rewards['gold'])
                logger.info(f"플레이어 {session.player.username}이(가) 골드 {rewards['gold']} 획득")
            
            # 플레이어 정보는 세션에 저장되어 있으므로 별도 DB 업데이트 불필요
            # (세션 종료 시 자동으로 저장됨)
            
            # 드롭된 아이템 처리
            dropped_items_msg = []
            if rewards.get('dropped_items'):
                from ..game.item_templates import ItemTemplateManager
                item_manager = ItemTemplateManager()
                
                for drop_info in rewards['dropped_items']:
                    if drop_info.get('location') == 'inventory':
                        # 플레이어 인벤토리에 직접 추가
                        template_id = drop_info.get('template_id')
                        if template_id and game_engine:
                            item_data = item_manager.create_item(
                                template_id=template_id,
                                location_type="inventory",
                                location_id=session.player.id,
                                quantity=drop_info.get('quantity', 1)
                            )
                            if item_data:
                                await game_engine.world_manager.create_game_object(item_data)
                                item_name = drop_info.get(f'name_{locale}', drop_info.get('name_ko', 'Unknown Item'))
                                dropped_items_msg.append(
                                    localization.get_message("combat.item_inventory", locale, 
                                                           name=item_name, 
                                                           quantity=drop_info.get('quantity', 1))
                                )
                                logger.info(
                                    f"플레이어 {session.player.username}이(가) "
                                    f"{drop_info['name_ko']} {drop_info.get('quantity', 1)}개 획득"
                                )
                            else:
                                # 템플릿이 없어서 아이템 생성 실패
                                item_name = drop_info.get(f'name_{locale}', drop_info.get('name_ko', 'Unknown Item'))
                                await session.send_message({
                                    "type": "room_message",
                                    "message": localization.get_message("item.disappeared", locale, item=item_name)
                                })
                                logger.error(f"아이템 드롭 실패 - 템플릿 없음: {template_id}")
                    elif drop_info.get('location') == 'ground':
                        # 땅에 떨어진 아이템
                        item_name = drop_info.get(f'name_{locale}', drop_info.get('name_ko', 'Unknown Item'))
                        dropped_items_msg.append(
                            localization.get_message("combat.item_ground", locale, 
                                                    name=item_name, 
                                                    quantity=drop_info.get('quantity', 1))
                        )
            
            # 승리 메시지 생성
            
            message = f"""
{ANSIColors.RED}{localization.get_message("combat.victory_message", locale)}{ANSIColors.RESET}

{localization.get_message("combat.rewards_header", locale)}
{localization.get_message("combat.gold_reward", locale, gold=rewards['gold'])}"""
            
            if dropped_items_msg:
                message += f"\n\n{localization.get_message('combat.items_obtained', locale)}\n" + "\n".join(dropped_items_msg)
            
            message += f"\n\n{localization.get_message('combat.returning_location', locale)}"
        else:
            message = f"{ANSIColors.RED}{localization.get_message('combat.defeat_message', locale)}{ANSIColors.RESET}\n\n{localization.get_message('combat.returning_location', locale)}"

        # 원래 방으로 복귀
        original_room_id = getattr(session, 'original_room_id', None)
        if original_room_id:
            session.current_room_id = original_room_id

        # 전투 상태 초기화
        session.in_combat = False
        session.original_room_id = None
        session.combat_id = None

        # 전투 종료
        self.combat_handler.combat_manager.end_combat(combat.id)

        return self.create_success_result(
            message=message.strip(),
            data={
                "action": "combat_end",
                "victory": player_won,
                "rewards": rewards
            }
        )

    def _get_combat_status_message(self, combat: CombatInstance, locale: str = "ko") -> str:
        """전투 상태 메시지 생성"""
        from ..core.localization import get_localization_manager
        localization = get_localization_manager()
        
        lines = [f"{ANSIColors.RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"]
        lines.append(localization.get_message("combat.round", locale, round=combat.turn_number))
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        # 플레이어 정보
        players = combat.get_alive_players()
        if players:
            player = players[0]
            hp_bar = self._get_hp_bar(player.current_hp, player.max_hp)
            lines.append(f"\n{localization.get_message('combat.player_hp', locale, name=player.name)}")
            lines.append(f"   HP: {hp_bar} {player.current_hp}/{player.max_hp}")

        # 몬스터 정보
        monsters = combat.get_alive_monsters()
        if monsters:
            lines.append(f"\n{localization.get_message('combat.monsters', locale)}")
            for monster in monsters:
                hp_bar = self._get_hp_bar(monster.current_hp, monster.max_hp)
                lines.append(localization.get_message("combat.monster_entry", locale, name=monster.name))
                lines.append(localization.get_message("combat.hp_display", locale, 
                                                    hp_bar=hp_bar, 
                                                    current=monster.current_hp, 
                                                    max=monster.max_hp))

        lines.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{ANSIColors.RESET}")
        return "\n".join(lines)

    def _get_turn_message(self, combat: CombatInstance, player_id: str, locale: str = "en") -> str:
        """턴 메시지 생성"""
        from ..core.localization import get_localization_manager
        localization = get_localization_manager()
        
        current = combat.get_current_combatant()
        if not current:
            return ""

        if current.id == player_id:
            return f"""
{localization.get_message("combat.your_turn", locale)}

1️⃣ {localization.get_message("combat.action_attack", locale)}
2️⃣ {localization.get_message("combat.action_defend", locale)}
3️⃣ {localization.get_message("combat.action_flee", locale)}

{localization.get_message("combat.enter_command", locale)}"""
        else:
            if locale == "ko":
                return f"{ANSIColors.RED}⏳ {current.name}의 턴입니다...{ANSIColors.RESET}"
            else:
                return f"{ANSIColors.RED}⏳ {current.name}'s turn...{ANSIColors.RESET}"

    def _get_hp_bar(self, current: int, maximum: int, length: int = 10) -> str:
        """HP 바 생성"""
        if maximum <= 0:
            return "[" + "░" * length + "]"

        filled = int((current / maximum) * length)
        empty = length - filled

        return "[" + "█" * filled + "░" * empty + "]"


class DefendCommand(BaseCommand):
    """방어 명령어"""

    def __init__(self, combat_handler: CombatHandler):
        super().__init__(
            name="defend",
            aliases=["def", "guard", "block"],
            description="방어 자세를 취합니다",
            usage="defend"
        )
        self.combat_handler = combat_handler

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        if not session.is_authenticated or not session.player:
            return self.create_error_result("인증되지 않은 사용자입니다.")

        if not getattr(session, 'in_combat', False):
            return self.create_error_result("전투 중이 아닙니다.")

        combat_id = getattr(session, 'combat_id', None)
        if not combat_id:
            return self.create_error_result("전투 정보를 찾을 수 없습니다.")

        combat = self.combat_handler.combat_manager.get_combat(combat_id)
        if not combat or not combat.is_active:
            return self.create_error_result("전투를 찾을 수 없거나 이미 종료되었습니다.")

        # 현재 턴 확인
        current_combatant = combat.get_current_combatant()
        if not current_combatant or current_combatant.id != session.player.id:
            return self.create_error_result("당신의 턴이 아닙니다.")

        # 방어 실행
        result = await self.combat_handler.process_player_action(
            combat_id,
            session.player.id,
            CombatAction.DEFEND,
            None
        )

        if not result.get('success'):
            return self.create_error_result(result.get('message', '방어 실패'))

        # 전투 종료 확인
        if result.get('combat_over'):
            return await self._end_combat(session, combat, result)

        # 몬스터 턴 자동 처리
        monster_messages = []
        while combat.is_active and not combat.is_combat_over():
            current = combat.get_current_combatant()
            if not current:
                break

            # 플레이어 턴이면 중단
            from ..game.combat import CombatantType
            if current.combatant_type == CombatantType.PLAYER:
                break

            # 몬스터 턴 처리
            monster_result = await self.combat_handler.process_monster_turn(combat.id)
            if monster_result.get('success') and monster_result.get('message'):
                monster_messages.append(monster_result['message'])
            
            # 전투 종료 확인
            if monster_result.get('combat_over'):
                return await self._end_combat(session, combat, monster_result)

        # 전투 종료 재확인
        if combat.is_combat_over():
            return await self._end_combat(session, combat, {})

        # 다음 턴 메시지
        attack_cmd = AttackCommand(self.combat_handler)
        locale = session.player.preferred_locale if session.player else "ko"
        message = f"{result.get('message', '')}\n"
        
        # 몬스터 턴 메시지 추가
        if monster_messages:
            message += "\n" + "\n".join(monster_messages) + "\n"
        
        message += "\n" + attack_cmd._get_combat_status_message(combat, locale)
        message += "\n\n"
        message += attack_cmd._get_turn_message(combat, session.player.id, locale)

        return self.create_success_result(
            message=message,
            data={
                "action": "combat_action_result",
                "combat_status": combat.to_dict()
            }
        )

    async def _process_monster_turns(self, combat):
        """몬스터 턴 처리"""
        attack_cmd = AttackCommand(self.combat_handler)
        await attack_cmd._process_monster_turns(combat)

    async def _end_combat(self, session, combat, result):
        """전투 종료"""
        attack_cmd = AttackCommand(self.combat_handler)
        return await attack_cmd._end_combat(session, combat, result)


class FleeCommand(BaseCommand):
    """도망 명령어"""

    def __init__(self, combat_handler: CombatHandler):
        super().__init__(
            name="flee",
            aliases=["run", "escape", "retreat"],
            description="전투에서 도망칩니다",
            usage="flee"
        )
        self.combat_handler = combat_handler

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        if not session.is_authenticated or not session.player:
            return self.create_error_result("인증되지 않은 사용자입니다.")

        if not getattr(session, 'in_combat', False):
            return self.create_error_result("전투 중이 아닙니다.")

        combat_id = getattr(session, 'combat_id', None)
        if not combat_id:
            return self.create_error_result("전투 정보를 찾을 수 없습니다.")

        combat = self.combat_handler.combat_manager.get_combat(combat_id)
        if not combat or not combat.is_active:
            return self.create_error_result("전투를 찾을 수 없거나 이미 종료되었습니다.")

        # 현재 턴 확인
        current_combatant = combat.get_current_combatant()
        if not current_combatant or current_combatant.id != session.player.id:
            return self.create_error_result("당신의 턴이 아닙니다.")

        # 도망 실행
        result = await self.combat_handler.process_player_action(
            combat_id,
            session.player.id,
            CombatAction.FLEE,
            None
        )

        if not result.get('success'):
            return self.create_error_result(result.get('message', '도망 실패'))

        # 도망 성공 여부 확인
        if result.get('fled'):
            # 원래 방 정보 가져오기
            original_room_id = getattr(session, 'original_room_id', None)
            if not original_room_id:
                return self.create_error_result("원래 위치를 찾을 수 없습니다.")
            
            try:
                game_engine = getattr(session, 'game_engine', None)
                if not game_engine:
                    return self.create_error_result("게임 엔진에 접근할 수 없습니다.")
                
                # 원래 방의 출구 정보 가져오기
                original_room = await game_engine.world_manager.get_room(original_room_id)
                if not original_room:
                    return self.create_error_result("원래 방을 찾을 수 없습니다.")
                
                # 출구가 있는지 확인
                import json
                exits = original_room.exits
                if isinstance(exits, str):
                    exits = json.loads(exits)
                
                from ..core.localization import get_localization_manager
                localization = get_localization_manager()
                locale = session.player.preferred_locale if session.player else "en"
                
                if not exits or len(exits) == 0:
                    # 출구가 없으면 원래 방으로 복귀
                    session.current_room_id = original_room_id
                    flee_message = f"{localization.get_message('combat.flee_success', locale)}\n\n{localization.get_message('combat.return_location', locale)}"
                else:
                    # 랜덤 출구 선택
                    import random
                    exit_directions = list(exits.keys())
                    random_direction = random.choice(exit_directions)
                    target_room_id = exits[random_direction]
                    
                    # 대상 방이 존재하는지 확인
                    target_room = await game_engine.world_manager.get_room(target_room_id)
                    if target_room:
                        session.current_room_id = target_room_id
                        flee_message = f"{localization.get_message('combat.flee_success', locale)}\n\n{random_direction} 방향으로 도망쳐 {target_room.get_localized_name(locale)}에 도착했습니다."
                    else:
                        # 대상 방이 없으면 원래 방으로
                        session.current_room_id = original_room_id
                        flee_message = f"{localization.get_message('combat.flee_success', locale)}\n\n{localization.get_message('combat.return_location', locale)}"
                
                # 전투 상태 초기화
                session.in_combat = False
                session.original_room_id = None
                session.combat_id = None
                
                # 전투 인스턴스 종료
                self.combat_handler.combat_manager.end_combat(combat_id)
                logger.info(f"플레이어 {session.player.username} 도망 성공 - 전투 {combat_id} 종료, 이동: {session.current_room_id}")

                return self.create_success_result(
                    message=flee_message,
                    data={"action": "flee_success", "new_room_id": session.current_room_id}
                )
                
            except Exception as e:
                logger.error(f"도망 처리 중 오류: {e}", exc_info=True)
                # 오류 발생 시 원래 방으로 복귀
                session.current_room_id = original_room_id
                session.in_combat = False
                session.original_room_id = None
                session.combat_id = None
                self.combat_handler.combat_manager.end_combat(combat_id)
                
                from ..core.localization import get_localization_manager
                localization = get_localization_manager()
                locale = session.player.preferred_locale if session.player else "en"
                
                return self.create_success_result(
                    message=f"{localization.get_message('combat.flee_success', locale)}\n\n{localization.get_message('combat.return_location', locale)}",
                    data={"action": "flee_success"}
                )

        # 도망 실패 - 몬스터 턴 처리
        monster_messages = []
        while combat.is_active and not combat.is_combat_over():
            current = combat.get_current_combatant()
            if not current:
                break

            # 플레이어 턴이면 중단
            from ..game.combat import CombatantType
            if current.combatant_type == CombatantType.PLAYER:
                break

            # 몬스터 턴 처리
            monster_result = await self.combat_handler.process_monster_turn(combat.id)
            if monster_result.get('success') and monster_result.get('message'):
                monster_messages.append(monster_result['message'])
            
            # 전투 종료 확인
            if monster_result.get('combat_over'):
                return await self._end_combat(session, combat, monster_result)

        # 전투 종료 확인
        if combat.is_combat_over():
            return await self._end_combat(session, combat, {})

        # 다음 턴 메시지
        attack_cmd = AttackCommand(self.combat_handler)
        locale = session.player.preferred_locale if session.player else "ko"
        message = f"{result.get('message', '')}\n"
        
        # 몬스터 턴 메시지 추가
        if monster_messages:
            message += "\n" + "\n".join(monster_messages) + "\n"
        
        message += "\n" + attack_cmd._get_combat_status_message(combat, locale)
        message += "\n\n"
        message += attack_cmd._get_turn_message(combat, session.player.id, locale)

        return self.create_success_result(
            message=message,
            data={
                "action": "combat_action_result",
                "combat_status": combat.to_dict()
            }
        )

    async def _process_monster_turns(self, combat):
        """몬스터 턴 처리"""
        attack_cmd = AttackCommand(self.combat_handler)
        await attack_cmd._process_monster_turns(combat)

    async def _end_combat(self, session, combat, result):
        """전투 종료"""
        attack_cmd = AttackCommand(self.combat_handler)
        return await attack_cmd._end_combat(session, combat, result)


class CombatStatusCommand(BaseCommand):
    """전투 상태 확인 명령어"""

    def __init__(self, combat_handler: CombatHandler):
        super().__init__(
            name="combat",
            aliases=["battle", "fight_status", "cs"],
            description="현재 전투 상태를 확인합니다",
            usage="combat"
        )
        self.combat_handler = combat_handler

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        if not session.is_authenticated or not session.player:
            return self.create_error_result("인증되지 않은 사용자입니다.")

        if not getattr(session, 'in_combat', False):
            return self.create_info_result("현재 전투 중이 아닙니다.")

        combat_id = getattr(session, 'combat_id', None)
        if not combat_id:
            return self.create_error_result("전투 정보를 찾을 수 없습니다.")

        combat = self.combat_handler.combat_manager.get_combat(combat_id)
        if not combat:
            return self.create_error_result("전투를 찾을 수 없습니다.")

        attack_cmd = AttackCommand(self.combat_handler)
        locale = session.player.preferred_locale if session.player else "ko"
        message = attack_cmd._get_combat_status_message(combat, locale)
        message += "\n\n"
        message += attack_cmd._get_turn_message(combat, session.player.id, locale)

        return self.create_success_result(
            message=message,
            data={
                "action": "combat_status",
                "combat_status": combat.to_dict()
            }
        )
