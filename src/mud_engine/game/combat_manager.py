"""
전투 매니저 - 전투 인스턴스 관리
"""

import logging
from typing import Any, Dict, List, Optional

from .combat import CombatInstance, CombatantType, Combatant
from .monster import Monster
from .models import Player
from ..core.localization import get_localization_manager

logger = logging.getLogger(__name__)


class CombatManager:
    """전투 매니저 - 전투 인스턴스 관리"""

    def __init__(self, session_manager: Any = None):
        """전투 매니저 초기화"""
        self.combat_instances: Dict[str, CombatInstance] = {}  # combat_id -> CombatInstance
        self.room_combats: Dict[str, str] = {}  # room_id -> combat_id
        self.player_combats: Dict[str, str] = {}  # player_id -> combat_id
        self.session_manager = session_manager
        logger.info("CombatManager 초기화 완료")

    def create_combat(self, room_id: str) -> CombatInstance:
        """새로운 전투 인스턴스 생성"""
        combat = CombatInstance(room_id=room_id)
        self.combat_instances[combat.id] = combat
        self.room_combats[room_id] = combat.id
        logger.info(f"방 {room_id}에 전투 인스턴스 {combat.id} 생성")
        return combat

    def _build_turn_order_message(self, combat: CombatInstance, locale: str) -> str:
        """참가자의 locale에 맞는 턴 순서 메시지 생성"""
        I18N = get_localization_manager()
        parts = [I18N.get_message("combat.turn_order", locale)]
        for combatant_id in combat.turn_order:
            combatant = combat.get_combatant(combatant_id)
            name = combatant.get_display_name(locale)
            parts.append(f"[{name}]")
        return " ".join(parts)

    async def _broadcast_per_player_locale(self, combat: CombatInstance, build_msg) -> None:
        """각 플레이어의 locale에 맞게 개별 메시지를 전송"""
        for c in combat.combatants:
            if c.combatant_type == CombatantType.PLAYER:
                session = self.session_manager.get_player_session(c.id)
                if session:
                    player_locale = getattr(session, 'locale', 'en')
                    msg = build_msg(player_locale)
                    await session.send_message({"type": "combat_message", "message": msg})

    async def turn_boardcast_for_new_instance(self, combat: CombatInstance, locale: str = "en") -> None:
        """전투 참가자들에게 결정된 턴 순서 브로드캐스트 (참가자별 locale)"""
        logger.info(f"{combat.turn_order}")
        # SUPERADMIN 우선 턴 처리
        superadmin_id: str = ""
        for combatant_id in combat.turn_order:
            if combat.get_combatant(combatant_id).name == "SUPERADMIN":
                superadmin_id = combat.get_combatant(combatant_id).id
                logger.info(f"superadmin_id {superadmin_id}")
                break
        if superadmin_id:
            combat.turn_order.insert(0, combat.turn_order.pop(combat.turn_order.index(superadmin_id)))
            logger.info(f"after {combat.turn_order}")

        # 참가자별 locale로 개별 전송
        await self._broadcast_per_player_locale(
            combat, lambda loc: self._build_turn_order_message(combat, loc)
        )

    async def turn_boardcast_for_new_instance_with_aggresive_mob(self, combat: CombatInstance, monster: Monster) -> None:
        """선공 몬스터 전투 시작 시 턴 순서 브로드캐스트 (참가자별 locale)"""
        combat.turn_order.insert(0, combat.turn_order.pop(combat.turn_order.index(monster.id)))
        logger.info(f"after {combat.turn_order}")

        # 참가자별 locale로 개별 전송
        await self._broadcast_per_player_locale(
            combat, lambda loc: self._build_turn_order_message(combat, loc)
        )

    def get_combat_instances(self) -> Dict[str, CombatInstance]:
        return self.combat_instances

    def get_combat(self, combat_id: str) -> Optional[CombatInstance]:
        """전투 인스턴스 조회"""
        return self.combat_instances.get(combat_id)

    def get_combat_by_room(self, room_id: str) -> Optional[CombatInstance]:
        """방 ID로 전투 인스턴스 조회"""
        combat_id = self.room_combats.get(room_id)
        if combat_id:
            return self.get_combat(combat_id)
        return None

    def get_combat_by_player(self, player_id: str) -> Optional[CombatInstance]:
        """플레이어 ID로 전투 인스턴스 조회"""
        combat_id = self.player_combats.get(player_id)
        if combat_id:
            return self.get_combat(combat_id)
        return None

    def is_player_in_combat(self, player_id: str) -> bool:
        """플레이어가 전투 중인지 확인"""
        combat = self.get_combat_by_player(player_id)
        return combat is not None and combat.is_active

    def is_room_in_combat(self, room_id: str) -> bool:
        """방에 전투가 진행 중인지 확인"""
        combat = self.get_combat_by_room(room_id)
        return combat is not None and combat.is_active

    def add_player_to_combat(self, combat_id: str, player: Player, player_id: str) -> bool:
        """플레이어를 전투에 추가"""
        combat = self.get_combat(combat_id)
        if not combat or not combat.is_active:
            logger.warning(f"전투 {combat_id}를 찾을 수 없거나 비활성 상태")
            return False

        # 이미 다른 전투에 참가 중인지 확인
        if self.is_player_in_combat(player_id):
            logger.warning(f"플레이어 {player_id}는 이미 전투 중")
            return False

        # Combatant 생성
        from .stats import StatType

        combatant = Combatant(
            id=player_id,
            name=player.get_display_name(),
            combatant_type=CombatantType.PLAYER,
            agility=player.stats.get_primary_stat(StatType.DEX),
            max_hp=player.stats.get_secondary_stat(StatType.HP),
            # current_hp=player.stats.get_secondary_stat(StatType.HP),
            current_hp=player.stats.get_current_hp(),
            attack_power=player.stats.get_secondary_stat(StatType.ATK),
            defense=player.stats.get_secondary_stat(StatType.DEF),
        )
        logger.info(f"플레이어 {player_id}를 전투 {combat_id}에 추가")
        combatant.data = {"player": player}
        combat.add_combatant(combatant)
        self.player_combats[player_id] = combat_id
        return True

    def add_monster_to_combat(self, combat_id: str, monster: Monster) -> bool:
        """몬스터를 전투에 추가"""
        logger.info("invoked")
        combat = self.get_combat(combat_id)
        if not combat or not combat.is_active:
            logger.warning(f"전투 {combat_id}를 찾을 수 없거나 비활성 상태")
            return False
        logger.info(combat.to_simple())

        # Combatant 생성 (D&D 능력치 사용)
        # 몬스터 이름은 원본 Monster 객체를 참조하여 동적으로 처리
        logger.info(f"monster[{monster}]")
        combatant = Combatant(
            id=monster.id,
            name=monster.id,  # ID로 저장하고 표시 시 동적으로 언어별 이름 조회
            combatant_type=CombatantType.MONSTER,
            agility=monster.stats.dexterity,  # 민첩 사용
            max_hp=monster.stats.max_hp,
            current_hp=monster.stats.current_hp,  # 얘도 전투가 종료 되도 이 전에 hp 를 보존 하고 있어야 함
            attack_power=monster.stats.attack_power,
            defense=monster.stats.defense,
        )
        logger.info(combatant)
        # Monster 객체의 추가 정보를 data에 저장 (전투 계산에 사용)
        combatant.data = {
            "monster": monster,  # Monster 객체 전체 저장 (다국어 이름 조회용)
            "armor_class": monster.stats.armor_class,
            "attack_bonus": monster.stats.attack_bonus,
            "initiative_bonus": monster.stats.initiative_bonus,
            "level": monster.stats.level,
        }
        logger.info(
            f"몬스터 {monster.id}를 전투 {combat_id}에 추가 (AC: {monster.stats.armor_class}, 공격보너스: {monster.stats.attack_bonus})"
        )
        combat.add_combatant(combatant)
        return True

    def remove_player_from_combat(self, player_id: str) -> bool:
        """플레이어를 전투에서 제거"""
        combat = self.get_combat_by_player(player_id)
        if not combat:
            return False

        success = combat.remove_combatant(player_id)
        if success:
            del self.player_combats[player_id]
            logger.info(f"플레이어 {player_id}를 전투에서 제거")

        return success

    def end_combat(self, combat_id: str) -> bool:
        """전투 종료"""
        combat = self.get_combat(combat_id)
        if not combat:
            return False

        combat.end_combat()

        # 플레이어 전투 매핑 제거
        for player_id in list(self.player_combats.keys()):
            if self.player_combats[player_id] == combat_id:
                del self.player_combats[player_id]

        # 방 전투 매핑 제거
        if combat.room_id in self.room_combats:
            del self.room_combats[combat.room_id]

        logger.info(f"전투 {combat_id} 종료 및 정리 완료")
        return True

    def cleanup_finished_combats(self) -> int:
        """종료된 전투 인스턴스 정리"""
        finished_combats = [combat_id for combat_id, combat in self.combat_instances.items() if not combat.is_active]

        for combat_id in finished_combats:
            del self.combat_instances[combat_id]

        if finished_combats:
            logger.info(f"{len(finished_combats)}개의 종료된 전투 인스턴스 정리")

        return len(finished_combats)

    def get_active_combats_count(self) -> int:
        """활성 전투 수 반환"""
        return sum(1 for combat in self.combat_instances.values() if combat.is_active)

    def mark_player_disconnected(self, player_id: str) -> bool:
        """
        플레이어를 연결 해제 상태로 표시 (전투 유지)

        Args:
            player_id: 플레이어 ID

        Returns:
            bool: 성공 여부
        """
        combat = self.get_combat_by_player(player_id)
        if not combat or not combat.is_active:
            return False

        combat.mark_player_disconnected(player_id)
        logger.info(f"플레이어 {player_id} 연결 해제 - 전투 {combat.id} 유지")
        return True

    def try_rejoin_combat(self, player_id: str, player: Player) -> Optional[CombatInstance]:
        """
        플레이어 재접속 시 기존 전투에 복귀 시도

        Args:
            player_id: 플레이어 ID
            player: 플레이어 객체

        Returns:
            CombatInstance: 복귀한 전투 인스턴스 (없으면 None)
        """
        combat_id = self.player_combats.get(player_id)
        if not combat_id:
            return None

        combat = self.get_combat(combat_id)
        if not combat or not combat.is_active:
            # 전투가 종료되었으면 매핑 제거
            if player_id in self.player_combats:
                del self.player_combats[player_id]
            return None

        # 재접속 처리
        if combat.mark_player_reconnected(player_id):
            # Combatant 데이터 업데이트 (Player 객체 갱신)
            combatant = combat.get_combatant(player_id)
            if combatant and combatant.data:
                combatant.data["player"] = player
            logger.info(f"플레이어 {player_id} 전투 {combat_id}에 복귀")
            return combat

        return None

    async def process_combat_tick(self) -> Dict[str, Any]:
        """
        전투 tick 처리 (스케줄러에서 15초마다 호출)

        Returns:
            Dict: tick 처리 결과
        """
        logger.info("process_combat_tick invoked")

        result: Dict[str, Any] = {
            "processed_combats": 0,
            "timed_out_combats": [],
            "active_combats": 0,
        }

        timed_out_combat_ids: List[str] = []

        for combat_id, combat in list(self.combat_instances.items()):
            if not combat.is_active:
                continue

            result["processed_combats"] += 1

            # 타임아웃 체크 (연결된 플레이어가 없는 경우만)
            if combat.increment_timeout_tick():
                timed_out_combat_ids.append(combat_id)
                result["timed_out_combats"].append(combat_id)
                logger.info(f"전투 {combat_id} 타임아웃 (2분 경과)")

        # 타임아웃된 전투 종료
        for combat_id in timed_out_combat_ids:
            self.end_combat(combat_id)

        result["active_combats"] = self.get_active_combats_count()
        return result

    def get_disconnected_players_in_combat(self, combat_id: str) -> List[str]:
        """전투에서 연결 해제된 플레이어 목록 반환"""
        combat = self.get_combat(combat_id)
        if not combat:
            return []
        return list(combat.disconnected_players.keys())
