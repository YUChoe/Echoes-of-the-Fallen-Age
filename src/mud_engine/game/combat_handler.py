"""
전투 핸들러 - 전투 시작, 턴 처리, 종료 로직
"""

import logging
import random
from typing import Optional, List, Dict, Any

from .combat import CombatManager, CombatInstance, CombatAction, CombatTurn, Combatant
from .monster import Monster, MonsterType
from .models import Player

logger = logging.getLogger(__name__)


class CombatHandler:
    """전투 핸들러 - 전투 로직 처리"""
    
    def __init__(self, combat_manager: CombatManager):
        """전투 핸들러 초기화"""
        self.combat_manager = combat_manager
        logger.info("CombatHandler 초기화 완료")
    
    async def check_and_start_combat(
        self,
        room_id: str,
        player: Player,
        player_id: str,
        monsters: List[Monster]
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
            m for m in monsters
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
                existing_combat.id,
                player,
                player_id
            )
            if success:
                logger.info(f"플레이어 {player_id}를 기존 전투 {existing_combat.id}에 추가")
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
        target_id: Optional[str] = None
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
                'success': False,
                'message': '전투를 찾을 수 없거나 이미 종료되었습니다.'
            }
        
        # 현재 턴인지 확인
        current_combatant = combat.get_current_combatant()
        if not current_combatant or current_combatant.id != player_id:
            return {
                'success': False,
                'message': '당신의 턴이 아닙니다.'
            }
        
        # 행동 처리
        result = await self._execute_action(combat, current_combatant, action, target_id)
        
        # 턴 로그 추가
        turn = CombatTurn(
            turn_number=combat.turn_number,
            combatant_id=player_id,
            action=action,
            target_id=target_id,
            damage_dealt=result.get('damage_dealt', 0),
            damage_received=result.get('damage_received', 0),
            message=result.get('message', '')
        )
        combat.add_combat_log(turn)
        
        # 다음 턴으로 진행
        combat.advance_turn()
        
        # 전투 종료 확인
        if combat.is_combat_over():
            rewards = await self._end_combat(combat)
            result['combat_over'] = True
            result['winners'] = [c.to_dict() for c in combat.get_winners()]
            result['rewards'] = rewards
        
        return result
    
    async def _execute_action(
        self,
        combat: CombatInstance,
        actor: Combatant,
        action: CombatAction,
        target_id: Optional[str]
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
            return {
                'success': False,
                'message': '알 수 없는 행동입니다.'
            }
    
    async def _execute_attack(
        self,
        combat: CombatInstance,
        actor: Combatant,
        target_id: Optional[str]
    ) -> Dict[str, Any]:
        """공격 실행"""
        if not target_id:
            return {
                'success': False,
                'message': '공격 대상을 지정해야 합니다.'
            }
        
        target = combat.get_combatant(target_id)
        if not target:
            return {
                'success': False,
                'message': '대상을 찾을 수 없습니다.'
            }
        
        if not target.is_alive():
            return {
                'success': False,
                'message': '이미 사망한 대상입니다.'
            }
        
        # 데미지 계산
        base_damage = actor.attack_power
        # 랜덤 요소 추가 (80% ~ 120%)
        damage_multiplier = random.uniform(0.8, 1.2)
        damage = int(base_damage * damage_multiplier)
        
        # 크리티컬 확률 (10%)
        is_critical = random.random() < 0.1
        if is_critical:
            damage = int(damage * 1.5)
        
        # 대상에게 데미지 적용
        actual_damage = target.take_damage(damage)
        
        # 방어 상태 해제
        actor.is_defending = False
        
        message = f"{actor.name}이(가) {target.name}을(를) 공격하여 {actual_damage} 데미지를 입혔습니다."
        if is_critical:
            message += " (크리티컬!)"
        
        if not target.is_alive():
            message += f" {target.name}이(가) 쓰러졌습니다!"
        
        return {
            'success': True,
            'message': message,
            'damage_dealt': actual_damage,
            'is_critical': is_critical,
            'target_hp': target.current_hp,
            'target_max_hp': target.max_hp
        }
    
    async def _execute_defend(self, actor: Combatant) -> Dict[str, Any]:
        """방어 실행"""
        actor.is_defending = True
        
        return {
            'success': True,
            'message': f"{actor.name}이(가) 방어 자세를 취했습니다. (다음 공격 데미지 50% 감소)"
        }
    
    async def _execute_flee(
        self,
        combat: CombatInstance,
        actor: Combatant
    ) -> Dict[str, Any]:
        """도망 실행"""
        # 도망 성공 확률 (50%)
        flee_chance = 0.5
        success = random.random() < flee_chance
        
        if success:
            # 전투에서 제거
            combat.remove_combatant(actor.id)
            
            return {
                'success': True,
                'message': f"{actor.name}이(가) 전투에서 도망쳤습니다!",
                'fled': True
            }
        else:
            return {
                'success': True,
                'message': f"{actor.name}이(가) 도망치려 했지만 실패했습니다!",
                'fled': False
            }
    
    async def _execute_wait(self, actor: Combatant) -> Dict[str, Any]:
        """대기 실행"""
        # 방어 상태 해제
        actor.is_defending = False
        
        return {
            'success': True,
            'message': f"{actor.name}이(가) 대기합니다."
        }
    
    async def process_monster_turn(self, combat_id: str) -> Dict[str, Any]:
        """몬스터 턴 처리 (AI)"""
        combat = self.combat_manager.get_combat(combat_id)
        if not combat or not combat.is_active:
            return {
                'success': False,
                'message': '전투를 찾을 수 없거나 이미 종료되었습니다.'
            }
        
        current_combatant = combat.get_current_combatant()
        if not current_combatant:
            return {
                'success': False,
                'message': '현재 턴의 참가자를 찾을 수 없습니다.'
            }
        
        # 몬스터 AI: 랜덤한 플레이어 공격
        alive_players = combat.get_alive_players()
        if not alive_players:
            return {
                'success': False,
                'message': '공격할 대상이 없습니다.'
            }
        
        target = random.choice(alive_players)
        
        # 공격 실행
        result = await self._execute_attack(combat, current_combatant, target.id)
        
        # 턴 로그 추가
        turn = CombatTurn(
            turn_number=combat.turn_number,
            combatant_id=current_combatant.id,
            action=CombatAction.ATTACK,
            target_id=target.id,
            damage_dealt=result.get('damage_dealt', 0),
            message=result.get('message', '')
        )
        combat.add_combat_log(turn)
        
        # 다음 턴으로 진행
        combat.advance_turn()
        
        # 전투 종료 확인
        if combat.is_combat_over():
            rewards = await self._end_combat(combat)
            result['combat_over'] = True
            result['winners'] = [c.to_dict() for c in combat.get_winners()]
            result['rewards'] = rewards
        
        return result
    
    async def _end_combat(self, combat: CombatInstance) -> Dict[str, Any]:
        """
        전투 종료 처리 및 보상 지급
        
        Returns:
            Dict: 전투 종료 결과 (보상 정보 포함)
        """
        winners = combat.get_winners()
        rewards: Dict[str, Any] = {
            'experience': 0,
            'gold': 0,
            'items': []
        }
        
        # 승리자 로그
        if winners:
            winner_names = [w.name for w in winners]
            logger.info(f"전투 {combat.id} 종료 - 승리자: {', '.join(winner_names)}")
            
            # 플레이어가 승리한 경우 보상 지급
            from .combat import CombatantType
            player_winners = [w for w in winners if w.combatant_type == CombatantType.PLAYER]
            
            if player_winners:
                # 처치한 몬스터들로부터 보상 계산
                defeated_monsters = combat.get_alive_monsters()  # 사망한 몬스터는 제외되므로 반대로 가져와야 함
                all_monsters = [c for c in combat.combatants if c.combatant_type != CombatantType.PLAYER]
                defeated_monsters = [m for m in all_monsters if not m.is_alive()]
                
                # 각 몬스터로부터 보상 수집
                for monster_combatant in defeated_monsters:
                    # 몬스터 ID로 실제 Monster 객체 찾기 (보상 정보 가져오기 위해)
                    # 여기서는 기본 보상만 지급 (나중에 Monster 객체 연동 필요)
                    rewards['experience'] += 50  # 기본 경험치
                    rewards['gold'] += 10  # 기본 골드
                
                logger.info(f"전투 보상: 경험치 {rewards['experience']}, 골드 {rewards['gold']}")
        else:
            logger.info(f"전투 {combat.id} 종료 - 무승부")
        
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
        self,
        player: Player,
        monster: Monster,
        room_id: str,
        broadcast_callback=None
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
        # 전투 인스턴스 생성
        combat = self.combat_manager.create_combat(room_id)
        
        # 플레이어 추가
        self.combat_manager.add_player_to_combat(combat.id, player, player.id)
        
        # 몬스터 추가
        self.combat_manager.add_monster_to_combat(combat.id, monster)
        
        logger.info(f"전투 시작: {player.username} vs {monster.get_localized_name('ko')}")
        
        return combat
    
    async def add_monsters_to_combat(
        self,
        player_id: str,
        monsters: List[Monster]
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
