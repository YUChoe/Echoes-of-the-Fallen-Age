# -*- coding: utf-8 -*-
"""Telnet 전용 세션 관리자"""

import logging
from typing import Dict, Optional, Any
from datetime import datetime

from .telnet_session import TelnetSession
from ..game.models import Player

logger = logging.getLogger(__name__)


class SessionManager:
    """Telnet 세션 관리자 (간소화 버전)"""

    def __init__(self):
        """SessionManager 초기화"""
        self.sessions: Dict[str, TelnetSession] = {}
        self.player_sessions: Dict[str, str] = {}  # player_id -> session_id 매핑
        logger.info("SessionManager 초기화 완료")

    def add_session(self, session: TelnetSession) -> None:
        """세션 추가

        Args:
            session: 추가할 세션
        """
        self.sessions[session.session_id] = session
        logger.debug(f"세션 추가: {session.session_id}")

    def remove_session(self, session_id: str) -> bool:
        """세션 제거

        Args:
            session_id: 제거할 세션 ID

        Returns:
            bool: 제거 성공 여부
        """
        session = self.sessions.get(session_id)
        if not session:
            return False

        # 플레이어 매핑 제거 (해당 세션 ID와 일치하는 경우만)
        if session.player and session.player.id in self.player_sessions:
            if self.player_sessions[session.player.id] == session_id:
                del self.player_sessions[session.player.id]
                logger.debug(f"플레이어 매핑 제거: {session.player.id} -> {session_id}")

        # 세션 제거
        del self.sessions[session_id]
        logger.debug(f"세션 제거: {session_id}")
        return True

    async def authenticate_session(self, session_id: str, player: Player) -> None:
        """세션 인증

        Args:
            session_id: 세션 ID
            player: 플레이어 객체
        """
        session = self.sessions.get(session_id)
        if not session:
            return

        # 기존 세션이 있는지 확인
        existing_session_id = self.player_sessions.get(player.id)
        if existing_session_id and existing_session_id != session_id:
            # 기존 세션 종료
            existing_session = self.sessions.get(existing_session_id)
            if existing_session:
                logger.info(f"중복 로그인 감지 - 기존 세션 종료: {existing_session_id}, 플레이어: {player.username}")
                # 기존 세션에 종료 메시지 전송 후 연결 종료
                try:
                    await existing_session.send_message({
                        "type": "system_message",
                        "message": "다른 곳에서 로그인하여 연결이 종료됩니다."
                    })
                    await existing_session.close("다른 곳에서 로그인하여 연결이 종료됩니다.")
                except Exception as e:
                    logger.warning(f"기존 세션 종료 처리 실패: {e}")
                
                # 기존 세션 정리
                self.remove_session(existing_session_id)

        # 세션 등록 (인증은 telnet_server에서 수행)
        self.player_sessions[player.id] = session_id
        short_session_id = session_id.split('-')[-1] if '-' in session_id else session_id
        logger.info(f"세션 등록: {short_session_id}, 플레이어: {player.username}")

    def get_session(self, session_id: str) -> Optional[TelnetSession]:
        """세션 조회

        Args:
            session_id: 세션 ID

        Returns:
            Optional[TelnetSession]: 세션 객체
        """
        return self.sessions.get(session_id)

    def get_player_session(self, player_id: str) -> Optional[TelnetSession]:
        """플레이어의 세션 조회

        Args:
            player_id: 플레이어 ID

        Returns:
            Optional[TelnetSession]: 세션 객체
        """
        session_id = self.player_sessions.get(player_id)
        if session_id:
            return self.sessions.get(session_id)
        return None

    def get_all_sessions(self) -> list[TelnetSession]:
        """모든 세션 조회

        Returns:
            list[TelnetSession]: 세션 목록
        """
        return list(self.sessions.values())

    def get_authenticated_sessions(self) -> list[TelnetSession]:
        """인증된 세션 목록 조회

        Returns:
            list[TelnetSession]: 인증된 세션 목록
        """
        return [s for s in self.sessions.values() if s.is_authenticated]

    def get_stats(self) -> Dict[str, int]:
        """세션 통계 정보 반환

        Returns:
            Dict[str, int]: 통계 정보
        """
        total_sessions = len(self.sessions)
        authenticated_sessions = len([s for s in self.sessions.values() if s.is_authenticated])
        active_sessions = len([s for s in self.sessions.values() if s.is_active()])

        return {
            "total_sessions": total_sessions,
            "authenticated_sessions": authenticated_sessions,
            "active_sessions": active_sessions,
            "inactive_sessions": total_sessions - active_sessions
        }

    async def broadcast_to_all(self, message: Dict[str, Any], authenticated_only: bool = True) -> int:
        """모든 세션에 메시지 브로드캐스트

        Args:
            message: 전송할 메시지
            authenticated_only: 인증된 세션에만 전송할지 여부

        Returns:
            int: 메시지를 받은 세션 수
        """
        count = 0
        for session in self.sessions.values():
            if authenticated_only and not session.is_authenticated:
                continue
            if await session.send_message(message):
                count += 1
        return count

    def iter_authenticated_sessions(self):
        """인증된 세션을 순회하는 이터레이터 반환
        
        리스트/딕셔너리 호환성 문제를 해결하는 헬퍼 메서드
        
        Yields:
            TelnetSession: 인증된 세션
        """
        for session in self.sessions.values():
            if session.is_authenticated:
                yield session
    
    def iter_all_sessions(self):
        """모든 세션을 순회하는 이터레이터 반환
        
        리스트/딕셔너리 호환성 문제를 해결하는 헬퍼 메서드
        
        Yields:
            TelnetSession: 세션
        """
        return iter(self.sessions.values())
