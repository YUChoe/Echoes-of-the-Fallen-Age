# -*- coding: utf-8 -*-
"""플레이어 이동 관리자"""

import logging
from typing import TYPE_CHECKING, Optional, Any
from datetime import datetime

from ..event_bus import Event, EventType
from ..types import SessionType

if TYPE_CHECKING:
    from ..game_engine import GameEngine
    from ...game.combat import CombatInstance

logger = logging.getLogger(__name__)


class PlayerMovementManager:
    """플레이어 이동 및 따라가기 시스템을 담당하는 매니저"""

    def __init__(self, game_engine: 'GameEngine'):
        self.game_engine = game_engine

    async def move_player_to_room(self, session: SessionType, room_id: str, skip_followers: bool = False) -> bool:
        """
        플레이어를 특정 방으로 이동시킵니다.

        Args:
            session: 플레이어 세션
            room_id: 목적지 방 ID
            skip_followers: 따라가는 플레이어들 이동 생략 여부

        Returns:
            bool: 이동 성공 여부
        """
        if not session.is_authenticated or not session.player:
            return False

        try:
            logger.debug(f"플레이어 이동 시작: {session.player.username} -> {room_id}")

            # 방이 존재하는지 확인
            room = await self.game_engine.world_manager.get_room(room_id)
            if not room:
                logger.warning(f"존재하지 않는 방으로 이동 시도: {room_id} (플레이어: {session.player.username})")
                await session.send_error("존재하지 않는 방입니다.")
                return False

            # 이전 방 ID 저장
            old_room_id = getattr(session, 'current_room_id', None)

            # 세션의 현재 방 업데이트
            session.current_room_id = room_id

            # 방 퇴장 이벤트 발행 (이전 방이 있는 경우)
            if old_room_id:
                await self.game_engine.event_bus.publish(Event(
                    event_type=EventType.ROOM_LEFT,
                    source=session.session_id,
                    room_id=old_room_id,
                    data={
                        "player_id": session.player.id,
                        "username": session.player.username,
                        "session_id": session.session_id,
                        "old_room_id": old_room_id,
                        "new_room_id": room_id
                    }
                ))

            # 방 입장 이벤트 발행
            await self.game_engine.event_bus.publish(Event(
                event_type=EventType.ROOM_ENTERED,
                source=session.session_id,
                room_id=room_id,
                data={
                    "player_id": session.player.id,
                    "username": session.player.username,
                    "session_id": session.session_id,
                    "room_id": room_id,
                    "old_room_id": old_room_id
                }
            ))

            # 이전 방의 다른 플레이어들에게 퇴장 알림
            if old_room_id:
                leave_message = {
                    "type": "room_message",
                    "message": f"🚶 {session.player.get_display_name()}님이 떠났습니다.",
                    "timestamp": datetime.now().isoformat()
                }
                await self.game_engine.broadcast_to_room(old_room_id, leave_message, exclude_session=session.session_id)

            # 새 방의 다른 플레이어들에게 입장 알림
            enter_message = {
                "type": "room_message",
                "message": f"🚶 {session.player.get_display_name()}님이 도착했습니다.",
                "timestamp": datetime.now().isoformat()
            }
            await self.game_engine.broadcast_to_room(room_id, enter_message, exclude_session=session.session_id)

            # 따라가는 플레이어들도 함께 이동 - skip_followers가 False인 경우에만
            if not skip_followers:
                await self.handle_player_movement_with_followers(session, room_id, old_room_id)

            # 방 플레이어 목록 업데이트 (이전 방과 새 방 모두)
            if old_room_id:
                await self.update_room_player_list(old_room_id)
            await self.update_room_player_list(room_id)

            # 방 정보를 플레이어에게 전송 (follower든 아니든 항상 전송)
            await self.send_room_info_to_player(session, room_id)

            # 선공형 몬스터 체크 및 즉시 공격 처리
            await self._check_aggressive_monsters_on_entry(session, room_id)

            # 플레이어 좌표 업데이트
            await self._update_player_coordinates(session, room_id)

            logger.info(f"플레이어 {session.player.username}이 방 {room_id}로 이동")
            return True

        except Exception as e:
            logger.error(f"플레이어 방 이동 실패 ({session.player.username} -> {room_id}): {e}")
            await session.send_error("방 이동 중 오류가 발생했습니다.")
            return False

    async def send_room_info_to_player(self, session: SessionType, room_id: str) -> None:
        """
        플레이어에게 방 정보를 전송합니다.

        Args:
            session: 플레이어 세션
            room_id: 방 ID
        """
        try:
            room_info = await self.game_engine.get_room_info(room_id, session.locale)
            if room_info:
                # 디버깅: 몬스터 정보 로깅
                monsters = room_info.get('monsters', [])
                logger.debug(f"방 {room_id}에서 {len(monsters)}마리 몬스터 발견")
                for i, monster in enumerate(monsters):
                    logger.debug(f"몬스터 {i+1}: {monster.get_localized_name(session.locale)}, 타입: {monster.monster_type}, 행동: {monster.behavior}")
                
                # 세션에 엔티티 번호 매핑 저장
                entity_map = {}
                entity_index = 1
                
                # 몬스터 번호 매핑
                for monster in room_info.get('monsters', []):
                    entity_map[entity_index] = {
                        'type': 'monster',
                        'id': monster.id,
                        'name': monster.get_localized_name(session.locale),
                        'entity': monster
                    }
                    entity_index += 1
                
                # NPC 번호 매핑
                for npc in room_info.get('npcs', []):
                    entity_map[entity_index] = {
                        'type': 'npc',
                        'id': npc.id,
                        'name': npc.get_localized_name(session.locale),
                        'entity': npc
                    }
                    entity_index += 1
                
                # 세션에 저장
                session.room_entity_map = entity_map
                
                room_data = {
                    "id": room_info['room'].id,
                    "description": room_info['room'].get_localized_description(session.locale),
                    "exits": room_info['exits'],
                    "objects": [
                        {
                            "id": obj.id,
                            "name": obj.get_localized_name(session.locale),
                            "type": obj.object_type
                        }
                        for obj in room_info['objects']
                    ],
                    "monsters": [
                        {
                            "id": monster.id,
                            "name": monster.get_localized_name(session.locale),
                            "level": monster.level,
                            "current_hp": monster.current_hp,
                            "max_hp": monster.max_hp,
                            "faction_id": monster.faction_id,
                            "monster_type": monster.monster_type.value if hasattr(monster.monster_type, 'value') else str(monster.monster_type),
                            "behavior": monster.behavior.value if hasattr(monster.behavior, 'value') else str(monster.behavior),
                            "is_aggressive": monster.is_aggressive(),
                            "is_passive": monster.is_passive(),
                            "is_neutral": monster.is_neutral()
                        }
                        for monster in room_info.get('monsters', [])
                    ],
                    "npcs": [
                        {
                            "id": npc.id,
                            "name": npc.get_localized_name(session.locale),
                            "description": npc.get_localized_description(session.locale),
                            "npc_type": npc.npc_type,
                            "is_merchant": npc.is_merchant()
                        }
                        for npc in room_info.get('npcs', [])
                    ]
                }

                await session.send_message({
                    "type": "room_info",
                    "room": room_data,
                    "entity_map": entity_map
                })

                # UI 업데이트 정보 전송
                await self.game_engine.ui_manager.send_ui_update(session, room_info)

                logger.debug(f"방 정보 전송 완료: {session.player.username} -> 방 {room_id}")

        except Exception as e:
            logger.error(f"방 정보 전송 실패 ({session.player.username}, {room_id}): {e}")

    async def handle_player_movement_with_followers(self, session: SessionType, new_room_id: str, old_room_id: Optional[str] = None) -> None:
        """
        플레이어 이동 시 따라가는 플레이어들도 함께 이동시킵니다.

        Args:
            session: 이동하는 플레이어의 세션
            new_room_id: 새로운 방 ID
            old_room_id: 이전 방 ID (따라가는 플레이어들을 찾기 위해 필요)
        """
        if not session.player or not old_room_id:
            return

        # 이 플레이어를 따라가는 다른 플레이어들 찾기 (이전 방에서)
        followers = []

        for other_session in self.game_engine.session_manager.get_authenticated_sessions():
            if (other_session.player and
                other_session.session_id != session.session_id and
                getattr(other_session, 'current_room_id', None) == old_room_id and
                getattr(other_session, 'following_player', None) == session.player.username):
                followers.append(other_session)

        if followers:
            logger.info(f"따라가는 플레이어 {len(followers)}명 발견: {[f.player.username for f in followers]}")
        else:
            logger.debug(f"따라가는 플레이어 없음 (리더: {session.player.username}, 이전 방: {old_room_id})")

        # 따라가는 플레이어들을 함께 이동
        for follower_session in followers:
            try:
                # 따라가는 플레이어에게 알림
                await follower_session.send_message({
                    "type": "following_movement",
                    "message": f"👥 {session.player.username}님을 따라 이동합니다..."
                })

                # 실제 이동 수행 (무한 재귀 방지를 위해 skip_followers=True)
                success = await self.move_player_to_room(follower_session, new_room_id, skip_followers=True)

                if success:
                    # 이동 성공 시 follower에게 이동 완료 메시지 전송
                    await follower_session.send_message({
                        "type": "following_movement_complete",
                        "message": f"👥 {session.player.username}님을 따라 이동했습니다."
                    })

                    logger.info(f"따라가기 이동 완료: {follower_session.player.username} -> 방 {new_room_id}")
                else:
                    # 이동 실패 시 따라가기 중지
                    if hasattr(follower_session, 'following_player'):
                        delattr(follower_session, 'following_player')

                    await follower_session.send_error(
                        f"{session.player.username}님을 따라가지 못했습니다. 따라가기가 중지됩니다."
                    )

            except Exception as e:
                logger.error(f"따라가기 이동 실패 ({follower_session.player.username}): {e}")
                # 오류 시 따라가기 중지
                if hasattr(follower_session, 'following_player'):
                    delattr(follower_session, 'following_player')

    async def update_room_player_list(self, room_id: str) -> None:
        """
        방의 플레이어 목록을 실시간으로 업데이트합니다.

        Args:
            room_id: 업데이트할 방 ID
        """
        try:
            # 방에 있는 모든 플레이어들 찾기
            players_in_room = []
            for session in self.game_engine.session_manager.get_authenticated_sessions():
                if (session.player and
                    getattr(session, 'current_room_id', None) == room_id):

                    player_info = {
                        "id": session.player.id,
                        "name": session.player.username,
                        "session_id": session.session_id,
                        "following": getattr(session, 'following_player', None)
                    }
                    players_in_room.append(player_info)

            # 방에 있는 모든 플레이어들에게 업데이트된 목록 전송
            update_message = {
                "type": "room_players_update",
                "room_id": room_id,
                "players": players_in_room,
                "player_count": len(players_in_room)
            }

            await self.game_engine.broadcast_to_room(room_id, update_message)
            logger.debug(f"방 {room_id} 플레이어 목록 업데이트: {len(players_in_room)}명")

        except Exception as e:
            logger.error(f"방 플레이어 목록 업데이트 실패 ({room_id}): {e}")

    async def handle_player_disconnect_cleanup(self, session: SessionType) -> None:
        """
        플레이어 연결 해제 시 따라가기 및 전투 관련 정리 작업

        Args:
            session: 연결 해제된 플레이어의 세션
        """
        if not session.player:
            return

        try:
            disconnected_player = session.player.username

            # 전투 중이었다면 전투 종료 처리
            if getattr(session, 'in_combat', False):
                combat_id = getattr(session, 'combat_id', None)
                if combat_id:
                    combat = self.game_engine.combat_manager.get_combat(combat_id)
                    if combat and combat.is_active:
                        # 전투 인스턴스 종료
                        self.game_engine.combat_manager.end_combat(combat_id)
                        logger.info(f"플레이어 {disconnected_player} 연결 해제로 전투 {combat_id} 종료")
                
                # 전투 상태 초기화
                session.in_combat = False
                session.combat_id = None
                session.original_room_id = None

            # 이 플레이어를 따라가던 다른 플레이어들의 따라가기 해제
            for other_session in self.game_engine.session_manager.get_authenticated_sessions():
                if (other_session.player and
                    hasattr(other_session, 'following_player') and
                    other_session.following_player == disconnected_player):

                    # 따라가기 해제
                    delattr(other_session, 'following_player')

                    # 알림 전송
                    await other_session.send_message({
                        "type": "follow_stopped",
                        "message": f"👥 {disconnected_player}님이 연결을 해제하여 따라가기가 중지되었습니다.",
                        "reason": "player_disconnected"
                    })

            logger.info(f"플레이어 연결 해제 정리 완료: {disconnected_player}")

        except Exception as e:
            logger.error(f"플레이어 연결 해제 정리 실패: {e}")

    async def notify_player_status_change(self, player_id: str, status: str, data: dict = None) -> None:
        """
        플레이어 상태 변경을 다른 플레이어들에게 알립니다.

        Args:
            player_id: 상태가 변경된 플레이어 ID
            status: 상태 ('online', 'offline', 'busy', 'away' 등)
            data: 추가 데이터
        """
        try:
            # 상태 변경 이벤트 발행
            await self.game_engine.event_bus.publish(Event(
                event_type=EventType.PLAYER_STATUS_CHANGED,
                source=player_id,
                data={
                    "player_id": player_id,
                    "status": status,
                    "timestamp": datetime.now().isoformat(),
                    **(data or {})
                }
            ))

            # 전체 플레이어들에게 상태 변경 알림 (선택적)
            if status in ['online', 'offline']:
                player_session = None
                for session in self.game_engine.session_manager.get_authenticated_sessions():
                    if session.player and session.player.id == player_id:
                        player_session = session
                        break

                if player_session:
                    status_message = {
                        "type": "player_status_change",
                        "message": f"🔄 {player_session.player.username}님이 {status} 상태가 되었습니다.",
                        "player_name": player_session.player.username,
                        "status": status,
                        "timestamp": datetime.now().isoformat()
                    }

                    await self.game_engine.broadcast_to_all(status_message)

        except Exception as e:
            logger.error(f"플레이어 상태 변경 알림 실패 ({player_id}, {status}): {e}")

    async def _check_aggressive_monsters_on_entry(self, session: SessionType, room_id: str) -> None:
        """
        플레이어가 방에 입장할 때 선공형 몬스터 체크 및 즉시 공격 처리

        Args:
            session: 플레이어 세션
            room_id: 입장한 방 ID
        """
        try:
            logger.info(f"선공형 몬스터 체크 시작: 플레이어 {session.player.username}, 방 {room_id}")

            # 플레이어가 이미 전투 중인지 확인
            if self.game_engine.combat_manager.is_player_in_combat(session.player.id):
                logger.info(f"플레이어 {session.player.username}이 이미 전투 중이므로 선공 체크 생략")
                return

            # 방의 선공형 몬스터들 조회
            room_info = await self.game_engine.get_room_info(room_id, session.locale)
            if not room_info or not room_info.get('monsters'):
                return

            aggressive_monsters = []
            for monster in room_info['monsters']:
                logger.info(f"몬스터 체크: {monster.get_localized_name(session.locale)}, 타입: {monster.monster_type}, 선공형: {monster.is_aggressive()}, 살아있음: {monster.is_alive}")
                # 선공형이고 살아있는 몬스터만
                if monster.is_aggressive() and monster.is_alive:
                    aggressive_monsters.append(monster)
                    logger.info(f"선공형 몬스터 발견: {monster.get_localized_name(session.locale)}")

            if not aggressive_monsters:
                logger.info(f"방 {room_id}에 선공형 몬스터 없음")
                return

            # 첫 번째 선공형 몬스터가 공격 (우선순위: 레벨 높은 순)
            aggressive_monsters.sort(key=lambda m: m.level, reverse=True)
            attacking_monster = aggressive_monsters[0]

            logger.info(f"선공형 몬스터 {attacking_monster.get_localized_name(session.locale)}이 플레이어 {session.player.username}을 공격!")

            # 선공 메시지 브로드캐스트
            monster_name = attacking_monster.get_localized_name(session.locale)
            aggro_message = f"🔥 {monster_name}이(가) {session.player.username}을(를) 발견하고 공격합니다!"

            # 방에 있는 모든 플레이어에게 선공 메시지 전송
            await self.game_engine.broadcast_to_room(room_id, {
                'type': 'monster_aggro',
                'message': aggro_message,
                'monster_id': attacking_monster.id,
                'player_id': session.player.id,
                'timestamp': datetime.now().isoformat()
            })

            # 전투 시작
            combat = await self.game_engine.combat_handler.check_and_start_combat(
                room_id, session.player, session.player.id, aggressive_monsters
            )
            
            if combat:
                # 세션 전투 상태 업데이트
                session.in_combat = True
                session.combat_id = combat.id
                session.original_room_id = room_id
                session.current_room_id = f"combat_{combat.id}"
                
                logger.info(f"세션 전투 상태 업데이트: combat_id={combat.id}, in_combat={session.in_combat}")
                
                # 전투 시작 간단 알림 (전투 상태는 몬스터 턴 후 표시)
                combat_start_msg = f"⚔️ 전투 시작! {monster_name}이(가) 당신을 공격합니다!"
                await session.send_message({
                    'type': 'combat_start',
                    'message': combat_start_msg
                })
                
                # 몬스터 턴들을 자동으로 처리 (플레이어 턴까지)
                await self._process_monster_turns_until_player(combat, session)

            logger.info(f"선공형 몬스터 전투 시작: {monster_name} vs {session.player.username}")

        except Exception as e:
            logger.error(f"선공형 몬스터 체크 중 오류: {e}")
    
    async def _process_monster_turns_until_player(self, combat: Any, session: SessionType) -> None:
        """
        몬스터 턴들을 자동으로 처리하여 플레이어 턴까지 진행
        
        Args:
            combat: 전투 인스턴스
            session: 플레이어 세션
        """
        from ...game.combat import CombatantType
        
        try:
            max_iterations = 20  # 무한 루프 방지
            iterations = 0
            
            while combat.is_active and not combat.is_combat_over() and iterations < max_iterations:
                iterations += 1
                current = combat.get_current_combatant()
                
                if not current:
                    logger.warning("현재 턴 전투원을 찾을 수 없음")
                    break
                
                # 플레이어 턴이면 중단
                if current.combatant_type == CombatantType.PLAYER:
                    logger.info(f"플레이어 {session.player.username}의 턴 - 몬스터 턴 처리 완료")
                    
                    # 플레이어에게 턴 알림 전송 (포맷팅된 텍스트)
                    turn_msg = f"""
{self._format_combat_status(combat)}

🎯 당신의 턴입니다! 행동을 선택하세요:

1️⃣ attack  - 무기로 공격
2️⃣ defend  - 방어 자세 (다음 데미지 50% 감소)
3️⃣ flee    - 도망치기 (50% 확률)

명령어를 입력하세요:"""
                    await session.send_message({
                        'type': 'combat_your_turn',
                        'message': turn_msg.strip()
                    })
                    break
                
                # 몬스터 턴 처리
                logger.info(f"몬스터 {current.name}의 턴 자동 처리 중...")
                await self.game_engine.combat_handler.process_monster_turn(combat.id)
                
                # 전투 종료 확인
                if combat.is_combat_over():
                    logger.info("전투 종료됨")
                    await self._handle_combat_end(combat, session)
                    break
            
            if iterations >= max_iterations:
                logger.error(f"몬스터 턴 처리 무한 루프 감지 (combat_id: {combat.id})")
                
        except Exception as e:
            logger.error(f"몬스터 턴 자동 처리 중 오류: {e}", exc_info=True)
    
    async def _handle_combat_end(self, combat: Any, session: SessionType) -> None:
        """
        전투 종료 처리
        
        Args:
            combat: 전투 인스턴스
            session: 플레이어 세션
        """
        from ...game.combat import CombatantType
        
        try:
            winners = combat.get_winners()
            player_won = any(w.combatant_type == CombatantType.PLAYER for w in winners)
            
            # 보상 계산 (승리 시)
            rewards: dict[str, Any] = {'experience': 0, 'gold': 0, 'items': []}
            if player_won:
                defeated_monsters = [c for c in combat.combatants if c.combatant_type != CombatantType.PLAYER and not c.is_alive()]
                for monster in defeated_monsters:
                    rewards['experience'] = rewards['experience'] + 50  # 기본 경험치
                    rewards['gold'] = rewards['gold'] + 10  # 기본 골드
            
            # 전투 종료 메시지
            if player_won:
                message = f"""
🎉 전투에서 승리했습니다!

💰 보상:
  - 경험치: {rewards['experience']}
  - 골드: {rewards['gold']}

원래 위치로 돌아갑니다...
"""
            else:
                message = "💀 전투에서 패배했습니다...\n\n원래 위치로 돌아갑니다..."
            
            await session.send_message({
                'type': 'combat_end',
                'message': message.strip(),
                'victory': player_won,
                'rewards': rewards
            })
            
            # 원래 방으로 복귀
            if session.original_room_id:
                session.current_room_id = session.original_room_id
            
            # 전투 상태 초기화
            session.in_combat = False
            session.original_room_id = None
            session.combat_id = None
            
            # 전투 종료
            self.game_engine.combat_manager.end_combat(combat.id)
            
            logger.info(f"전투 종료 처리 완료: combat_id={combat.id}, 승리={player_won}")
            
        except Exception as e:
            logger.error(f"전투 종료 처리 중 오류: {e}", exc_info=True)
    
    def _format_combat_status(self, combat: Any) -> str:
        """
        전투 상태를 포맷팅된 텍스트로 변환
        
        Args:
            combat: 전투 인스턴스
        
        Returns:
            str: 포맷팅된 전투 상태 텍스트
        """
        from ...game.combat import CombatantType
        
        lines = ["━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"]
        lines.append(f"⚔️ 전투 라운드 {combat.turn_number}")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        # 플레이어 정보
        players = [c for c in combat.combatants if c.combatant_type == CombatantType.PLAYER and c.is_alive()]
        if players:
            player = players[0]
            hp_bar = self._get_hp_bar(player.current_hp, player.max_hp)
            lines.append(f"\n👤 {player.name}")
            lines.append(f"   HP: {hp_bar} {player.current_hp}/{player.max_hp}")
        
        # 몬스터 정보
        monsters = [c for c in combat.combatants if c.combatant_type == CombatantType.MONSTER and c.is_alive()]
        if monsters:
            lines.append("\n👹 몬스터:")
            for monster in monsters:
                hp_bar = self._get_hp_bar(monster.current_hp, monster.max_hp)
                lines.append(f"   • {monster.name}")
                lines.append(f"     HP: {hp_bar} {monster.current_hp}/{monster.max_hp}")
        
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        return "\n".join(lines)
    
    def _get_hp_bar(self, current: int, maximum: int, length: int = 10) -> str:
        """
        HP 바 생성
        
        Args:
            current: 현재 HP
            maximum: 최대 HP
            length: 바 길이
        
        Returns:
            str: HP 바 문자열
        """
        if maximum <= 0:
            return "[" + "░" * length + "]"
        
        filled = int((current / maximum) * length)
        empty = length - filled
        
        return "[" + "█" * filled + "░" * empty + "]"

    async def _update_player_coordinates(self, session: SessionType, room_id: str) -> None:
        """
        플레이어의 좌표를 업데이트합니다.
        room_id에서 좌표를 추출하여 데이터베이스에 저장합니다.

        Args:
            session: 플레이어 세션
            room_id: 방 ID (예: forest_5_7, town_square)
        """
        try:
            # room_id에서 좌표 추출
            x, y = self._extract_coordinates_from_room_id(room_id)
            
            if x is not None and y is not None:
                # 플레이어 객체 업데이트
                session.player.last_room_x = x
                session.player.last_room_y = y
                
                # 데이터베이스 업데이트
                from ...game.repositories import PlayerRepository
                from ...database import get_database_manager
                
                db_manager = await get_database_manager()
                player_repo = PlayerRepository(db_manager)
                
                update_data = {
                    'last_room_id': room_id,
                    'last_room_x': x,
                    'last_room_y': y
                }
                await player_repo.update(session.player.id, update_data)
                
                logger.debug(f"플레이어 {session.player.username} 좌표 업데이트: ({x}, {y})")
            else:
                # 좌표를 추출할 수 없는 경우 room_id만 업데이트
                from ...game.repositories import PlayerRepository
                from ...database import get_database_manager
                
                db_manager = await get_database_manager()
                player_repo = PlayerRepository(db_manager)
                
                update_data = {'last_room_id': room_id}
                await player_repo.update(session.player.id, update_data)
                
                logger.debug(f"플레이어 {session.player.username} room_id만 업데이트: {room_id}")
                
        except Exception as e:
            logger.error(f"플레이어 좌표 업데이트 실패: {e}")

    def _extract_coordinates_from_room_id(self, room_id: str) -> tuple[int | None, int | None]:
        """
        room_id에서 좌표를 추출합니다.
        
        Args:
            room_id: 방 ID (예: forest_5_7, town_square)
            
        Returns:
            tuple: (x, y) 좌표, 추출 실패 시 (None, None)
        """
        try:
            # room_id 형식: prefix_x_y (예: forest_5_7)
            parts = room_id.split('_')
            
            if len(parts) >= 3:
                # 마지막 두 부분이 숫자인지 확인
                try:
                    x = int(parts[-2])
                    y = int(parts[-1])
                    return (x, y)
                except ValueError:
                    pass
            
            # 좌표를 추출할 수 없는 경우
            return (None, None)
            
        except Exception as e:
            logger.error(f"좌표 추출 실패 ({room_id}): {e}")
            return (None, None)
