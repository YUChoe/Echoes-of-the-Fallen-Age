"""
전투 시스템 - 인스턴스 기반 턴제 전투
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..core.localization import get_localization_manager
from ..server.ansi_colors import ANSIColors
from .combatant import CombatAction, CombatantType, Combatant  # noqa: F401

logger = logging.getLogger(__name__)


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
        sorted_combatants = sorted(self.combatants, key=lambda c: c.agility, reverse=True)
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

    # TODO: comnatant 를 player vs mobs 로 한정할 수 없고 전체를 몰아 넣고 나와 적대적인지 아닌지로 구분 해야 함
    #    그리고 턴은 골고루 돌아 옴
    def get_alive_players(self) -> List[Combatant]:
        """생존한 플레이어 목록 반환"""
        return [c for c in self.combatants if c.is_alive() and c.combatant_type == CombatantType.PLAYER]

    def get_alive_monsters(self) -> List[Combatant]:
        """생존한 몬스터 목록 반환"""
        return [c for c in self.combatants if c.is_alive() and c.combatant_type == CombatantType.MONSTER]

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
            logger.info(f"전투 {self.id}: 타임아웃 tick {self.timeout_ticks}/{self.max_timeout_ticks}")
            return self.timeout_ticks >= self.max_timeout_ticks
        else:
            # 연결된 플레이어가 있으면 tick 리셋
            if self.timeout_ticks > 0:
                self.timeout_ticks = 0
                logger.info(f"전투 {self.id}: 타임아웃 tick 리셋 (연결된 플레이어 있음)")
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

    def to_simple(self) -> str:
        r = f'CombatInstance[{self.id} room_id[{self.room_id}] is_active[{self.is_active}]'
        r += f'_entity_map[{self._entity_map}]'
        return r

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "id": self.id,
            "room_id": self.room_id,
            "combatants": [c.to_dict() for c in self.combatants],
            "turn_order": self.turn_order,
            "current_turn_index": self.current_turn_index,
            "turn_number": self.turn_number,
            "current_combatant": (self.get_current_combatant().to_dict() if self.get_current_combatant() else None),
            "is_active": self.is_active,
            "is_over": self.is_combat_over(),
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
        }

    def get_whos_turn(self, locale="en") -> str:
        logger.info("get_whos_turn invoked")
        # 현재 전투 턴 combatant 로 이름 구하기
        combatant = self.get_current_combatant()
        # next_turn_id = combatant.id

        # if self.get_current_combatant().id == next_turn_id:
        #     logger.info(f"player turn")
        # start_message += f"{self._get_turn_message(next_turn_id, locale)}"

        # monster_name = target_monster.get_localized_name(locale)
        # 다른 플레이어 이거나 몹인 경우 이렇게 처리 해도 됨
        name = combatant.get_display_name(locale)
        message = f"{ANSIColors.RED}{self.I18N.get_message('combat.whos_turn', locale, name=name)}{ANSIColors.RESET}"

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
            lines.append(f"[0] 👤 {player.name} HP: {player.current_hp}/{player.max_hp}")

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
                if "id" in room_entity_map[num] and room_entity_map[num]["id"] == monster.name:
                    logger.info(f"found id[{monster.name}] {room_entity_map[num]}")
                    break
            else:
                num = "?"
            lines.append(f"[{num}] 👹 {monster_name}: HP: {monster.current_hp}/{monster.max_hp}")
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

    def get_player_turn_message(self, locale: str = "en") -> str:
        """플레이어 턴 메시지 생성"""
        turn_message = "\n".join(
            [
                self.I18N.get_message("combat.your_turn", locale),
                "",
                f"{self.I18N.get_message('combat.action_attack', locale)}",
                f"{self.I18N.get_message('combat.action_defend', locale)}",
                f"{self.I18N.get_message('combat.action_flee', locale)}",
                f"[4] Item  ",
                f"[7] Spell",
                f"[9] End Turn / 턴넘기기",
                self.I18N.get_message("combat.enter_command", locale),
            ]
        )
        logger.info(turn_message)
        return turn_message



