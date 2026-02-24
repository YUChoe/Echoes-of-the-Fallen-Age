"""
전투 핸들러 - 전투 시작, 턴 처리, 종료 로직
"""

import logging
import random
from typing import Optional, List, Dict, Any

from .combat import CombatManager, CombatInstance, CombatAction, CombatTurn, Combatant, CombatantType
from .monster import Monster, MonsterType
from .models import Player
from ..server.ansi_colors import ANSIColors

# D&D 전투 엔진 import
try:
    from .dnd_combat import DnDCombatEngine
except ImportError:
    from src.mud_engine.game.dnd_combat import DnDCombatEngine

logger = logging.getLogger(__name__)


class CombatHandler:
    """전투 핸들러 - 전투 로직 처리"""

    def __init__(self, combat_manager: CombatManager, world_manager: Any = None, game_engine: Any = None, session_manager: Any = None):
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

    def _get_weapon_name(self, combatant, locale: str = "ko") -> str:
        """전투 참가자의 무기 이름 반환"""
        if combatant.combatant_type.value == "player":
            # 플레이어의 경우 장착된 무기 확인
            # 사용자가 곤봉을 들고 있다고 했으므로 곤봉으로 설정
            return "곤봉" if locale == "ko" else "club"
        elif combatant.combatant_type.value == "monster":
            # 몬스터의 경우 종류에 따라 다른 무기
            if combatant.data and "monster" in combatant.data:
                monster_obj = combatant.data["monster"]
                monster_name = monster_obj.get_localized_name(locale).lower()

                # 몬스터 종류별 무기 설정
                if "쥐" in monster_name or "rat" in monster_name:
                    return "날카로운 이빨" if locale == "ko" else "sharp teeth"
                elif "고블린" in monster_name or "goblin" in monster_name:
                    return "곤봉" if locale == "ko" else "club"
                elif "경비병" in monster_name or "guard" in monster_name:
                    return "검" if locale == "ko" else "sword"
                else:
                    return "발톱" if locale == "ko" else "claws"
            return "발톱" if locale == "ko" else "claws"
        else:
            return "무기" if locale == "ko" else "weapon"

    async def check_and_start_combat(
        self, room_id: str, player: Player, player_id: str, monsters: List[Monster]
    ) -> Optional[CombatInstance]:
        """
        방에 공격적인 몬스터가 있으면 전투 시작

        Args:
            room_id: 방 ID
            player: 플레이어 객체
            player_id: 플레이어 ID
            monsters: 방에 있는 몬스터 목록

        Returns:
            CombatInstance: 생성된 전투 인스턴스 (전투가 시작되지 않으면 None)
        """
        # 이미 전투 중인지 확인
        if self.combat_manager.is_player_in_combat(player_id):
            logger.info(f"플레이어 {player_id}는 이미 전투 중")
            return None

        # 공격적인 몬스터 찾기 (전투 중이 아닌 몬스터만)
        aggressive_monsters = [
            m
            for m in monsters
            if m.is_aggressive() and m.is_alive and not self.is_monster_in_combat(m.id)
        ]

        if not aggressive_monsters:
            logger.debug(f"방 {room_id}에 공격 가능한 선공형 몬스터 없음")
            return None

        # 이미 방에 전투가 있는지 확인
        existing_combat = self.combat_manager.get_combat_by_room(room_id)

        if existing_combat and existing_combat.is_active:
            # 기존 전투에 플레이어 추가
            success = self.combat_manager.add_player_to_combat(
                existing_combat.id, player, player_id
            )
            if success:
                logger.info(
                    f"플레이어 {player_id}를 기존 전투 {existing_combat.id}에 추가"
                )
                return existing_combat
            return None

        # 새로운 전투 인스턴스 생성
        combat = self.combat_manager.create_combat(room_id)

        # 플레이어 추가
        self.combat_manager.add_player_to_combat(combat.id, player, player_id)

        # 공격적인 몬스터들 추가
        for monster in aggressive_monsters:
            self.combat_manager.add_monster_to_combat(combat.id, monster)

        logger.info(
            f"전투 시작: 방 {room_id}, "
            f"플레이어 {player_id}, "
            f"몬스터 {len(aggressive_monsters)}마리"
        )

        return combat

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
        result = await self._execute_action(
            combat, current_combatant, action, target_id
        )

        # 턴 로그 추가
        turn = CombatTurn(
            turn_number=combat.turn_number,
            combatant_id=player_id,
            action=action,
            target_id=target_id,
            damage_dealt=result.get("damage_dealt", 0),
            damage_received=result.get("damage_received", 0),
            message=result.get("message", ""),
        )
        combat.add_combat_log(turn)

        # 다음 턴으로 진행
        combat.advance_turn()

        # 전투 종료 확인은 combat_commands.py에서만 처리
        # 여기서는 공격 결과만 반환

        return result

    async def _execute_action(
        self,
        combat: CombatInstance,
        actor: Combatant,
        action: CombatAction,
        target_id: Optional[str],
    ) -> Dict[str, Any]:
        """행동 실행"""
        if action == CombatAction.ATTACK:
            return await self._execute_attack(combat, actor, target_id)
        elif action == CombatAction.DEFEND:
            return await self._execute_defend(actor)
        elif action == CombatAction.FLEE:
            return await self._execute_flee(combat, actor)
        elif action == CombatAction.WAIT:
            return await self._execute_wait(actor)
        else:
            return {"success": False, "message": "알 수 없는 행동입니다."}

    async def _execute_attack(
        self, combat: CombatInstance, actor: Combatant, target_id: Optional[str]
    ) -> Dict[str, Any]:
        """공격 실행 (D&D 5e 룰 적용)"""
        if not target_id:
            return {"success": False, "message": "공격 대상을 지정해야 합니다."}

        target = combat.get_combatant(target_id)
        if not target:
            return {"success": False, "message": "대상을 찾을 수 없습니다."}

        if not target.is_alive():
            return {"success": False, "message": "이미 사망한 대상입니다."}

        # D&D 5e 룰 적용
        # 1. 공격 굴림 (d20 + 공격 보너스)
        attack_bonus = self._calculate_attack_bonus(actor)
        attack_roll, is_critical = self.dnd_engine.make_attack_roll(attack_bonus)

        # 2. 대상 AC (방어도) 계산
        # target.data에서 armor_class 가져오기
        if target.data and "armor_class" in target.data:
            target_ac = target.data["armor_class"]
        else:
            target_ac = 10 + target.defense  # 기본 AC 10 + 방어력

        # 3. 명중 판정
        hit = self.dnd_engine.check_hit(attack_roll, target_ac)

        # 방어 상태 해제
        actor.is_defending = False

        # 빗나감
        if not hit and not is_critical:
            # 기본 언어는 영어로 설정 (추후 세션 정보에서 가져올 수 있도록 개선 필요)
            locale = "ko"
            actor_name = self._get_combatant_name(actor, locale)
            target_name = self._get_combatant_name(target, locale)

            # 무기 정보 가져오기
            weapon_name = self._get_weapon_name(actor, locale)

            message = f"{ANSIColors.RED}{actor_name}이(가) {weapon_name}(으)로 {target_name}을(를) 공격합니다!\n"
            message += f"🎲 공격 굴림: {attack_roll} vs AC {target_ac}\n"
            message += f"❌ 공격이 빗나갔습니다!{ANSIColors.RESET}"

            return {
                "success": True,
                "message": message,
                "damage_dealt": 0,
                "is_critical": False,
                "hit": False,
                "attack_roll": attack_roll,
                "target_ac": target_ac,
                "target_hp": target.current_hp,
                "target_max_hp": target.max_hp,
            }

        # 4. 데미지 계산
        # 데미지 주사위 표기법 생성 (예: "1d8+2")
        damage_dice = self._get_damage_dice(actor)
        damage = self.dnd_engine.calculate_damage(damage_dice, is_critical)

        # 5. 방어 중이면 데미지 50% 감소
        if target.is_defending:
            damage = damage // 2
            logger.info(f"{target.name} 방어 중 - 데미지 50% 감소")

        # 6. 대상에게 데미지 적용 (방어력 적용)
        actual_damage = max(1, damage - target.defense)
        target.current_hp = max(0, target.current_hp - actual_damage)

        # 메시지 생성
        locale = "ko"  # 한국어로 설정
        actor_name = self._get_combatant_name(actor, locale)
        target_name = self._get_combatant_name(target, locale)

        # 무기 정보 가져오기
        weapon_name = self._get_weapon_name(actor, locale)

        message = f"{ANSIColors.RED}{actor_name}이(가) {weapon_name}(으)로 {target_name}을(를) 공격합니다!\n"
        message += f"🎲 공격 굴림: {attack_roll} vs AC {target_ac}\n"

        if is_critical:
            message += f"💥 크리티컬 히트! {target_name}에게 {actual_damage} 데미지를 입혔습니다!"
        else:
            message += (
                f"✅ 명중! {target_name}에게 {actual_damage} 데미지를 입혔습니다!"
            )

        if target.is_defending:
            message += " (방어 중 - 50% 감소)"

        if not target.is_alive():
            message += f"\n💀 {target_name}이(가) 죽었습니다!"

        message += ANSIColors.RESET

        # TODO: 실제 player stat 에 저장 되어야 함
        if target.data and "player" in target.data:
            p: Player = target.data["player"]
            p.stats.set_current_hp(target.current_hp)
        # ===== ===== ===== =====
        return {
            "success": True,
            "message": message,
            "damage_dealt": actual_damage,
            "is_critical": is_critical,
            "hit": True,
            "attack_roll": attack_roll,
            "target_ac": target_ac,
            "target_hp": target.current_hp,
            "target_max_hp": target.max_hp,
        }

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

    def _get_damage_dice(self, combatant: Combatant) -> str:
        """데미지 주사위 표기법 생성

        공격력 기반으로 주사위 표기법 생성
        예: 공격력 8 -> "1d6+2"
        """
        base_dice = combatant.attack_power // 3  # 주사위 개수
        bonus = combatant.attack_power % 3  # 보너스

        if base_dice <= 0:
            base_dice = 1

        # 주사위 크기 결정 (d4, d6, d8)
        if combatant.attack_power < 5:
            dice_size = 4
        elif combatant.attack_power < 10:
            dice_size = 6
        else:
            dice_size = 8

        if bonus > 0:
            return f"{base_dice}d{dice_size}+{bonus}"
        else:
            return f"{base_dice}d{dice_size}"

    async def _execute_defend(self, actor: Combatant) -> Dict[str, Any]:
        """방어 실행"""
        actor.is_defending = True

        from ..core.localization import get_localization_manager

        localization = get_localization_manager()

        # 기본 언어는 영어로 설정 (세션 정보가 없는 경우)
        locale = "en"

        message = localization.get_message(
            "combat.defend_stance", locale, actor=actor.name
        )

        return {
            "success": True,
            "message": f"{ANSIColors.RED}{message}{ANSIColors.RESET}",
        }

    async def _execute_flee(
        self, combat: CombatInstance, actor: Combatant
    ) -> Dict[str, Any]:
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

            message = localization.get_message(
                "combat.fled_from_combat", locale, actor=actor.name
            )

            return {
                "success": True,
                "message": f"{ANSIColors.RED}{message}{ANSIColors.RESET}",
                "fled": True,
            }
        else:
            message = localization.get_message(
                "combat.flee_failed", locale, actor=actor.name
            )

            return {
                "success": True,
                "message": f"{ANSIColors.RED}{message}{ANSIColors.RESET}",
                "fled": False,
            }

    async def _execute_wait(self, actor: Combatant) -> Dict[str, Any]:
        """대기 실행"""
        # 방어 상태 해제
        actor.is_defending = False

        from ..core.localization import get_localization_manager

        localization = get_localization_manager()

        # 기본 언어는 영어로 설정 (세션 정보가 없는 경우)
        locale = "en"

        message = localization.get_message(
            "combat.wait_action", locale, actor=actor.name
        )

        return {
            "success": True,
            "message": f"{ANSIColors.RED}{message}{ANSIColors.RESET}",
        }

    async def process_monster_turn(self, combat_id: str) -> Dict[str, Any]:
        """몬스터 턴 처리 (AI)"""
        logger.info(f"몬스터 턴 처리 시작 - combat_id: {combat_id}")

        combat = self.combat_manager.get_combat(combat_id)
        if not combat or not combat.is_active:
            logger.warning(
                f"전투를 찾을 수 없거나 비활성 상태 - combat_id: {combat_id}"
            )
            return {
                "success": False,
                "message": "전투를 찾을 수 없거나 이미 종료되었습니다.",
            }

        current_combatant = combat.get_current_combatant()
        if not current_combatant:
            logger.warning(f"현재 턴의 참가자를 찾을 수 없음 - combat_id: {combat_id}")
            return {"success": False, "message": "현재 턴의 참가자를 찾을 수 없습니다."}

        logger.info(f"몬스터 {current_combatant.name}의 턴 처리 중...")

        # 몬스터 AI: 랜덤한 플레이어 공격
        alive_players = combat.get_alive_players()
        if not alive_players:
            logger.warning(f"공격할 플레이어가 없음 - combat_id: {combat_id}")
            return {"success": False, "message": "공격할 대상이 없습니다."}

        target = random.choice(alive_players)
        logger.info(
            f"몬스터 {current_combatant.name}이(가) {target.name}을(를) 공격 시도"
        )

        # 공격 실행
        result = await self._execute_attack(combat, current_combatant, target.id)
        msg = f"{result.get('message', 'N/A')}"
        logger.info(f"몬스터 공격 결과: {result.get('success', False)}, 메시지: {msg}")

        # 전투 참가자들에게 몬스터 공격 결과 브로드캐스트
        for combatant in combat.combatants:
            if combatant.combatant_type == CombatantType.PLAYER:
                session = self.session_manager.get_player_session(combatant.id)
                if session:
                    await session.send_message({ "type": "combat_message", "message": msg })

        # 턴 로그 추가
        turn = CombatTurn(
            turn_number=combat.turn_number,
            combatant_id=current_combatant.id,
            action=CombatAction.ATTACK,
            target_id=target.id,
            damage_dealt=result.get("damage_dealt", 0),
            message=result.get("message", ""),
        )
        combat.add_combat_log(turn)

        # 다음 턴으로 진행
        combat.advance_turn()

        # 전투 종료 확인
        if combat.is_combat_over():
            rewards = await self._end_combat(combat)
            result["combat_over"] = True
            result["winners"] = [c.to_dict() for c in combat.get_winners()]
            result["rewards"] = rewards

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

            player_winners = [
                w for w in winners if w.combatant_type == CombatantType.PLAYER
            ]

            if player_winners:
                # 처치한 몬스터들로부터 보상 계산
                all_monsters = [
                    c
                    for c in combat.combatants
                    if c.combatant_type != CombatantType.PLAYER
                ]
                defeated_monsters = [m for m in all_monsters if not m.is_alive()]

                # 각 몬스터로부터 보상 수집 (현재 보상 시스템 비활성화)
                for monster_combatant in defeated_monsters:
                    # 보상 시스템 재개발 예정 - 현재는 드롭 아이템만 처리
                    logger.debug(
                        f"몬스터 {monster_combatant.name} 처치됨"
                    )

                logger.info(f"전투 종료 - 몬스터 {len(defeated_monsters)}마리 처치")
        else:
            logger.info(f"전투 {combat.id} 종료 - 무승부")

        # 죽은 몬스터들을 DB에 저장하고 아이템 드롭 처리
        from .combat import CombatantType

        if self.world_manager:
            for combatant in combat.combatants:
                if (
                    combatant.combatant_type != CombatantType.PLAYER
                    and not combatant.is_alive()
                ):
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
                                logger.info(
                                    f"몬스터 {combatant.name} ({combatant.id}) 사망 처리 완료"
                                )
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
        return {
            combat_id: combat
            for combat_id, combat in self.combat_manager.combat_instances.items()
            if combat.is_active
        }

    async def start_combat(
        self, player: Player, monster: Monster, room_id: str, broadcast_callback=None
    ) -> CombatInstance:
        """
        새로운 전투 시작

        Args:
            player: 플레이어 객체
            monster: 몬스터 객체
            room_id: 방 ID
            broadcast_callback: 브로드캐스트 콜백 함수

        Returns:
            CombatInstance: 생성된 전투 인스턴스
        """
        # 몹을 통해 이미 존재 하는 combat을 찾음
        _found = False
        logger.info("invoked")
        logger.info(monster)

        for combat in self.combat_manager.combat_instances.values():
            for combatant in combat.combatants:
                if monster.id == combatant.id and combatant.is_alive():
                    _found = True
                    break
            if _found:
                break

        if _found:
            # 플레이어 만 추가
            logger.info("플레이어 만 추가")
            self.combat_manager.add_player_to_combat(combat.id, player, player.id)
        else:
            logger.info("mark")
            combat = self.combat_manager.create_combat(room_id)  # TODO: 이 때 턴이 정해지면 안됨. 아래의 add 가 다 끝나면 그 이후에 만들어 져야 함 
            # 플레이어 추가
            logger.info("플레이어 추가")
            self.combat_manager.add_player_to_combat(combat.id, player, player.id)
            # 몬스터 추가
            logger.info("몬스터 추가")
            self.combat_manager.add_monster_to_combat(combat.id, monster)

        logger.info(
            f"전투 시작[{combat.id}] {player.username} vs {monster.get_localized_name('ko')}"
        )

        return combat

    async def add_monsters_to_combat(
        self, player_id: str, monsters: List[Monster]
    ) -> bool:
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
