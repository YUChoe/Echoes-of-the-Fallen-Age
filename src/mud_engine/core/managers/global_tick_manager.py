# -*- coding: utf-8 -*-

import asyncio
import logging

from typing import TYPE_CHECKING
from ...commands.combat_commands import AttackCommand

if TYPE_CHECKING:
    from ..game_engine import GameEngine
from ...game.combat import CombatantType


logger = logging.getLogger(__name__)

class GlobalTickManager:
    """글로벌 Tick 매니저 - 3초간격 몹 턴"""

    def __init__(self, game_engine: 'GameEngine'):
        self.game_engine = game_engine
        self.session_manager = self.game_engine.session_manager
        self.combat_handler = self.game_engine.combat_handler
        self._running: bool = False
        logger.info("GlobalTickManager 초기화 완료")

    async def start(self):
        """스케줄러 시작"""
        if self._running:
            logger.warning("GlobalTickManager 이미 실행 중입니다")
            return

        self._running = True
        self._tasks = []
        self._loop = asyncio.create_task(self._scheduler_loop())
        logger.info("글로벌 Tick 매니저 시작 완료")

    async def _scheduler_loop(self):
        while self._running:
            logger.debug(f"GlobalTickManager _running[{self._running}]")

            new_task = asyncio.create_task(self._worker())
            self._tasks.append(new_task)

            await asyncio.sleep(3)

            # 완료된 태스크 정리
            self._tasks = [t for t in self._tasks if t and not t.done()]

            if not self._running:
                break

    async def stop(self):
        self._running = False
        if self._loop and not self._loop.done():
            self._loop.cancel()
            try:
                await self._loop
            except asyncio.CancelledError:
                pass

        for t in self._tasks:
            if t and not t.done(): t.cancle()

        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        logger.info("글로벌 Tick 매니저 중지 완료")

    async def _worker(self):
        # 스태미나 회복 (모든 세션, 3초마다 +0.5)
        for s in self.session_manager.get_all_sessions():
            if hasattr(s, 'stamina') and hasattr(s, 'max_stamina'):
                if s.stamina < s.max_stamina:
                    s.stamina = min(s.stamina + 0.5, s.max_stamina)

        try:
            for s in self.session_manager.get_all_sessions():
                logger.debug(f"session_id[{s.session_id}]")
                if not s.in_combat: continue
                logger.info(f"몹턴 session_id[{s.session_id[-12:]}] in_combat True session.combat_id[{s.combat_id[-12:]}]")
                # 배틀 객체 가져오기
                _combats = self.combat_handler.active_combats
                for cid in _combats:  # 이 루프는 세션 갯수만큼 반복 됨.. 으음..
                    if cid == s.combat_id:
                        _combat_instancese = _combats[cid]
                        combatant = _combat_instancese.get_current_combatant()  # 현재 누구 턴
                        if combatant.combatant_type == CombatantType.MONSTER:
                            logger.info(f"몹 턴 combatant is [{combatant.combatant_type}]")
                            await self._process_monster_turn(cid)
                            # 전투 종료 확인
                            if _combat_instancese.is_combat_over():
                                acmd = AttackCommand(_combats)
                                await acmd._end_combat(s, _combat_instancese, {})
                        break  # 해당 세션에 대한 combat_id 를 찾으려는 것이므로 찾았으면 break
        except asyncio.CancelledError:
            logger.info("Worker 태스크 취소됨 - 전투중 몹턴")
            # 정리 작업 수행
            raise  # 반드시 re-raise
        # ===== ===== ===== ===== ===== =====
        try:
            locale = 'en' # 서버내부처리를 위해서는 디폴트 값 이용
            for s in self.session_manager.get_all_sessions():
                logger.debug(f"session_id[{s.session_id}]")
                if s.in_combat: continue
                room_info = await self.game_engine.get_room_info(s.current_room_id, locale)
                if not room_info or not room_info.get('monsters'):
                    return
                aggressive_monsters = []
                for monster in room_info['monsters']:
                    logger.info(f"몬스터 체크: {monster.get_localized_name(locale)}, 타입: {monster.monster_type}, 선공형: {monster.is_aggressive()}, 살아있음: {monster.is_alive}")
                    # 선공형이고 살아있는 몬스터만
                    if monster.is_aggressive() and monster.is_alive:
                        aggressive_monsters.append(monster)
                        logger.info(f"선공형 몬스터 발견: {monster.get_localized_name(locale)}")
                if not aggressive_monsters:
                    logger.info(f"방 {s.current_room_id[-12:]}에 선공형 몬스터 없음")
                    return
                logger.info(f"선공몹({len(aggressive_monsters)}개) action {aggressive_monsters[0].get_localized_name('en')}")
                # TODO: 선공형몹이 플레이어를 발견했습니다 메시지
                # 인스턴스 확인 및 생성
                combat = await self.combat_handler.start_combat(s.player, aggressive_monsters[0], s.current_room_id, aggresive=True)

                # 인스턴스에 엔티티 기록
                combat.set_entity_map(getattr(s, "room_entity_map", {}))

                # 세션 상태 업데이트
                s.in_combat = True
                s.original_room_id =s.current_room_id
                s.combat_id = combat.id
                s.current_room_id = f"combat_{combat.id}"  # 전투 인스턴스로 이동
                logger.debug(s)

                # 만약 몹 턴이면 공격
                combatant = combat.get_current_combatant()  # 현재 누구 턴
                if combatant.combatant_type == CombatantType.MONSTER:
                    logger.info(f"몹 턴 combatant is [{combatant.combatant_type}]")
                    await self._process_monster_turn(combat.id)
                    # 전투 종료 확인
                    if combat.is_combat_over():
                        acmd = AttackCommand(_combats)
                        await acmd._end_combat(s, _combat_instancese, {})

        except asyncio.CancelledError:
            logger.info("Worker 태스크 취소됨 - 몹 선공")
            # 정리 작업 수행
            raise  # 반드시 re-raise

    async def _process_monster_turn(self, combat_id):
        await self.combat_handler.process_monster_turn(combat_id)
        logger.debug("process_monster_turn finished")
