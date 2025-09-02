"""
전투 시스템 구현
"""

import random
import logging
import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union, Tuple, Callable
from enum import Enum
from datetime import datetime

from .models import Player
from .monster import Monster, MonsterStats
from .stats import PlayerStats, StatType, StatCalculator


class CombatAction(Enum):
    """전투 액션 타입"""
    ATTACK = "attack"
    DEFEND = "defend"
    FLEE = "flee"
    USE_ITEM = "use_item"
    CAST_SPELL = "cast_spell"


class CombatMessageType(Enum):
    """전투 메시지 타입"""
    COMBAT_START = "combat_start"
    COMBAT_MESSAGE = "combat_message"
    COMBAT_STATUS = "combat_status"
    COMBAT_END = "combat_end"
    TURN_START = "turn_start"
    ACTION_RESULT = "action_result"


class CombatResult(Enum):
    """전투 결과"""
    ONGOING = "ongoing"
    PLAYER_VICTORY = "player_victory"
    MONSTER_VICTORY = "monster_victory"
    PLAYER_FLED = "player_fled"
    DRAW = "draw"


class CombatState(Enum):
    """전투 상태"""
    INITIALIZING = "initializing"  # 전투 초기화 중
    ROLLING_INITIATIVE = "rolling_initiative"  # Initiative 계산 중
    WAITING_FOR_ACTION = "waiting_for_action"  # 플레이어 액션 대기
    PROCESSING_TURN = "processing_turn"  # 턴 처리 중
    COMBAT_ENDED = "combat_ended"  # 전투 종료


@dataclass
class CombatTurn:
    """전투 턴 정보"""
    turn_number: int
    attacker_id: str
    attacker_type: str  # "player" or "monster"
    action: CombatAction
    target_id: str
    damage_dealt: int = 0
    is_critical: bool = False
    is_hit: bool = True
    message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """JSON 직렬화를 위한 딕셔너리 변환"""
        return {
            'turn_number': self.turn_number,
            'attacker_id': self.attacker_id,
            'attacker_type': self.attacker_type,
            'action': self.action.value,  # Enum을 문자열로 변환
            'target_id': self.target_id,
            'damage_dealt': self.damage_dealt,
            'is_critical': self.is_critical,
            'is_hit': self.is_hit,
            'message': self.message,
            'timestamp': self.timestamp.isoformat()  # datetime을 문자열로 변환
        }


@dataclass
class CombatParticipant:
    """전투 참여자 정보"""
    id: str
    name: str
    participant_type: str  # "player" or "monster"
    max_hp: int
    current_hp: int
    attack_power: int
    defense: int
    speed: int
    accuracy: int = 80
    critical_chance: int = 5
    is_defending: bool = False
    initiative: int = 0  # Initiative 값 (속도 + 1d20)
    pending_action: Optional[CombatAction] = None  # 대기 중인 액션

    def is_alive(self) -> bool:
        """생존 여부 확인"""
        return self.current_hp > 0

    def take_damage(self, damage: int) -> int:
        """데미지를 받고 실제 받은 데미지 반환"""
        if self.is_defending:
            damage = int(damage * 0.5)  # 방어 시 데미지 50% 감소
            self.is_defending = False

        actual_damage = max(1, damage - self.defense)
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

    def roll_initiative(self) -> int:
        """Initiative 계산 (속도 + 1d20)"""
        roll = random.randint(1, 20)
        self.initiative = self.speed + roll
        return self.initiative


class CombatSystem:
    """전투 시스템 메인 클래스"""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.active_combats: Dict[str, 'AutoCombat'] = {}  # player_id -> AutoCombat
        self.combat_tasks: Dict[str, asyncio.Task] = {}  # player_id -> combat_task
        self.room_combats: Dict[str, List[str]] = {}  # room_id -> List[player_id] (방별 전투 목록)

    async def start_combat(self, player: Player, monsters: Union[Monster, List[Monster]], room_id: str,
                          broadcast_callback: Optional[Callable] = None) -> 'AutoCombat':
        """전투 시작 (다중 전투 지원)"""
        # 단일 몬스터인 경우 리스트로 변환
        if isinstance(monsters, Monster):
            monsters = [monsters]

        monster_names = [monster.get_localized_name('ko') for monster in monsters]
        self.logger.info(f"전투 시작: {player.username} vs {', '.join(monster_names)} in room {room_id}")

        # 플레이어가 이미 전투 중이라면 몬스터 추가 또는 새 전투 시작
        if player.id in self.active_combats:
            existing_combat = self.active_combats[player.id]
            # 기존 전투에 몬스터 추가
            await self.add_monsters_to_combat(player.id, monsters)
            return existing_combat
        else:
            # 새 다중 전투 생성
            combat = AutoCombat(player, monsters, room_id, broadcast_callback)
            self.active_combats[player.id] = combat

            # 방별 전투 목록에 추가
            if room_id not in self.room_combats:
                self.room_combats[room_id] = []
            self.room_combats[room_id].append(player.id)

            # 자동 전투 루프 시작
            task = asyncio.create_task(combat.start_auto_combat())
            self.combat_tasks[player.id] = task

            return combat

    async def add_monsters_to_combat(self, player_id: str, new_monsters: List[Monster]) -> bool:
        """기존 전투에 몬스터 추가"""
        if player_id not in self.active_combats:
            return False

        combat = self.active_combats[player_id]

        # 새 몬스터들을 전투에 추가
        for monster in new_monsters:
            monster_participant = combat._create_monster_participant(monster)
            combat.monster_participants.append(monster_participant)
            combat.monsters.append(monster)

            # Initiative 계산 및 턴 순서에 추가
            monster_participant.roll_initiative()
            combat.turn_order.append(monster_participant)

        # 턴 순서 재정렬 (Initiative 순)
        combat.turn_order.sort(key=lambda p: p.initiative, reverse=True)

        # 현재 턴 인덱스 조정
        current_participant = combat.turn_order[combat.current_turn_index] if combat.turn_order else None
        if current_participant:
            # 현재 턴 참여자의 새로운 인덱스 찾기
            for i, participant in enumerate(combat.turn_order):
                if participant.id == current_participant.id:
                    combat.current_turn_index = i
                    break

        # 몬스터 추가 알림
        monster_names = [monster.get_localized_name('ko') for monster in new_monsters]
        add_message = f"⚔️ {', '.join(monster_names)}이(가) 전투에 참여했습니다!"
        await combat._broadcast_message(add_message, CombatMessageType.COMBAT_MESSAGE)

        self.logger.info(f"전투에 몬스터 추가: {', '.join(monster_names)}")
        return True

    def get_combat_by_room(self, room_id: str) -> List['AutoCombat']:
        """방의 모든 활성 전투 조회"""
        if room_id not in self.room_combats:
            return []

        combats = []
        for player_id in self.room_combats[room_id]:
            if player_id in self.active_combats:
                combats.append(self.active_combats[player_id])
        return combats

    def get_combat_by_player(self, player_id: str) -> Optional['AutoCombat']:
        """플레이어의 활성 전투 조회"""
        return self.active_combats.get(player_id)

    async def end_player_combat(self, player_id: str) -> None:
        """플레이어의 전투 종료"""
        if player_id in self.active_combats:
            combat = self.active_combats[player_id]
            room_id = combat.room_id
            self.logger.info(f"전투 종료: player {player_id}, 결과: {combat.result}")

            # 전투 태스크 취소
            if player_id in self.combat_tasks:
                task = self.combat_tasks[player_id]
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                del self.combat_tasks[player_id]

            # 전투 상태를 종료로 변경
            combat.state = CombatState.COMBAT_ENDED
            del self.active_combats[player_id]

            # 방별 전투 목록에서 제거
            if room_id in self.room_combats and player_id in self.room_combats[room_id]:
                self.room_combats[room_id].remove(player_id)
                if not self.room_combats[room_id]:  # 빈 리스트면 제거
                    del self.room_combats[room_id]

    async def end_combat(self, room_id: str) -> None:
        """방의 모든 전투 종료 (하위 호환성을 위해 유지)"""
        if room_id in self.room_combats:
            player_ids = self.room_combats[room_id].copy()
            for player_id in player_ids:
                await self.end_player_combat(player_id)

    def is_in_combat(self, player_id: str) -> bool:
        """플레이어가 전투 중인지 확인"""
        for combat in self.active_combats.values():
            if combat.player_participant.id == player_id:
                return True
        return False

    def get_player_combat(self, player_id: str) -> Optional['AutoCombat']:
        """플레이어의 현재 전투 조회"""
        for combat in self.active_combats.values():
            if combat.player_participant.id == player_id:
                return combat
        return None

    def set_player_action(self, player_id: str, action: CombatAction) -> bool:
        """플레이어 액션 설정 (자동 전투에서 사용)"""
        combat = self.get_player_combat(player_id)
        if not combat:
            return False

        combat.player_participant.pending_action = action
        return True

    def calculate_damage(self, attacker: CombatParticipant,
                        defender: CombatParticipant) -> Tuple[int, bool, bool]:
        """
        데미지 계산

        Returns:
            Tuple[int, bool, bool]: (데미지, 명중여부, 크리티컬여부)
        """
        # 명중률 계산
        hit_chance = attacker.accuracy / 100.0
        is_hit = random.random() <= hit_chance

        if not is_hit:
            return 0, False, False

        # 크리티컬 확률 계산
        critical_chance = attacker.critical_chance / 100.0
        is_critical = random.random() <= critical_chance

        # 기본 데미지 계산
        base_damage = attacker.attack_power

        # 크리티컬 시 데미지 2배
        if is_critical:
            base_damage *= 2

        # 방어력 적용
        final_damage = max(1, base_damage - defender.defense)

        # 랜덤 변동 (±20%)
        variation = random.uniform(0.8, 1.2)
        final_damage = int(final_damage * variation)

        return final_damage, is_hit, is_critical


class AutoCombat:
    """자동 전투 인스턴스 (다중 전투 지원)"""

    def __init__(self, player: Player, monsters: List[Monster], room_id: str,
                 broadcast_callback: Optional[Callable] = None):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.room_id = room_id
        self.result = CombatResult.ONGOING
        self.state = CombatState.INITIALIZING
        self.turn_number = 0
        self.combat_log: List[CombatTurn] = []
        self.started_at = datetime.now()
        self.broadcast_callback = broadcast_callback

        # 전투 참여자 생성
        self.player_participant = self._create_player_participant(player)
        self.monster_participants = [self._create_monster_participant(monster) for monster in monsters]

        # 원본 객체 참조 유지 (경험치, 레벨업 등을 위해)
        self.player = player
        self.monsters = monsters

        # 턴 순서 (Initiative 순) - 플레이어 + 모든 몬스터
        self.turn_order: List[CombatParticipant] = []
        self.current_turn_index = 0

        # 턴 타이머 설정 (2초)
        self.turn_timeout = 2.0

        # 현재 타겟 (플레이어가 공격할 몬스터)
        self.current_target_index = 0

        monster_names = [monster.get_localized_name('ko') for monster in monsters]
        self.logger.info(f"다중 전투 생성: {player.username} vs {', '.join(monster_names)}")

    # 하위 호환성을 위한 생성자 (단일 몬스터)
    @classmethod
    def create_single_combat(cls, player: Player, monster: Monster, room_id: str,
                           broadcast_callback: Optional[Callable] = None):
        """단일 몬스터와의 전투 생성 (하위 호환성)"""
        return cls(player, [monster], room_id, broadcast_callback)

    @property
    def monster_participant(self):
        """하위 호환성을 위한 속성 (첫 번째 몬스터 반환)"""
        return self.monster_participants[0] if self.monster_participants else None

    @property
    def monster(self):
        """하위 호환성을 위한 속성 (첫 번째 몬스터 반환)"""
        return self.monsters[0] if self.monsters else None

    async def start_auto_combat(self) -> None:
        """자동 전투 시작"""
        try:
            # 1. Initiative 계산
            await self._roll_initiative()

            # 2. 전투 루프 시작
            await self._combat_loop()

        except asyncio.CancelledError:
            self.logger.info(f"전투 취소됨: {self.room_id}")
            raise
        except Exception as e:
            self.logger.error(f"전투 중 오류 발생: {e}")
            self.result = CombatResult.DRAW
            self.state = CombatState.COMBAT_ENDED

    async def _roll_initiative(self) -> None:
        """Initiative 계산 및 턴 순서 결정 (다중 전투 지원)"""
        self.state = CombatState.ROLLING_INITIATIVE

        # 모든 참여자의 Initiative 계산
        player_init = self.player_participant.roll_initiative()
        monster_inits = []

        for monster_participant in self.monster_participants:
            monster_init = monster_participant.roll_initiative()
            monster_inits.append(monster_init)

        # 턴 순서 결정 (높은 Initiative 순)
        participants = [self.player_participant] + self.monster_participants
        self.turn_order = sorted(participants, key=lambda p: p.initiative, reverse=True)

        # 브로드캐스트 메시지 생성
        monster_init_info = []
        for i, monster_participant in enumerate(self.monster_participants):
            monster_init_info.append(f"{monster_participant.name}({monster_inits[i]})")

        init_message = (
            f"⚔️ 다중 전투 시작!\n"
            f"Initiative: {self.player_participant.name}({player_init}) vs {', '.join(monster_init_info)}\n"
            f"턴 순서: {' → '.join([p.name for p in self.turn_order])}"
        )

        await self._broadcast_message(init_message, CombatMessageType.COMBAT_START)

        self.logger.info(f"다중 전투 Initiative 계산 완료: {self.player_participant.name}({player_init}) vs {', '.join(monster_init_info)}")

    async def _combat_loop(self) -> None:
        """자동 전투 메인 루프"""
        while self.result == CombatResult.ONGOING:
            # 현재 턴 참여자
            current_participant = self.turn_order[self.current_turn_index]

            self.state = CombatState.WAITING_FOR_ACTION

            # 액션 결정
            if current_participant.participant_type == "player":
                action = await self._get_player_action(current_participant)
            else:
                action = self._get_monster_action()

            # 턴 처리
            self.state = CombatState.PROCESSING_TURN
            await self._process_turn(current_participant, action)

            # 전투 종료 조건 확인
            if not self.player_participant.is_alive():
                self.result = CombatResult.MONSTER_VICTORY
                await self._handle_defeat()
                break
            elif all(not monster.is_alive() for monster in self.monster_participants):
                # 모든 몬스터가 죽었을 때 승리
                self.result = CombatResult.PLAYER_VICTORY
                await self._handle_victory()
                break
            else:
                # 죽은 몬스터들을 턴 순서에서 제거
                self.turn_order = [p for p in self.turn_order if p.is_alive()]
                # 현재 턴 인덱스 조정
                if self.current_turn_index >= len(self.turn_order):
                    self.current_turn_index = 0

            # 다음 턴으로
            self.current_turn_index = (self.current_turn_index + 1) % len(self.turn_order)

            # 턴 간 짧은 대기
            await asyncio.sleep(0.5)

        self.state = CombatState.COMBAT_ENDED

    async def _get_player_action(self, participant: CombatParticipant) -> CombatAction:
        """플레이어 액션 대기 (타이머 포함)"""
        # 대기 중인 액션이 있으면 사용
        if participant.pending_action:
            action = participant.pending_action
            participant.pending_action = None
            return action

        # 액션 선택 요청 브로드캐스트
        await self._broadcast_message(
            f"🎯 {participant.name}의 턴입니다! ({self.turn_timeout}초 내에 액션을 선택하세요)\n"
            f"사용 가능한 명령어: attack, defend, flee",
            CombatMessageType.TURN_START
        )

        # 타이머 시작
        try:
            await asyncio.wait_for(
                self._wait_for_player_action(participant),
                timeout=self.turn_timeout
            )
        except asyncio.TimeoutError:
            # 시간 초과 시 기본 공격
            await self._broadcast_message(f"⏰ {participant.name}의 시간이 초과되어 자동으로 공격합니다!")
            return CombatAction.ATTACK

        # 액션 반환
        action = participant.pending_action or CombatAction.ATTACK
        participant.pending_action = None
        return action

    async def _wait_for_player_action(self, participant: CombatParticipant) -> None:
        """플레이어 액션 대기"""
        while participant.pending_action is None:
            await asyncio.sleep(0.1)

    async def _process_turn(self, attacker: CombatParticipant, action: CombatAction) -> None:
        """턴 처리 (다중 전투 지원)"""
        self.turn_number += 1

        # 타겟 결정
        if attacker.participant_type == "player":
            # 플레이어의 경우 현재 타겟 몬스터 선택
            alive_monsters = [m for m in self.monster_participants if m.is_alive()]
            if not alive_monsters:
                return  # 살아있는 몬스터가 없으면 턴 종료

            # 현재 타겟이 죽었거나 인덱스가 범위를 벗어나면 첫 번째 살아있는 몬스터로 변경
            if (self.current_target_index >= len(alive_monsters) or
                not alive_monsters[self.current_target_index].is_alive()):
                self.current_target_index = 0

            defender = alive_monsters[self.current_target_index]
        else:
            # 몬스터의 경우 항상 플레이어를 공격
            defender = self.player_participant

        # 턴 생성
        turn = CombatTurn(
            turn_number=self.turn_number,
            attacker_id=attacker.id,
            attacker_type=attacker.participant_type,
            action=action,
            target_id=defender.id
        )

        # 액션 처리
        if action == CombatAction.ATTACK:
            damage, is_hit, is_critical = self._calculate_damage(attacker, defender)

            if is_hit:
                actual_damage = defender.take_damage(damage)
                turn.damage_dealt = actual_damage
                turn.is_hit = True
                turn.is_critical = is_critical

                if is_critical:
                    turn.message = f"💥 {attacker.name}이(가) {defender.name}에게 치명타로 {actual_damage} 데미지를 입혔습니다!"
                else:
                    turn.message = f"⚔️ {attacker.name}이(가) {defender.name}에게 {actual_damage} 데미지를 입혔습니다."
            else:
                turn.is_hit = False
                turn.message = f"💨 {attacker.name}의 공격이 빗나갔습니다!"

        elif action == CombatAction.DEFEND:
            attacker.is_defending = True
            turn.message = f"🛡️ {attacker.name}이(가) 방어 자세를 취했습니다."

        elif action == CombatAction.FLEE:
            if attacker.participant_type == "player":
                flee_success = self._calculate_flee_success()
                if flee_success:
                    self.result = CombatResult.PLAYER_FLED
                    turn.message = f"💨 {attacker.name}이(가) 성공적으로 도망쳤습니다!"
                else:
                    turn.message = f"💨 {attacker.name}이(가) 도망치려 했지만 실패했습니다!"
            else:
                turn.message = f"💨 {attacker.name}이(가) 도망치려 합니다!"

        # 로그 추가
        self.combat_log.append(turn)

        # 턴 결과 브로드캐스트
        status_message = (
            f"{turn.message}\n"
            f"💚 {self.player_participant.name}: {self.player_participant.current_hp}/{self.player_participant.max_hp} HP\n"
            f"👹 {self.monster_participant.name}: {self.monster_participant.current_hp}/{self.monster_participant.max_hp} HP"
        )
        await self._broadcast_message(status_message, CombatMessageType.ACTION_RESULT)

    async def _broadcast_message(self, message: str, message_type: CombatMessageType = CombatMessageType.COMBAT_MESSAGE) -> None:
        """메시지 브로드캐스트 (개선된 버전)"""
        if self.broadcast_callback:
            # 전투 상태 정보 포함
            combat_status = self.get_combat_status()
            await self.broadcast_callback(
                self.room_id,
                message,
                message_type.value,
                combat_status
            )
        else:
            self.logger.info(f"[전투 메시지] {message}")

    def _create_player_participant(self, player: Player) -> CombatParticipant:
        """플레이어 전투 참여자 생성"""
        stats = player.stats if player.stats else PlayerStats()

        return CombatParticipant(
            id=player.id,
            name=player.username,
            participant_type="player",
            max_hp=stats.get_secondary_stat(StatType.HP),
            current_hp=stats.get_secondary_stat(StatType.HP),  # 전투 시작 시 풀 HP
            attack_power=stats.get_secondary_stat(StatType.ATK),
            defense=stats.get_secondary_stat(StatType.DEF),
            speed=stats.get_secondary_stat(StatType.SPD),
            accuracy=80 + stats.get_primary_stat(StatType.DEX),  # 기본 80% + 민첩성
            critical_chance=5 + int(stats.get_primary_stat(StatType.DEX) * 0.2)  # 기본 5% + 민첩성 보너스
        )

    def _create_monster_participant(self, monster: Monster) -> CombatParticipant:
        """몬스터 전투 참여자 생성"""
        return CombatParticipant(
            id=monster.id,
            name=monster.get_localized_name('ko'),
            participant_type="monster",
            max_hp=monster.stats.max_hp,
            current_hp=monster.stats.current_hp,
            attack_power=monster.stats.attack_power,
            defense=monster.stats.defense,
            speed=monster.stats.speed,
            accuracy=monster.stats.accuracy,
            critical_chance=monster.stats.critical_chance
        )

    def set_player_action(self, action: CombatAction) -> bool:
        """플레이어 액션 설정"""
        if self.state != CombatState.WAITING_FOR_ACTION:
            return False

        # 현재 턴이 플레이어 턴인지 확인
        current_participant = self.turn_order[self.current_turn_index]
        if current_participant.participant_type != "player":
            return False

        current_participant.pending_action = action
        return True

    def _calculate_damage(self, attacker: CombatParticipant,
                        defender: CombatParticipant) -> Tuple[int, bool, bool]:
        """데미지 계산"""
        # 명중률 계산
        hit_chance = attacker.accuracy / 100.0
        is_hit = random.random() <= hit_chance

        if not is_hit:
            return 0, False, False

        # 크리티컬 확률 계산
        critical_chance = attacker.critical_chance / 100.0
        is_critical = random.random() <= critical_chance

        # 기본 데미지 계산
        base_damage = attacker.attack_power

        # 크리티컬 시 데미지 2배
        if is_critical:
            base_damage *= 2

        # 방어력 적용
        final_damage = max(1, base_damage - defender.defense)

        # 랜덤 변동 (±20%)
        variation = random.uniform(0.8, 1.2)
        final_damage = int(final_damage * variation)

        return final_damage, is_hit, is_critical

    def _get_monster_action(self) -> CombatAction:
        """몬스터 AI 액션 결정"""
        # 간단한 AI: 90% 확률로 공격, 10% 확률로 방어
        if random.random() < 0.9:
            return CombatAction.ATTACK
        else:
            return CombatAction.DEFEND

    def _calculate_flee_success(self) -> bool:
        """도망 성공률 계산"""
        # 플레이어 속도와 몬스터 속도 비교
        player_speed = self.player_participant.speed
        monster_speed = self.monster_participant.speed

        # 기본 50% + 속도 차이에 따른 보너스/페널티
        base_chance = 0.5
        speed_modifier = (player_speed - monster_speed) * 0.02  # 속도 차이 1당 2%

        flee_chance = base_chance + speed_modifier
        flee_chance = max(0.1, min(0.9, flee_chance))  # 10%~90% 제한

        return random.random() <= flee_chance

    async def _handle_victory(self) -> None:
        """승리 처리 (다중 전투 지원)"""
        # 모든 몬스터로부터 경험치 획득
        total_exp_gained = sum(monster.experience_reward for monster in self.monsters)
        monster_names = [monster.get_localized_name('ko') for monster in self.monsters]

        if len(self.monsters) == 1:
            victory_message = f"🎉 {self.player.username}이(가) {monster_names[0]}을(를) 처치했습니다!"
        else:
            victory_message = f"🎉 {self.player.username}이(가) {', '.join(monster_names)}을(를) 모두 처치했습니다!"

        if self.player.stats:
            leveled_up = self.player.stats.add_experience(total_exp_gained)
            victory_message += f"\n💫 총 경험치 {total_exp_gained} 획득!"

            if leveled_up:
                victory_message += f"\n🆙 레벨업! 현재 레벨: {self.player.stats.level}"
                self.logger.info(f"플레이어 {self.player.username} 레벨업! 현재 레벨: {self.player.stats.level}")

        # 모든 몬스터 사망 처리
        for monster in self.monsters:
            monster.die()

        await self._broadcast_message(victory_message, CombatMessageType.COMBAT_END)
        self.logger.info(f"다중 전투 승리: {self.player.username}이(가) {', '.join(monster_names)}을(를) 처치했습니다")

    async def _handle_defeat(self) -> None:
        """패배 처리 (다중 전투 지원)"""
        monster_names = [monster.get_localized_name('ko') for monster in self.monsters]

        if len(self.monsters) == 1:
            defeat_message = f"💀 {self.player.username}이(가) {monster_names[0]}에게 패배했습니다!"
        else:
            defeat_message = f"💀 {self.player.username}이(가) {', '.join(monster_names)}에게 패배했습니다!"

        await self._broadcast_message(defeat_message, CombatMessageType.COMBAT_END)
        self.logger.info(f"다중 전투 패배: {self.player.username}이(가) {', '.join(monster_names)}에게 패배했습니다")

    def get_combat_status(self) -> Dict[str, Any]:
        """전투 상태 정보 반환 (다중 전투 지원)"""
        current_participant = None
        if self.turn_order and self.current_turn_index < len(self.turn_order):
            current_participant = self.turn_order[self.current_turn_index]

        # 다중 몬스터 정보 생성
        monsters_info = []
        for monster_participant in self.monster_participants:
            monsters_info.append({
                'name': monster_participant.name,
                'hp': monster_participant.current_hp,
                'max_hp': monster_participant.max_hp,
                'hp_percentage': monster_participant.get_hp_percentage(),
                'initiative': monster_participant.initiative,
                'is_alive': monster_participant.is_alive()
            })

        return {
            'room_id': self.room_id,
            'result': self.result.value,
            'state': self.state.value,
            'turn_number': self.turn_number,
            'current_turn': current_participant.name if current_participant else None,
            'turn_timeout': self.turn_timeout,
            'current_target_index': self.current_target_index,
            'player': {
                'name': self.player_participant.name,
                'hp': self.player_participant.current_hp,
                'max_hp': self.player_participant.max_hp,
                'hp_percentage': self.player_participant.get_hp_percentage(),
                'initiative': self.player_participant.initiative
            },
            'monsters': monsters_info,
            # 하위 호환성을 위한 단일 몬스터 정보
            'monster': monsters_info[0] if monsters_info else None,
            'last_turn': self.combat_log[-1].message if self.combat_log else "",
            'is_ongoing': self.result == CombatResult.ONGOING
        }

    def get_combat_log(self) -> List[Dict[str, Any]]:
        """전투 로그 반환"""
        return [
            {
                'turn_number': turn.turn_number,
                'attacker': turn.attacker_id,
                'attacker_type': turn.attacker_type,
                'action': turn.action.value,
                'damage_dealt': turn.damage_dealt,
                'is_critical': turn.is_critical,
                'is_hit': turn.is_hit,
                'message': turn.message,
                'timestamp': turn.timestamp.isoformat()
            }
            for turn in self.combat_log
        ]