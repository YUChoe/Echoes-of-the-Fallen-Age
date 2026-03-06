# -*- coding: utf-8 -*-

import asyncio
import logging

from typing import TYPE_CHECKING

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
        try:
            for s in self.session_manager.get_all_sessions():
                logger.debug(f"session_id[{s.session_id}]")
                if not s.in_combat: continue
                logger.info(f"session_id[{s.session_id}] in_combat True session.combat_id[{s.combat_id}]")
                # 배틀 객체 가져오기
                _combats = self.combat_handler.active_combats
                for cid in _combats:  # 이 루프는 세션 갯수만큼 반복 됨.. 으음..
                    logger.info(f"cid[{cid}]")
                    if cid == s.combat_id:
                        _combat_instancese = _combats[cid]
                        combatant = _combat_instancese.get_current_combatant()  # 현재 누구 턴
                        if combatant.combatant_type == CombatantType.MONSTER:
                            logger.info(f"몹 턴 combatant is [{combatant.combatant_type}]")
                            await self._process_monster_turn(cid)
                        break  # 해당 세션에 대한 combat_id 를 찾으려는 것이므로 찾았으면 break


        except asyncio.CancelledError:
            logger.info("Worker 태스크 취소됨")
            # 정리 작업 수행
            raise  # 반드시 re-raise

    async def _process_monster_turn(self, combat_id):
        await self.combat_handler.process_monster_turn(combat_id)
# 아 깔끔하다 역시 내 코드