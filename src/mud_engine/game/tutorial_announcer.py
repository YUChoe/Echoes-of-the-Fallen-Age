# -*- coding: utf-8 -*-
"""튜토리얼 안내 시스템"""

import asyncio
import logging
from typing import TYPE_CHECKING, Dict
from datetime import datetime, timedelta

if TYPE_CHECKING:
    from ..core.game_engine import GameEngine

logger = logging.getLogger(__name__)


class TutorialAnnouncer:
    """튜토리얼 안내 시스템"""

    def __init__(self, game_engine: 'GameEngine'):
        self.game_engine = game_engine
        self.last_announcement: Dict[str, datetime] = {}  # 플레이어별 마지막 안내 시간
        self.announcement_interval = 300  # 5분 간격
        self.running = False

    async def start(self):
        """안내 시스템 시작"""
        if self.running:
            return

        self.running = True
        logger.info("튜토리얼 안내 시스템 시작")

        # 백그라운드 태스크로 실행
        asyncio.create_task(self._announcement_loop())

    async def stop(self):
        """안내 시스템 중지"""
        self.running = False
        logger.info("튜토리얼 안내 시스템 중지")

    async def _announcement_loop(self):
        """안내 루프"""
        while self.running:
            try:
                await self._check_and_announce()
                await asyncio.sleep(60)  # 1분마다 체크
            except Exception as e:
                logger.error(f"튜토리얼 안내 루프 오류: {e}")
                await asyncio.sleep(60)

    async def _check_and_announce(self):
        """신입 플레이어 체크 및 안내"""
        try:
            # 마을 광장에 있는 플레이어들 확인
            town_square_sessions = []

            for session in self.game_engine.session_manager.get_authenticated_sessions():
                if (session.player and
                    getattr(session, 'current_room_id', None) == 'town_square'):
                    town_square_sessions.append(session)

            if not town_square_sessions:
                return

            # 신입 플레이어 (튜토리얼 퀘스트 미완료) 찾기
            new_players = []
            for session in town_square_sessions:
                if self._is_new_player(session):
                    # 마지막 안내 시간 체크
                    player_id = session.player.id
                    last_time = self.last_announcement.get(player_id)

                    if (not last_time or
                        datetime.now() - last_time > timedelta(seconds=self.announcement_interval)):
                        new_players.append(session)

            if not new_players:
                return

            # 안내 메시지 전송
            await self._send_tutorial_announcement(town_square_sessions, new_players)

            # 안내 시간 업데이트
            current_time = datetime.now()
            for session in new_players:
                self.last_announcement[session.player.id] = current_time

        except Exception as e:
            logger.error(f"튜토리얼 안내 체크 실패: {e}")

    def _is_new_player(self, session) -> bool:
        """신입 플레이어 여부 확인"""
        try:
            # 튜토리얼 퀘스트 완료 여부 확인
            completed_quests = getattr(session.player, 'completed_quests', [])
            return 'tutorial_basic_equipment' not in completed_quests
        except:
            return True

    async def _send_tutorial_announcement(self, all_sessions, new_player_sessions):
        """튜토리얼 안내 메시지 전송"""
        try:
            # 신입 플레이어 이름 목록
            new_player_names = [session.player.username for session in new_player_sessions]

            if len(new_player_names) == 1:
                target_text_ko = f"{new_player_names[0]}님"
                target_text_en = f"{new_player_names[0]}"
            else:
                target_text_ko = "신입 모험가들"
                target_text_en = "new adventurers"

            # 모든 플레이어에게 안내 메시지 (언어별)
            for session in all_sessions:
                locale = session.player.preferred_locale if session.player else "en"

                if locale == "ko":
                    announcement = f"""
🏛️ 광장 경비병이 외칩니다:

"{target_text_ko}! 새로 오신 모험가시군요.
동쪽 교회로 가서 수도사님께 기본 장비를 받아가세요.
모험을 시작하기 전에 꼭 필요한 준비물들을 주실 겁니다!"

💡 힌트: 'east' 또는 'go east' 명령어로 교회로 갈 수 있습니다.
"""
                else:
                    announcement = f"""
🏛️ A town guard shouts:

"{target_text_en}! You look like new adventurers.
Go east to the church and receive basic equipment from the monk.
He will give you essential supplies before you start your adventure!"

💡 Hint: Use 'east' or 'go east' command to go to the church.
"""

                await session.send_message({
                    "type": "tutorial_announcement",
                    "message": announcement.strip()
                })

            logger.info(f"튜토리얼 안내 전송: {len(new_player_sessions)}명의 신입 플레이어")

        except Exception as e:
            logger.error(f"튜토리얼 안내 메시지 전송 실패: {e}")


# 전역 인스턴스
_tutorial_announcer = None


def get_tutorial_announcer(game_engine: 'GameEngine') -> TutorialAnnouncer:
    """전역 튜토리얼 안내자 인스턴스 반환"""
    global _tutorial_announcer
    if _tutorial_announcer is None:
        _tutorial_announcer = TutorialAnnouncer(game_engine)
    return _tutorial_announcer