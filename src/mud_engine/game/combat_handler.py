"""
전투 핸들러 - 전투 시작, 턴 처리, 종료 로직
"""

import logging
import random
from typing import Optional, List, Dict, Any

from .combat import (
    CombatInstance,
    CombatAction,
    CombatTurn,
    Combatant,
    CombatantType,
)
from .combat_manager import CombatManager
from .monster import Monster, MonsterType
from .models import Player, GameObject
from ..server.ansi_colors import ANSIColors
from ..core.localization import get_localization_manager
from uuid import uuid4

# D&D 전투 엔진 import
try:
    from .dnd_combat import DnDCombatEngine
except ImportError:
    from src.mud_engine.game.dnd_combat import DnDCombatEngine

logger = logging.getLogger(__name__)


class CombatHandler:
    """전투 핸들러 - 전투 로직 처리"""

    def __init__(
        self,
        combat_manager: CombatManager,
        world_manager: Any = None,
        game_engine: Any = None,
        session_manager: Any = None,
    ):
        """전투 핸들러 초기화"""
        self.combat_manager = combat_manager
        self.world_manager = world_manager
        self.game_engine = game_engine
        self.session_manager = session_manager
        self.dnd_engine = DnDCombatEngine()
        logger.info("CombatHandler 초기화 완료 (D&D 5e 룰 적용)")

    def _get_combatant_name(self, combatant, locale: str = "en") -> str:
        """전투 참가자의 언어별 이름 반환"""
        if combatant.combatant_type.value == "player":
            return combatant.name
        elif combatant.combatant_type.value == "monster":
            # 몬스터는 data에서 Monster 객체를 가져와서 언어별 이름 조회
            if combatant.data and "monster" in combatant.data:
                monster_obj = combatant.data["monster"]
                return monster_obj.get_localized_name(locale)
            return combatant.name
        else:
            return combatant.name

    async def _get_weapon_name(self, combatant, locale: str = "en") -> str:  # type: ignore[no-untyped-def]
        """전투 참가자의 무기 이름 반환 (인벤토리 장착 무기 → unarmed_attack fallback)"""
        try:
            # 플레이어/몬스터 공통: 인벤토리에서 장착 무기 조회
            entity_id = None
            if combatant.combatant_type.value == "player" and combatant.data:
                player_obj = combatant.data.get("player")
                if player_obj:
                    entity_id = player_obj.id
            elif combatant.combatant_type.value == "monster":
                entity_id = combatant.id

            if entity_id and self.world_manager:
                inventory_objects = await self.world_manager.get_inventory_objects(entity_id)
                for obj in inventory_objects:
                    if obj.is_equipped and obj.equipment_slot == "right_hand":
                        return obj.get_localized_name(locale)

            # 장착 무기 없으면 unarmed_attack 사용
            if combatant.combatant_type.value == "player" and combatant.data:
                player_obj = combatant.data.get("player")
                if player_obj and hasattr(player_obj, 'stats'):
                    # 플레이어 기본 맨손 공격
                    unarmed = {"name": {"en": "fists", "ko": "맨손"}}
                    name_dict = unarmed.get("name", {})
                    return name_dict.get(locale, name_dict.get("en", "fists"))
            elif combatant.combatant_type.value == "monster" and combatant.data:
                monster_obj = combatant.data.get("monster")
                if monster_obj:
                    unarmed = monster_obj.properties.get('unarmed_attack')
                    if unarmed:
                        name_dict = unarmed.get("name", {})
                        return name_dict.get(locale, name_dict.get("en", "claws"))

        except Exception as e:
            logger.warning(f"무기 이름 가져오기 실패: {e}")

        # 최종 fallback
        if combatant.combatant_type.value == "player":
            return "bare hands" if locale == "en" else "맨손"
        return "claws" if locale == "en" else "발톱"

    def is_monster_in_combat(self, monster_id: str) -> bool:
        """
        몬스터가 전투 중인지 확인

        Args:
            monster_id: 몬스터 ID

        Returns:
            bool: 전투 중이면 True
        """
        for combat in self.combat_manager.combat_instances.values():
            if not combat.is_active:
                continue

            # 전투 참가자 중에 해당 몬스터가 있는지 확인
            for combatant in combat.combatants:
                if combatant.id == monster_id and combatant.is_alive():
                    return True

        return False

    async def process_player_action(
        self,
        combat_id: str,
        player_id: str,
        action: CombatAction,
        target_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        플레이어 행동 처리

        Args:
            combat_id: 전투 ID
            player_id: 플레이어 ID
            action: 행동 타입
            target_id: 대상 ID (공격 시 필요)

        Returns:
            Dict: 행동 결과
        """
        combat = self.combat_manager.get_combat(combat_id)
        if not combat or not combat.is_active:
            return {
                "success": False,
                "message": "전투를 찾을 수 없거나 이미 종료되었습니다.",
            }

        # 현재 턴인지 확인
        current_combatant = combat.get_current_combatant()
        if not current_combatant or current_combatant.id != player_id:
            return {"success": False, "message": "당신의 턴이 아닙니다."}

        # 행동 처리
        result = await self._execute_action(combat, current_combatant, action, target_id)

        return result

    # 전투 참가자들에게 브로드캐스트
    async def send_broadcast_combat_message(self, combat: CombatInstance, message: str):
        for combatant in combat.get_alive_players():
            session = self.session_manager.get_player_session(combatant.id)
            if session:
                await session.send_message({"type": "combat_message", "message": message})

    async def send_broadcast_combat_message_localized(self, combat: CombatInstance, build_msg) -> None:
        """각 플레이어의 locale에 맞게 개별 메시지를 전송"""
        for combatant in combat.get_alive_players():
            session = self.session_manager.get_player_session(combatant.id)
            if session:
                player_locale = getattr(session, 'locale', 'en')
                msg = build_msg(player_locale)
                await session.send_message({"type": "combat_message", "message": msg})

    async def send_battle_command_menu(self, combat: CombatInstance):
        for combatant in combat.get_alive_players():
            if combatant.combatant_type != CombatantType.PLAYER: continue
            if combatant.id != combat.get_current_combatant().id: continue
            session = self.session_manager.get_player_session(combatant.id)
            if session:
                message = combat.get_player_turn_message(session.locale)
                await session.send_message({"type": "combat_message", "message": message})

    async def _execute_action(
        self,
        combat: CombatInstance,
        actor: Combatant,
        action: CombatAction,
        target_id: Optional[str],
    ) -> Dict[str, Any]:
        """행동 실행"""
        logger.info(f"_execute_action invoked {action}")
        if action == CombatAction.ATTACK:
            return await self._execute_attack(combat, actor, target_id)
        elif action == CombatAction.FLEE:
            return await self._execute_flee(combat, actor)
        elif action == CombatAction.ENDTURN:
            return await self._execute_endturn(combat, actor)
        else:
            return {"success": False, "message": "알 수 없는 행동입니다."}

    async def _execute_attack(self, combat: CombatInstance, actor: Combatant, target_id: Optional[str]) -> Dict[str, Any]:
        """공격 실행 (D&D 5e 룰 적용) - 메시지는 즉시 전송"""
        I18N = get_localization_manager()
        locale = "en"
        if not target_id:
            return {"success": False, "message": I18N.get_message("combat.no_target_specified", locale)}

        target = combat.get_combatant(target_id)
        if not target:
            return {"success": False, "message": I18N.get_message("combat.target_not_found", locale)}

        if not target.is_alive():
            return {"success": False, "message": I18N.get_message("combat.target_already_dead", locale)}

        _actor_is_superadmin = False
        if actor.get_display_name() == 'SUPERADMIN':
            _actor_is_superadmin = True

        # D&D 5e 룰 적용
        attack_bonus = self._calculate_attack_bonus(actor)
        attack_roll, is_critical = self.dnd_engine.make_attack_roll(attack_bonus)
        logger.info(f"attack_bonus[{attack_bonus}] attack_roll[{attack_roll}] is_critical[{is_critical}]")

        # 대상 AC 계산 (D&D 5e: 10 + DEX modifier + armor bonus)
        if target.data and "armor_class" in target.data:
            target_ac = target.data["armor_class"]
        else:
            # DEX modifier = (DEX - 10) // 2, 최소 -5
            dex_mod = (target.agility - 10) // 2
            # armor bonus = defense에서 base DEF(장비 없는 기본값)를 뺀 값
            # base DEF = 2 + int(CON * 0.3) 이므로, 장비 보너스만 armor로 취급
            armor_bonus = max(0, target.defense - 2)  # 기본 DEF 2를 빼고 장비분만
            target_ac = 10 + dex_mod + armor_bonus
            target_ac = max(1, target_ac)  # 최소 AC 1
        logger.info(f"target_ac[{target_ac}] target.defense[{target.defense}] target.agility[{target.agility}]")

        # 명중 판정
        hit = self.dnd_engine.check_hit(attack_roll, target_ac)
        logger.info(f"hit[{hit}]")

        # actor 방어 상태 해제
        actor.is_defending = False

        # 빗나감 - 참가자별 locale로 전송
        if not hit and not is_critical and not _actor_is_superadmin:
            _weapon_name_cache: Dict[str, str] = {}

            async def _get_weapon_cached(loc: str) -> str:
                if loc not in _weapon_name_cache:
                    _weapon_name_cache[loc] = await self._get_weapon_name(actor, loc)
                return _weapon_name_cache[loc]

            # 첫 호출로 캐시 채우기
            await _get_weapon_cached("en")
            await _get_weapon_cached("ko")

            def build_miss_msg(loc: str) -> str:
                a_name = self._get_combatant_name(actor, loc)
                t_name = self._get_combatant_name(target, loc)
                w_name = _weapon_name_cache.get(loc, _weapon_name_cache.get("en", ""))
                msg = f"{ANSIColors.RED}{I18N.get_message('combat.attack_swing', loc, actor=a_name, target=t_name, weapon=w_name)}\n"
                msg += f"{I18N.get_message('combat.roll_info', loc, roll=attack_roll, ac=target_ac)}\n"
                msg += f"{I18N.get_message('combat.miss', loc)}{ANSIColors.RESET}"
                return msg

            await self.send_broadcast_combat_message_localized(combat, build_miss_msg)

            return {
                "success": True, "hit": False, "damage_dealt": 0,
                "is_critical": False, "attack_roll": attack_roll,
                "target_ac": target_ac, "target_hp": target.current_hp,
                "target_max_hp": target.max_hp,
            }

        # 데미지 계산
        damage_dice = await self._get_damage_dice(actor)
        logger.info(f"damage_dice[{damage_dice}]")
        damage = self.dnd_engine.calculate_damage(damage_dice, is_critical)
        logger.info(f"damage[{damage}]")

        if target.is_defending:
            damage = damage // 2
            logger.info(f"{target.name} 방어 중 - 데미지 50% 감소")

        actual_damage = max(1, damage - target.defense)
        if _actor_is_superadmin:
            logger.warning(f"_actor_is_superadmin actual_damage[{actual_damage}] -> [{(actual_damage + 10) * 5}]")
            actual_damage = (actual_damage + 10) * 5
        target.current_hp = max(0, target.current_hp - actual_damage)
        logger.info(f"actual_damage[{actual_damage}] target.current_hp[{target.current_hp}]")

        # 공격 결과 메시지 - 참가자별 locale로 전송
        _is_defending = target.is_defending
        _weapon_name_cache2: Dict[str, str] = {}

        async def _get_weapon_cached2(loc: str) -> str:
            if loc not in _weapon_name_cache2:
                _weapon_name_cache2[loc] = await self._get_weapon_name(actor, loc)
            return _weapon_name_cache2[loc]

        await _get_weapon_cached2("en")
        await _get_weapon_cached2("ko")

        def build_hit_msg(loc: str) -> str:
            a_name = self._get_combatant_name(actor, loc)
            t_name = self._get_combatant_name(target, loc)
            w_name = _weapon_name_cache2.get(loc, _weapon_name_cache2.get("en", ""))
            msg = f"{ANSIColors.RED}{I18N.get_message('combat.attack_swing', loc, actor=a_name, target=t_name, weapon=w_name)}\n"
            msg += f"{I18N.get_message('combat.roll_info_dice', loc, dice=damage_dice, roll=attack_roll, ac=target_ac)}\n"
            if is_critical:
                msg += I18N.get_message("combat.critical_hit", loc, target=t_name, damage=actual_damage)
            else:
                msg += I18N.get_message("combat.hit", loc, target=t_name, damage=actual_damage)
            if _is_defending:
                msg += I18N.get_message("combat.defending_reduction", loc)
            msg += ANSIColors.RESET
            return msg

        await self.send_broadcast_combat_message_localized(combat, build_hit_msg)

        # 사망 처리 - 참가자별 locale로 전송
        if not target.is_alive():
            def build_death_msg(loc: str) -> str:
                t_name = self._get_combatant_name(target, loc)
                return f"{ANSIColors.RED}{I18N.get_message('combat.death', loc, name=t_name)}{ANSIColors.RESET}"

            await self.send_broadcast_combat_message_localized(combat, build_death_msg)
            await self._handle_death(combat, target)

        # player stat 저장 (메모리 + DB)
        if target.data and "player" in target.data:
            p: Player = target.data["player"]
            p.stats.set_current_hp(target.current_hp)
            await self._save_player_current_stats(p)

        return {
            "success": True, "hit": True, "damage_dealt": actual_damage,
            "is_critical": is_critical, "attack_roll": attack_roll,
            "target_ac": target_ac, "target_hp": target.current_hp,
            "target_max_hp": target.max_hp,
        }

    async def _move_inventory_to_corpse(self, entity_id: str, corpse_id: str) -> None:
        """사망자의 인벤토리 아이템을 corpse 컨테이너로 이동"""
        try:
            if not self.world_manager:
                return
            inventory = await self.world_manager.get_inventory_objects(entity_id)
            for obj in inventory:
                obj.location_type = "container"
                obj.location_id = corpse_id
                obj.is_equipped = False
                await self.world_manager._object_manager.update_game_object(obj.id, {
                    "location_type": "container",
                    "location_id": corpse_id,
                    "is_equipped": False,
                })
            if inventory:
                logger.info(f"사망자 {entity_id[-12:]}의 아이템 {len(inventory)}개를 corpse {corpse_id[-12:]}로 이동")
        except Exception as e:
            logger.error(f"인벤토리 → corpse 이동 실패 ({entity_id}): {e}")

    async def _save_player_current_stats(self, player: Player) -> None:
        """플레이어의 현재 상태값(HP 등)을 DB에 저장"""
        try:
            from .repositories import PlayerRepository
            from ..database import get_database_manager

            db_manager = await get_database_manager()
            player_repo = PlayerRepository(db_manager)
            stats_dict = player.stats.to_dict()
            await player_repo.update(player.id, {
                "stat_current": stats_dict.get("current", "{}"),
            })
        except Exception as e:
            logger.error(f"플레이어 상태 저장 실패 ({player.id}): {e}")

    async def _handle_death(self, combat: CombatInstance, dead_combatant: Combatant) -> None:
        """사망 처리 - corpse 컨테이너를 원래 방에 생성 (전투 종료 여부와 무관)"""
        I18N = get_localization_manager()
        try:
            if not self.world_manager:
                logger.warning("world_manager 없음 - corpse 생성 불가")
                return

            # 사망한 대상의 이름 결정
            name_en = dead_combatant.name
            name_ko = dead_combatant.name
            desc_en = ""
            desc_ko = ""

            if dead_combatant.combatant_type == CombatantType.MONSTER:
                if dead_combatant.data and "monster" in dead_combatant.data:
                    monster_obj: Monster = dead_combatant.data["monster"]
                    name_en = monster_obj.get_localized_name("en")
                    name_ko = monster_obj.get_localized_name("ko")
                    desc_en = I18N.get_message("combat.corpse_desc", "en", name=name_en)
                    desc_ko = I18N.get_message("combat.corpse_desc", "ko", name=name_ko)

                    # 몬스터 DB 사망 처리
                    monster = await self.world_manager.get_monster(dead_combatant.id)
                    if monster and monster.is_alive:
                        monster.die()
                        await self.world_manager.update_monster(monster)
                        logger.info(f"몬스터 {dead_combatant.id} DB 사망 처리 완료")
            else:
                # 플레이어 사망
                desc_en = I18N.get_message("combat.corpse_desc", "en", name=name_en)
                desc_ko = I18N.get_message("combat.corpse_desc", "ko", name=name_ko)

            # corpse 컨테이너 생성 - 원래 방(인스턴스 아님)에 배치
            room_id = combat.room_id
            corpse_id = str(uuid4())
            corpse_data = {
                "id": corpse_id,
                "name": {"en": I18N.get_message("combat.corpse_name", "en", name=name_en), "ko": I18N.get_message("combat.corpse_name", "ko", name=name_ko)},
                "description": {"en": desc_en, "ko": desc_ko},
                "location_type": "room",
                "location_id": room_id,
                "properties": {
                    "is_container": True,
                    "max_capacity": 20,
                    "corpse_of": dead_combatant.id,
                    "corpse_type": dead_combatant.combatant_type.value,
                },
                "weight": 10.0,
                "max_stack": 1,
            }
            await self.world_manager.create_game_object(corpse_data)
            logger.info(f"Corpse 생성 완료: {corpse_id} (room: {room_id}, target: {name_en})")

            # 사망자의 인벤토리 아이템을 corpse 컨테이너로 이동
            await self._move_inventory_to_corpse(dead_combatant.id, corpse_id)

            # 전투 참가자들에게 corpse 생성 알림
            def build_corpse_msg(loc: str) -> str:
                c_name = dead_combatant.get_display_name(loc)
                return I18N.get_message("combat.corpse_dropped", loc, name=c_name)

            await self.send_broadcast_combat_message_localized(combat, build_corpse_msg)

        except Exception as e:
            logger.error(f"사망 처리(corpse 생성) 실패: {e}", exc_info=True)

    def _calculate_attack_bonus(self, combatant: Combatant) -> int:
        """공격 보너스 계산

        D&D 5e: 숙련도 보너스 + 능력치 보정치
        combatant.data에 Monster 또는 Player 객체의 정보가 있음
        """
        # combatant.data에서 attack_bonus 가져오기
        if combatant.data and "attack_bonus" in combatant.data:
            return combatant.data["attack_bonus"]

        # 기본값: 공격력 기반 계산
        return max(1, combatant.attack_power // 5)

    async def _get_damage_dice(self, combatant: Combatant) -> str:
        """데미지 주사위 표기법 생성

        장착된 무기의 dice 속성을 사용하거나, 플레이어는 맨손(1d1), 몬스터는 공격력 기반으로 생성
        TODO: 몹도 장착 무기 기반.
        TODO: 숙련 굴림 추가 필요
        """
        # 플레이어의 경우 장착된 무기의 dice 확인
        if combatant.combatant_type.value == "player" and combatant.data:
            player_obj = combatant.data.get("player")
            if player_obj and self.world_manager:
                try:
                    # 플레이어의 장착된 무기 가져오기
                    inventory_objects = await self.world_manager.get_inventory_objects(player_obj.id)

                    # right_hand 슬롯에 장착된 무기 찾기
                    # TODO: left_hand 도
                    for obj in inventory_objects:
                        if obj.is_equipped and obj.equipment_slot == "right_hand":
                            # properties에서 dice 가져오기
                            if hasattr(obj, "properties") and obj.properties:
                                dice = obj.properties.get("dice")
                                if dice:
                                    logger.info(f"장착된 무기 dice 사용: {dice}")
                                    return dice
                except Exception as e:
                    logger.warning(f"무기 정보 가져오기 실패: {e}")

            # 플레이어인데 장착된 무기가 없으면 맨손 공격
            logger.info("장착된 무기 없음 - 맨손 공격(1d1) 사용")
            return "1d1"
        else:
            # 몬스터는 공격력 기반 계산
            # TODO: 위의 내용 반영
            base_dice = combatant.attack_power // 3  # 주사위 개수

            if base_dice <= 0:
                base_dice = 1

            # 주사위 크기 결정 (d4, d6, d8)
            if combatant.attack_power < 10:
                dice_size = 4
            elif combatant.attack_power < 20:
                dice_size = 6
            else:
                dice_size = 8

            return f"{base_dice}d{dice_size}"

    async def _execute_flee(self, combat: CombatInstance, actor: Combatant) -> Dict[str, Any]:
        """도망 실행"""
        # 도망 성공 확률 (50%)
        flee_chance = 0.5
        success = random.random() < flee_chance

        # TODO: superadmin 정보를 이렇게 가져 오면 안됨
        logger.info(f"actor.name[{actor.name}]")
        if actor.name == "SUPERADMIN":
            logger.warning("SUPERADMIN flee")
            success = True
        from ..core.localization import get_localization_manager

        localization = get_localization_manager()

        # 기본 언어는 영어로 설정 (세션 정보가 없는 경우)
        locale = "en"

        if success:
            # 전투에서 제거
            combat.remove_combatant(actor.id)

            message = localization.get_message("combat.fled_from_combat", locale, actor=actor.name)

            return {
                "success": True,
                "message": f"{ANSIColors.RED}{message}{ANSIColors.RESET}",
                "fled": True,
            }
        else:
            message = localization.get_message("combat.flee_failed", locale, actor=actor.name)

            return {
                "success": True,
                "message": f"{ANSIColors.RED}{message}{ANSIColors.RESET}",
                "fled": False,
            }

    async def _execute_endturn(self, combat:CombatInstance, actor: Combatant) -> Dict[str, Any]:
        """턴넘김"""
        # 방어 상태 해제
        actor.is_defending = False  # TODO: 방어 하고 턴넘김이 될 수 있게 되어야 함

        # from ..core.localization import get_localization_manager

        # localization = get_localization_manager()

        # 기본 언어는 영어로 설정 (세션 정보가 없는 경우)
        # locale = "en"

        # message = "" # localization.get_message("combat.wait_action", locale, actor=actor.name)

        # 턴을 종료 합니다.
        await self.send_broadcast_combat_message(combat, f"{actor.name} passed the turn.")
        combat.advance_turn()

        # 전투 참가자들에게 다음 턴 브로드캐스트
        logger.info("get_combat_status_message by process_monster_turn# 전투 참가자들에게 다음 턴 브로드캐스트")
        msg = combat.get_combat_status_message(locale="en")
        await self.send_broadcast_combat_message(combat, msg)

        return {
            "success": True,
            # "message": f"{ANSIColors.RED}{message}{ANSIColors.RESET}",
            "message": ""
        }

    async def process_monster_turn(self, combat_id: str) -> Dict[str, Any]:
        """몹 턴
        모든 몹의 턴은 3초틱 스케줄러에서 "만" 호출 된다.
        """
        logger.info(f"몹 턴 처리 시작 - combat_id: {combat_id}")

        combat = self.combat_manager.get_combat(combat_id)
        # if not combat or not combat.is_active:
        #     logger.warning(
        #         f"전투를 찾을 수 없거나 비활성 상태 - combat_id: {combat_id}"
        #     )
        #     return {
        #         "success": False,
        #         "message": "전투를 찾을 수 없거나 이미 종료되었습니다.",
        #     }

        current_combatant = combat.get_current_combatant()
        # if not current_combatant:
        #     logger.warning(f"현재 턴의 참가자를 찾을 수 없음 - combat_id: {combat_id}")
        #     return {"success": False, "message": "현재 턴의 참가자를 찾을 수 없습니다."}

        logger.info(f"몬스터 {current_combatant.name}의 턴 처리 중...")

        # 몬스터 AI: 랜덤한 플레이어 공격
        alive_players = combat.get_alive_players()
        if not alive_players:
            logger.warning(f"공격할 플레이어가 없음 - combat_id: {combat_id}")
            return {"success": False, "message": "공격할 대상이 없습니다."}

        target = random.choice(alive_players)
        logger.info(f"몬스터 {current_combatant.name}이(가) {target.name}을(를) 공격 시도")

        # 공격 실행 (_execute_attack 내부에서 즉시 broadcast됨)
        result = await self._execute_attack(combat, current_combatant, target.id)
        logger.info(f"몬스터 공격 결과: {result.get('success', False)}")

        # 다음 턴으로 진행
        combat.advance_turn()

        if combat.is_combat_over():
            return result

        # 전투 참가자들에게 다음 턴 브로드캐스트
        logger.info("get_combat_status_message by process_monster_turn# 전투 참가자들에게 다음 턴 브로드캐스트")
        msg = combat.get_combat_status_message(locale="en")
        await self.send_broadcast_combat_message(combat, msg)
        # # 전투 종료 확인
        # if combat.is_combat_over():
        #     rewards = await self._end_combat(combat)
        #     result["combat_over"] = True
        #     result["winners"] = [c.to_dict() for c in combat.get_winners()]
        #     result["rewards"] = rewards
        msg = combat.get_whos_turn(locale="en")
        await self.send_broadcast_combat_message(combat, msg)
        await self.send_battle_command_menu(combat)

        return result

    async def _end_combat(self, combat: CombatInstance) -> Dict[str, Any]:
        """
        전투 종료 처리 및 보상 지급

        Returns:
            Dict: 전투 종료 결과 (보상 정보 포함)
        """
        winners = combat.get_winners()
        rewards: Dict[str, Any] = {
            "gold": 0,
            "items": [],
            "dropped_items": [],  # 땅에 드롭된 아이템 정보
        }

        # 승리자 로그
        if winners:
            logger.info("mark")
            winner_names = [w.name for w in winners]
            logger.info(f"전투 {combat.id} 종료 - 승리자: {', '.join(winner_names)}")

            # 플레이어가 승리한 경우 보상 지급
            from .combat import CombatantType

            player_winners = [w for w in winners if w.combatant_type == CombatantType.PLAYER]

            if player_winners:
                # 처치한 몬스터들로부터 보상 계산
                all_monsters = [c for c in combat.combatants if c.combatant_type != CombatantType.PLAYER]
                defeated_monsters = [m for m in all_monsters if not m.is_alive()]

                # 각 몬스터로부터 보상 수집 (현재 보상 시스템 비활성화)
                for monster_combatant in defeated_monsters:
                    # 보상 시스템 재개발 예정 - 현재는 드롭 아이템만 처리
                    logger.debug(f"몬스터 {monster_combatant.name} 처치됨")

                logger.info(f"전투 종료 - 몬스터 {len(defeated_monsters)}마리 처치")
        else:
            logger.info(f"전투 {combat.id} 종료 - 무승부")

        # 죽은 몬스터들을 DB에 저장하고 아이템 드롭 처리
        from .combat import CombatantType

        if self.world_manager:
            for combatant in combat.combatants:
                if combatant.combatant_type != CombatantType.PLAYER and not combatant.is_alive():
                    # 몬스터가 죽었으면 DB에 저장하고 아이템 드롭
                    try:
                        monster = await self.world_manager.get_monster(combatant.id)
                        if monster:
                            # 아이템 드롭 처리 (사망 처리 전에 실행)
                            # dropped = await self._drop_monster_loot(monster, combat.room_id)
                            # if dropped:
                            #     rewards['dropped_items'].extend(dropped)
                            #     logger.info(f"몬스터 {combatant.name}이(가) {len(dropped)}개 아이템 드롭")

                            # 몬스터 사망 처리
                            if monster.is_alive:
                                monster.die()
                                await self.world_manager.update_monster(monster)
                                logger.info(f"몬스터 {combatant.name} ({combatant.id}) 사망 처리 완료")
                    except Exception as e:
                        logger.error(f"몬스터 사망 처리 실패 ({combatant.id}): {e}")

        # 전투 종료
        self.combat_manager.end_combat(combat.id)

        return rewards

    def get_combat_status(self, combat_id: str) -> Optional[Dict[str, Any]]:
        """전투 상태 조회"""
        combat = self.combat_manager.get_combat(combat_id)
        if not combat:
            return None

        return combat.to_dict()

    def get_player_combat(self, player_id: str) -> Optional[CombatInstance]:
        """
        플레이어가 참여 중인 전투 인스턴스 조회

        Args:
            player_id: 플레이어 ID

        Returns:
            CombatInstance: 전투 인스턴스 (없으면 None)
        """
        logger.info("mark")
        for combat in self.combat_manager.combat_instances.values():
            if not combat.is_active:
                continue

            # 전투 참가자 중에 해당 플레이어가 있는지 확인
            for combatant in combat.combatants:
                if combatant.id == player_id and combatant.is_alive():
                    return combat

        return None

    @property
    def active_combats(self) -> Dict[str, CombatInstance]:
        """활성 전투 목록 (호환성을 위한 속성)"""
        return {combat_id: combat for combat_id, combat in self.combat_manager.combat_instances.items() if combat.is_active}

    async def start_combat(self, player: Player, monster: Monster, room_id: str, broadcast_callback=None, aggresive=False) -> CombatInstance:
        """
        새로운 전투 시작 + 이미 전투 중인 경우 기존 CombatInstance 리턴

        Args:
            player: 플레이어 객체
            monster: 몬스터 객체
            room_id: 방 ID
            broadcast_callback: 브로드캐스트 콜백 함수
            aggresive: 선공 몹이 시작 한 경우

        Returns:
            CombatInstance: 생성된 전투 인스턴스
        """
        # 몹을 통해 이미 존재 하는 combat을 찾음
        _found = False
        logger.info("invoked start_combat")
        logger.info(monster)

        for combat in self.combat_manager.combat_instances.values():
            for combatant in combat.combatants:
                if monster.id == combatant.id and combatant.is_alive():
                    _found = True
                    break
            if _found:
                break

        if _found:
            # 플레이어가 인스턴스에 없는 경우 플레이어 추가
            for combatant in combat.combatants:
                if combatant.id == player.id:  # 꼭 찾는걸 이렇게 해야 하나
                    logger.info("found")
                    break
            else:
                logger.info("플레이어 만 추가")
                self.combat_manager.add_player_to_combat(combat.id, player, player.id)
            # 턴도 다시 결정 할 필요 없음
            return combat

        # 신규 인스턴스
        logger.info("신규 인스턴스")
        combat = self.combat_manager.create_combat(room_id)
        # 플레이어(== 나?) 추가
        logger.info("플레이어 추가")
        self.combat_manager.add_player_to_combat(combat.id, player, player.id)
        # 몬스터 추가
        logger.info("몬스터 추가")
        self.combat_manager.add_monster_to_combat(combat.id, monster)

        logger.info(f"aggresive[{aggresive}]")
        if not aggresive:
            # 일반 턴 결정
            await self.combat_manager.turn_boardcast_for_new_instance(combat)
        else:
            # 선공 몹 턴 결정
            await self.combat_manager.turn_boardcast_for_new_instance_with_aggresive_mob(combat, monster)

        logger.info(f"전투 시작[{combat.id}] {player.username} vs {monster.get_localized_name('ko')}")

        return combat

    async def add_monsters_to_combat(self, player_id: str, monsters: List[Monster]) -> bool:
        """
        기존 전투에 몬스터 추가

        Args:
            player_id: 플레이어 ID
            monsters: 추가할 몬스터 목록

        Returns:
            bool: 성공 여부
        """
        combat = self.get_player_combat(player_id)
        if not combat or not combat.is_active:
            return False

        for monster in monsters:
            self.combat_manager.add_monster_to_combat(combat.id, monster)

        logger.info(f"전투 {combat.id}에 몬스터 {len(monsters)}마리 추가")
        return True
