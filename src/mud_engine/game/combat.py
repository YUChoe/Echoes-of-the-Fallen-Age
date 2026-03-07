"""
전투 시스템 - 인스턴스 기반 턴제 전투
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from .monster import Monster
from .models import Player
from ..core.localization import get_localization_manager
from ..core.types import SessionType
from ..server.ansi_colors import ANSIColors

logger = logging.getLogger(__name__)


class CombatAction(Enum):
    """전투 행동 타입"""

    ATTACK = "attack"
    DEFEND = "defend"
    SKILL = "skill"
    FLEE = "flee"
    WAIT = "wait"


class CombatantType(Enum):
    """전투 참가자 타입"""

    PLAYER = "player"
    MONSTER = "monster"


@dataclass
class Combatant:
    """전투 참가자"""

    id: str
    name: str
    combatant_type: CombatantType
    agility: int  # 민첩 (턴 순서 결정)
    max_hp: int
    current_hp: int
    attack_power: int
    defense: int
    is_defending: bool = False  # 방어 중인지 여부
    data: Optional[Dict[str, Any]] = None  # 추가 데이터 (AC, 공격보너스 등)

    def __post_init__(self):
        """초기화 후 검증"""
        if self.agility < 0:
            raise ValueError("민첩은 0 이상이어야 합니다")
        if self.max_hp <= 0:
            raise ValueError("최대 HP는 1 이상이어야 합니다")
        if self.current_hp < 0:
            self.current_hp = 0

    def is_alive(self) -> bool:
        """생존 여부 확인"""
        return self.current_hp > 0

    def take_damage(self, damage: int) -> int:
        """데미지를 받고 실제 받은 데미지 반환"""
        # 방어 중이면 데미지 50% 감소
        if self.is_defending:
            damage = damage // 2

        actual_damage = max(0, damage - self.defense)
        self.current_hp = max(0, self.current_hp - actual_damage)
        return actual_damage

    def heal(self, amount: int) -> None:
        """체력 회복"""
        self.current_hp = min(self.max_hp, self.current_hp + amount)

    def get_hp_percentage(self) -> float:
        """HP 퍼센트 반환"""
        if self.max_hp <= 0:
            return 0.0
        return (self.current_hp / self.max_hp) * 100

    def get_display_name(self, locale: str = "en", world_manager=None) -> str:
        """표시용 이름 반환 (언어별)"""
        if self.combatant_type == CombatantType.PLAYER:
            return self.name  # 플레이어는 이름 그대로
        elif self.combatant_type == CombatantType.MONSTER:
            # 몬스터는 world_manager를 통해 동적으로 이름 조회
            if world_manager:
                try:
                    # 비동기 함수를 동기적으로 호출할 수 없으므로 data에서 조회
                    if self.data and "monster" in self.data:
                        monster = self.data["monster"]
                        return monster.get_localized_name(locale)
                except Exception:
                    pass
            # 폴백: ID 또는 기본 이름 사용
            return self.name
        else:
            return self.name

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "id": self.id,
            "name": self.name,
            "combatant_type": self.combatant_type.value,
            "agility": self.agility,
            "max_hp": self.max_hp,
            "current_hp": self.current_hp,
            "attack_power": self.attack_power,
            "defense": self.defense,
            "is_defending": self.is_defending,
            "hp_percentage": self.get_hp_percentage(),
        }


@dataclass
class CombatTurn:
    """전투 턴 정보"""

    turn_number: int
    combatant_id: str
    action: Optional[CombatAction] = None
    target_id: Optional[str] = None
    damage_dealt: int = 0
    damage_received: int = 0
    message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "turn_number": self.turn_number,
            "combatant_id": self.combatant_id,
            "action": self.action.value if self.action else None,
            "target_id": self.target_id,
            "damage_dealt": self.damage_dealt,
            "damage_received": self.damage_received,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class CombatInstance:
    """전투 인스턴스"""

    id: str = field(default_factory=lambda: str(uuid4()))
    room_id: str = ""
    combatants: List[Combatant] = field(default_factory=list)
    turn_order: List[str] = field(default_factory=list)  # combatant_id 순서
    current_turn_index: int = 0  # 위의 리스트의 인덱스이니 턴이 증가함으로 인해 도돌이
    turn_number: int = 1  # 계속 증가
    # combat_log: List[CombatTurn] = field(default_factory=list)
    is_active: bool = True
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    # 연결 해제된 플레이어 추적 (player_id -> 해제 시간)
    disconnected_players: Dict[str, datetime] = field(default_factory=dict)
    # 타임아웃 tick 카운트 (8회 = 2분, 15초 간격)
    timeout_ticks: int = 0
    max_timeout_ticks: int = 8  # 8 * 15초 = 2분  # TODO: 이건 또 뭐야
    I18N = get_localization_manager()
    _entity_map: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """초기화 후 턴 순서 결정"""
        if not self.turn_order and self.combatants:
            self._determine_turn_order()

    def _determine_turn_order(self) -> None:
        """민첩 기반 턴 순서 결정 (높은 순서대로)"""
        # 민첩이 높은 순서대로 정렬
        sorted_combatants = sorted(
            self.combatants, key=lambda c: c.agility, reverse=True
        )
        self.turn_order = [c.id for c in sorted_combatants]
        logger.info(f"전투 {self.id} 턴 순서 결정: {self.turn_order}")

    def add_combatant(self, combatant: Combatant) -> None:
        """전투 참가자 추가"""
        if any(c.id == combatant.id for c in self.combatants):
            logger.warning(f"이미 전투에 참가 중인 참가자: {combatant.id}")
            return

        self.combatants.append(combatant)
        # 턴 순서 재결정
        self._determine_turn_order()
        logger.info(f"전투 {self.id}에 {combatant.name} 추가")
        for c in self.combatants:
            logger.info(f"- {c.get_display_name()}")

    def remove_combatant(self, combatant_id: str) -> bool:
        """전투 참가자 제거"""
        original_count = len(self.combatants)
        self.combatants = [c for c in self.combatants if c.id != combatant_id]

        if len(self.combatants) < original_count:
            # 턴 순서에서도 제거
            if combatant_id in self.turn_order:
                self.turn_order.remove(combatant_id)
            logger.info(f"전투 {self.id}에서 {combatant_id} 제거")
            return True

        return False

    def get_combatant(self, combatant_id: str) -> Optional[Combatant]:
        """참가자 조회"""
        for combatant in self.combatants:
            if combatant.id == combatant_id:
                return combatant
        return None

    def get_current_combatant(self) -> Optional[Combatant]:
        """현재 턴의 참가자 반환"""
        if not self.turn_order or self.current_turn_index >= len(self.turn_order):
            return None

        current_id = self.turn_order[self.current_turn_index]
        return self.get_combatant(current_id)

    def get_entity_map(self):
        return self._entity_map

    def set_entity_map(self, new_entity_map):
        self._entity_map = new_entity_map

    def get_alive_combatants(self) -> List[Combatant]:
        """생존한 참가자 목록 반환"""
        return [c for c in self.combatants if c.is_alive()]

    def get_alive_players(self) -> List[Combatant]:
        """생존한 플레이어 목록 반환"""
        return [
            c
            for c in self.combatants
            if c.is_alive() and c.combatant_type == CombatantType.PLAYER
        ]

    def get_alive_monsters(self) -> List[Combatant]:
        """생존한 몬스터 목록 반환"""
        return [
            c
            for c in self.combatants
            if c.is_alive() and c.combatant_type == CombatantType.MONSTER
        ]

    def advance_turn(self, is_recursive=False) -> None:
        logger.info("invoked advance_turn")
        """다음 턴으로 진행"""
        if not self.turn_order:
            logger.info("not self.turn_order")
            return

        # 다음 참가자로 이동
        self.current_turn_index += 1
        if not is_recursive:
            self.turn_number += 1
            logger.info(f"전투 {self.id} 턴 {self.turn_number}")

        if self.current_turn_index >= len(self.turn_order):
            # 순서 맨뒤에서 다시 맨앞으로
            self.current_turn_index = 0

        # 사망한 참가자는 건너뛰기
        current = self.get_current_combatant()
        if current and not current.is_alive():
            logger.info("current_combatant dead")
            self.advance_turn(True)  # 이런 경우 self.turn_number 는 증가하면 안됨
        # NOTE: 누구턴 메시지는 실행 한 곳에서

    # def add_combat_log(self, turn: CombatTurn) -> None:
    #     """전투 로그 추가"""
    #     self.combat_log.append(turn)

    def is_combat_over(self) -> bool:
        """전투 종료 여부 확인"""
        # TODO: PVP 떄는 어떻게 판단? 우리편 다른편으로 구분 되어야 할 듯
        alive_players = self.get_alive_players()
        alive_monsters = self.get_alive_monsters()

        # 한쪽이 전멸하면 전투 종료
        return len(alive_players) == 0 or len(alive_monsters) == 0

    def mark_player_disconnected(self, player_id: str) -> None:
        """플레이어를 연결 해제 상태로 표시"""
        if player_id not in self.disconnected_players:
            self.disconnected_players[player_id] = datetime.now()
            logger.info(f"전투 {self.id}: 플레이어 {player_id} 연결 해제 표시")

    def mark_player_reconnected(self, player_id: str) -> bool:
        """플레이어 재접속 처리"""
        if player_id in self.disconnected_players:
            del self.disconnected_players[player_id]
            logger.info(f"전투 {self.id}: 플레이어 {player_id} 재접속")
            return True
        return False

    def is_player_disconnected(self, player_id: str) -> bool:
        """플레이어가 연결 해제 상태인지 확인"""
        return player_id in self.disconnected_players

    def has_connected_players(self) -> bool:
        """연결된 플레이어가 있는지 확인"""
        alive_players = self.get_alive_players()
        for player in alive_players:
            if player.id not in self.disconnected_players:
                return True
        return False

    def increment_timeout_tick(self) -> bool:
        """
        타임아웃 tick 증가. 타임아웃 시 True 반환.
        연결된 플레이어가 없을 때만 tick 증가.
        """
        if not self.has_connected_players():
            self.timeout_ticks += 1
            logger.info(
                f"전투 {self.id}: 타임아웃 tick {self.timeout_ticks}/{self.max_timeout_ticks}"
            )
            return self.timeout_ticks >= self.max_timeout_ticks
        else:
            # 연결된 플레이어가 있으면 tick 리셋
            if self.timeout_ticks > 0:
                self.timeout_ticks = 0
                logger.info(
                    f"전투 {self.id}: 타임아웃 tick 리셋 (연결된 플레이어 있음)"
                )
        return False

    def end_combat(self) -> None:
        """전투 종료"""
        self.is_active = False
        self.ended_at = datetime.now()
        logger.info(f"전투 {self.id} 종료")

    def get_winners(self) -> List[Combatant]:
        """승리자 목록 반환"""
        if not self.is_combat_over():
            return []

        alive_players = self.get_alive_players()
        alive_monsters = self.get_alive_monsters()

        if alive_players:
            return alive_players
        elif alive_monsters:
            return alive_monsters
        else:
            return []

    @property
    def monsters(self) -> List[Combatant]:
        """몬스터 목록 반환 (호환성을 위한 속성)"""
        return self.get_alive_monsters()

    def set_player_action(self, action: CombatAction) -> bool:
        """
        플레이어 액션 설정 (간단한 버전)

        Args:
            action: 전투 행동

        Returns:
            bool: 성공 여부
        """
        current = self.get_current_combatant()
        if not current or current.combatant_type != CombatantType.PLAYER:
            return False

        # 액션은 실제로 처리되지 않고 단순히 성공 반환
        # 실제 처리는 CombatHandler에서 수행
        return True

    def get_combat_status(self) -> Dict[str, Any]:
        """전투 상태 조회 (호환성을 위한 메서드)"""
        current = self.get_current_combatant()
        alive_players = self.get_alive_players()
        alive_monsters = self.get_alive_monsters()

        # 플레이어 정보
        player_info = None
        if alive_players:
            player = alive_players[0]
            player_info = {
                "id": player.id,
                "name": player.name,
                "hp": player.current_hp,
                "max_hp": player.max_hp,
                "hp_percentage": player.get_hp_percentage(),
                "initiative": player.agility,
            }

        # 몬스터 정보
        monster_info = []
        for monster in alive_monsters:
            monster_info.append(
                {
                    "id": monster.id,
                    "name": monster.name,
                    "hp": monster.current_hp,
                    "max_hp": monster.max_hp,
                    "hp_percentage": monster.get_hp_percentage(),
                    "initiative": monster.agility,
                    "is_alive": monster.is_alive(),
                }
            )

        return {
            "combat_id": self.id,
            "turn_number": self.turn_number,
            "current_turn": current.name if current else "알 수 없음",
            "state": "active" if self.is_active else "ended",
            "player": player_info,
            "monsters": monster_info,
            "monster": monster_info[0] if monster_info else None,  # 호환성
            # "last_turn": (
            #     self.combat_log[-1].message if self.combat_log else "전투 시작"
            # ),
            "current_target_index": 0,
        }

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "id": self.id,
            "room_id": self.room_id,
            "combatants": [c.to_dict() for c in self.combatants],
            "turn_order": self.turn_order,
            "current_turn_index": self.current_turn_index,
            "turn_number": self.turn_number,
            "current_combatant": (
                self.get_current_combatant().to_dict()
                if self.get_current_combatant()
                else None
            ),
            "is_active": self.is_active,
            "is_over": self.is_combat_over(),
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
        }

    def get_whos_turn(self, locale="en") -> str:
        logger.info("get_whos_turn invoked")
        # 현재 전투 턴 combatant 로 이름 구하기
        combatant = self.get_current_combatant()
        next_turn_id = combatant.id

        if self.get_current_combatant().id == next_turn_id:
            logger.info(f"player turn")
        # start_message += f"{self._get_turn_message(next_turn_id, locale)}"

        # monster_name = target_monster.get_localized_name(locale)
        # 다른 플레이어 이거나 몹인 경우 이렇게 처리 해도 됨
        if locale == "ko":  # TODO:
            message = f"{ANSIColors.RED}⏳ {combatant.get_display_name(locale)}의 턴입니다...{ANSIColors.RESET}"
        else:
            message = f"{ANSIColors.RED}⏳ {combatant.get_display_name(locale)}'s turn...{ANSIColors.RESET}"
        logger.info(message)
        return message

    def get_combat_status_message(self, locale: str = "en") -> str:
        """전투 상태 메시지 생성"""
        lines = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"{ANSIColors.RED}{self.I18N.get_message('combat.round', locale, round=self.turn_number)}{ANSIColors.RESET}",
            "",
        ]

        # 플레이어 정보
        players = self.get_alive_players()
        if players:
            player = players[0]
            lines.append(
                f"[0] 👤 {player.name} HP: {player.current_hp}/{player.max_hp}"
            )

        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        # 몬스터 정보
        monsters = self.get_alive_monsters()
        # room_entity_map = getattr(session, "room_entity_map", {})  # ???? 이게 왜 getattr 에 ?
        room_entity_map = self.get_entity_map()
        logger.info(room_entity_map)  # 왜 못찾음? 왜 {} 임?
        for monster in monsters:
            monster_name = monster.name  # monster.name 은 id
            if monster.data and "monster" in monster.data:
                monster_obj = monster.data["monster"]
                monster_name = monster_obj.get_localized_name(locale)
            for num in room_entity_map:
                if (
                    "id" in room_entity_map[num]
                    and room_entity_map[num]["id"] == monster.name
                ):
                    logger.info(f"found id[{monster.name}] {room_entity_map[num]}")
                    break
            else:
                num = "?"
            lines.append(
                f"[{num}] 👹 {monster_name}: HP: {monster.current_hp}/{monster.max_hp}"
            )
        lines.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(lines)
        """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚔️ Turn 2
[0] 👤 SUPERADMIN HP: 62/62
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[1] 👹 Small Rat: HP: 4/17
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        return "\n".join(lines) + "\n"

    def _get_turn_message(self, player_id: str, locale: str = "en") -> str:
        """플레이어 턴 메시지 생성"""
        turn_message = "\n".join(
            [
                self.I18N.get_message("combat.your_turn", locale),
                "",
                f"{self.I18N.get_message('combat.action_attack', locale)}",
                f"{self.I18N.get_message('combat.action_defend', locale)}",
                f"{self.I18N.get_message('combat.action_flee', locale)}",
                f"[4] Item  ",
                f"[5] Spell",
                self.I18N.get_message("combat.enter_command", locale),
            ]
        )
        logger.info(turn_message)
        return turn_message


class CombatManager:
    """전투 매니저 - 전투 인스턴스 관리"""

    def __init__(self, session_manager: Any = None):
        """전투 매니저 초기화"""
        self.combat_instances: Dict[
            str, CombatInstance
        ] = {}  # combat_id -> CombatInstance
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

    # TODO: 문제는 참자가 마다 locale 설정이 다를 수 있으니 관련 정보를 combatant 안에 한번에 받아야 함
    # 그리고 나중에 클라이언트가 이부분 처리를 하게 된다면 다 제거하고 영어+기호 로만 전달 후 클라에서 변환하도록 만들 것
    async def create_turn_for_new_instance(
        self, combat: CombatInstance, locale: str = "en"
    ) -> None:
        # 전투 참가자들에게 결정 된 턴 순서 브로드캐스트
        msg = ["순서: "]  # TODO: i18n
        logger.info(f"{combat.turn_order}")
        superadmin_id: str = ""
        for combatant_id in combat.turn_order:
            if combat.get_combatant(combatant_id).name == "SUPERADMIN":
                superadmin_id = combat.get_combatant(combatant_id).id
                logger.info(f"superadmin_id {superadmin_id}")
                break  # 하나만 찾아라
        if superadmin_id:
            combat.turn_order.insert(
                0, combat.turn_order.pop(combat.turn_order.index(superadmin_id))
            )
            logger.info(f"after {combat.turn_order}")

        for combatant_id in combat.turn_order:
            name = combat.get_combatant(combatant_id).name
            if "monster" in combat.get_combatant(combatant_id).data:
                name = (
                    combat.get_combatant(combatant_id)
                    .data["monster"]
                    .get_localized_name(locale)
                )
            msg.append(f"[{name}]")
        logger.info(" ".join(msg))

        # BROADCASE
        combatant: Combatant
        for combatant in combat.combatants:
            if combatant.combatant_type == CombatantType.PLAYER:
                session = self.session_manager.get_player_session(combatant.id)
                if session:
                    await session.send_message(
                        {"type": "combat_message", "message": " ".join(msg)}
                    )
        return

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

    def add_player_to_combat(
        self, combat_id: str, player: Player, player_id: str
    ) -> bool:
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
        logger.info(combat)

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
        finished_combats = [
            combat_id
            for combat_id, combat in self.combat_instances.items()
            if not combat.is_active
        ]

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

    def try_rejoin_combat(
        self, player_id: str, player: Player
    ) -> Optional[CombatInstance]:
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
