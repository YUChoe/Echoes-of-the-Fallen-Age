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
            # 실제 작업 수행
            # TODO:
            #   - [X] 현재 전투중인 세션을 찾는다
            #   - [ ] 각 세션 중에 몹 턴이면 몹턴을 실행하고 턴을 넘긴다
            #   - [ ] 몹/플레이어가 죽었으면 corpse 를 container 로 떨군다. << 이건 여기서 할게 아니라 attack 에서 할 일인 듯
            #   - [ ] 전투가 종료 되었는지 (한쪽편이 모두 전멸 했는지) 찾아서 인스턴스를 종료 시킨다.
            # 어우 졸려 피곤해

            for s in self.session_manager.get_all_sessions():
                logger.info(f"session_id[{s.session_id}]")
                if s.in_combat == True:
                    logger.info(f"session_id[{s.session_id}] in_combat True session.combat_id[{s.combat_id}]")
                    # 배틀 객체 가져오기
                    _combats = self.combat_handler.active_combats
                    logger.info(_combats)
                    for cid in _combats:  # 이 루프는 세션 갯수만큼 반복 됨.. 으음..
                        logger.info(f"cid[{cid}]")
                        if cid == s.combat_id:
                            _combat_instancese = _combats[cid]
                            combatant = _combat_instancese.get_current_combatant()  # 현재 턴 플레이어/몹
                            logger.info(f"Found combatant is [{combatant.combatant_type}]")
                            if combatant.combatant_type == CombatantType.MONSTER:  # 이거 어서 참조 하는디?
                                logger.info("몹 턴")
                                await self._process_monster_turn(cid)
                            break  # 해당 세션에 대한 combat_id 를 찾으려는 것이므로 찾았으면 break


        except asyncio.CancelledError:
            logger.info("Worker 태스크 취소됨")
            # 정리 작업 수행
            raise  # 반드시 re-raise

    async def _process_monster_turn(self, combat_id):
        # monster_result =
        await self.combat_handler.process_monster_turn(combat_id)
        # 안에서
        # - _execute_attack
        # - session.send_message 브로드캐스트
        # - # 다음 턴으로 진행 combat.advance_turn()
        # 다 하면 끝?