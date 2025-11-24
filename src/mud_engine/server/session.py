# -*- coding: utf-8 -*-
"""WebSocket 세션 관리"""

import asyncio
import json
import logging
import time
import uuid
from typing import Optional, Dict, Any
from datetime import datetime

from aiohttp import web, WSMsgType

from ..game.models import Player
from ..utils.exceptions import AuthenticationError

logger = logging.getLogger(__name__)


class Session:
    """플레이어 WebSocket 세션을 관리하는 클래스"""

    def __init__(self, websocket: web.WebSocketResponse, session_id: Optional[str] = None):
        """
        Session 초기화

        Args:
            websocket: WebSocket 연결 객체
            session_id: 세션 ID (없으면 자동 생성)
        """
        self.session_id: str = session_id or str(uuid.uuid4())
        self.websocket: web.WebSocketResponse = websocket
        self.player: Optional[Player] = None
        self.is_authenticated: bool = False
        self.created_at: datetime = datetime.now()
        self.last_activity: datetime = datetime.now()
        self.ip_address: Optional[str] = None
        self.user_agent: Optional[str] = None
        self.metadata: Dict[str, Any] = {}

        # 게임 관련 속성
        self.current_room_id: Optional[str] = None
        self.locale: str = "en"  # 기본 언어 설정
        self.game_engine: Optional[Any] = None  # GameEngine 참조
        self.following_player: Optional[str] = None  # 따라가고 있는 플레이어 이름
        
        # 전투 관련 속성
        self.in_combat: bool = False  # 전투 중인지 여부
        self.original_room_id: Optional[str] = None  # 전투 전 원래 방 ID
        self.combat_id: Optional[str] = None  # 참여 중인 전투 ID

        logger.info(f"새 세션 생성: {self.session_id}")

    def authenticate(self, player: Player) -> None:
        """
        세션에 플레이어 인증 정보 설정

        Args:
            player: 인증된 플레이어 객체
        """
        self.player = player
        self.is_authenticated = True
        self.update_activity()
        logger.info(f"세션 {self.session_id}에 플레이어 '{player.username}' 인증 완료")

    def update_activity(self) -> None:
        """마지막 활동 시간 업데이트"""
        self.last_activity = datetime.now()

    async def send_message(self, message: Dict[str, Any]) -> bool:
        """
        클라이언트에게 메시지 전송

        Args:
            message: 전송할 메시지 딕셔너리

        Returns:
            bool: 전송 성공 여부
        """
        try:
            if self.websocket.closed:
                logger.warning(f"세션 {self.session_id}: WebSocket이 이미 닫혀있음")
                return False

            await self.websocket.send_json(message)
            self.update_activity()
            return True

        except Exception as e:
            logger.error(f"세션 {self.session_id} 메시지 전송 실패: {e}")
            return False

    async def send_ui_update(self, ui_data: Dict[str, Any]) -> bool:
        """
        클라이언트에게 UI 업데이트 정보 전송

        Args:
            ui_data: UI 업데이트 데이터

        Returns:
            bool: 전송 성공 여부
        """
        ui_message = {
            "type": "ui_update",
            "ui": ui_data,
            "timestamp": datetime.now().isoformat()
        }
        return await self.send_message(ui_message)

    async def send_error(self, error_message: str, error_code: Optional[str] = None) -> bool:
        """
        클라이언트에게 오류 메시지 전송

        Args:
            error_message: 오류 메시지
            error_code: 오류 코드 (선택사항)

        Returns:
            bool: 전송 성공 여부
        """
        error_data = {
            "error": error_message,
            "timestamp": datetime.now().isoformat()
        }

        if error_code:
            error_data["error_code"] = error_code

        return await self.send_message(error_data)

    async def send_success(self, message: str, data: Optional[Dict[str, Any]] = None) -> bool:
        """
        클라이언트에게 성공 메시지 전송

        Args:
            message: 성공 메시지
            data: 추가 데이터 (선택사항)

        Returns:
            bool: 전송 성공 여부
        """
        success_data = {
            "status": "success",
            "message": message,
            "timestamp": datetime.now().isoformat()
        }

        if data:
            success_data["data"] = data

        return await self.send_message(success_data)

    async def close(self, code: int = 1000, message: str = "Session closed") -> None:
        """
        WebSocket 연결 종료

        Args:
            code: WebSocket 종료 코드
            message: 종료 메시지
        """
        try:
            if not self.websocket.closed:
                await self.websocket.close(code=code, message=message.encode())
                logger.info(f"세션 {self.session_id} 연결 종료: {message}")
        except Exception as e:
            logger.error(f"세션 {self.session_id} 종료 중 오류: {e}")

    def is_active(self, timeout_seconds: int = 300) -> bool:
        """
        세션이 활성 상태인지 확인

        Args:
            timeout_seconds: 타임아웃 시간 (초)

        Returns:
            bool: 활성 상태 여부
        """
        if self.websocket.closed:
            return False

        inactive_time = (datetime.now() - self.last_activity).total_seconds()
        return inactive_time < timeout_seconds

    def get_session_info(self) -> Dict[str, Any]:
        """
        세션 정보 반환

        Returns:
            Dict: 세션 정보
        """
        return {
            "session_id": self.session_id,
            "player_id": self.player.id if self.player else None,
            "username": self.player.username if self.player else None,
            "is_authenticated": self.is_authenticated,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "is_active": self.is_active(),
            "websocket_closed": self.websocket.closed
        }

    def __str__(self) -> str:
        """세션 문자열 표현"""
        player_info = f"({self.player.username})" if self.player else "(미인증)"
        return f"Session[{self.session_id[:8]}...]{player_info}"

    def __repr__(self) -> str:
        """세션 상세 표현"""
        return (f"Session(session_id='{self.session_id}', "
                f"player={self.player.username if self.player else None}, "
                f"authenticated={self.is_authenticated}, "
                f"active={self.is_active()})")


class SessionManager:
    """세션들을 관리하는 매니저 클래스"""

    def __init__(self):
        """SessionManager 초기화"""
        self.sessions: Dict[str, Session] = {}
        self.player_sessions: Dict[str, str] = {}  # player_id -> session_id 매핑
        self._cleanup_task: Optional[asyncio.Task] = None
        self._cleanup_interval: int = 60  # 60초마다 정리

        logger.info("SessionManager 초기화 완료")

    async def start_cleanup_task(self) -> None:
        """비활성 세션 정리 작업 시작"""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_inactive_sessions())
            logger.info("세션 정리 작업 시작")

    async def stop_cleanup_task(self) -> None:
        """비활성 세션 정리 작업 중지"""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("세션 정리 작업 중지")

    def add_session(self, websocket: web.WebSocketResponse,
                   request: web.Request) -> Session:
        """
        새 세션 추가

        Args:
            websocket: WebSocket 연결 객체
            request: HTTP 요청 객체

        Returns:
            Session: 생성된 세션 객체
        """
        session = Session(websocket)

        # 요청 정보 설정
        session.ip_address = request.remote
        session.user_agent = request.headers.get('User-Agent')

        self.sessions[session.session_id] = session

        logger.info(f"새 세션 추가: {session.session_id} (총 {len(self.sessions)}개)")
        return session

    def authenticate_session(self, session_id: str, player: Player) -> bool:
        """
        세션에 플레이어 인증

        Args:
            session_id: 세션 ID
            player: 플레이어 객체

        Returns:
            bool: 인증 성공 여부
        """
        session = self.sessions.get(session_id)
        if not session:
            logger.warning(f"세션 {session_id}를 찾을 수 없음")
            return False

        # 기존 플레이어 세션이 있다면 제거
        if player.id in self.player_sessions:
            old_session_id = self.player_sessions[player.id]
            if old_session_id in self.sessions:
                logger.info(f"플레이어 {player.username}의 기존 세션 {old_session_id} 제거")
                asyncio.create_task(self.remove_session(old_session_id,
                                                      "새 세션으로 대체됨"))

        session.authenticate(player)
        self.player_sessions[player.id] = session_id

        return True

    async def remove_session(self, session_id: str, reason: str = "세션 종료") -> bool:
        """
        세션 제거

        Args:
            session_id: 제거할 세션 ID
            reason: 제거 이유

        Returns:
            bool: 제거 성공 여부
        """
        session = self.sessions.get(session_id)
        if not session:
            return False

        # 플레이어 매핑 제거
        if session.player and session.player.id in self.player_sessions:
            del self.player_sessions[session.player.id]

        # WebSocket 연결 종료
        await session.close(message=reason)

        # 로그아웃 로깅 (인증된 세션인 경우)
        if session.player:
            logger.info(f"🚪 세션 종료: 플레이어='{session.player.username}', 이유='{reason}', IP={session.ip_address}")

        # 세션 제거
        if session_id in self.sessions:
            del self.sessions[session_id]

        logger.info(f"세션 {session_id[:8]}... 제거: {reason} (남은 세션: {len(self.sessions)}개)")
        return True

    def get_session(self, session_id: str) -> Optional[Session]:
        """
        세션 ID로 세션 조회

        Args:
            session_id: 세션 ID

        Returns:
            Optional[Session]: 세션 객체 (없으면 None)
        """
        return self.sessions.get(session_id)

    def get_player_session(self, player_id: str) -> Optional[Session]:
        """
        플레이어 ID로 세션 조회

        Args:
            player_id: 플레이어 ID

        Returns:
            Optional[Session]: 세션 객체 (없으면 None)
        """
        session_id = self.player_sessions.get(player_id)
        if session_id:
            return self.sessions.get(session_id)
        return None

    def get_all_sessions(self) -> Dict[str, Session]:
        """모든 세션 반환"""
        return self.sessions.copy()

    def get_authenticated_sessions(self) -> Dict[str, Session]:
        """인증된 세션들만 반환"""
        return {sid: session for sid, session in self.sessions.items()
                if session.is_authenticated}

    async def broadcast_to_all(self, message: Dict[str, Any],
                              authenticated_only: bool = True) -> int:
        """
        모든 세션에 메시지 브로드캐스트

        Args:
            message: 브로드캐스트할 메시지
            authenticated_only: 인증된 세션에만 전송할지 여부

        Returns:
            int: 성공적으로 전송된 세션 수
        """
        sessions = (self.get_authenticated_sessions() if authenticated_only
                   else self.sessions)

        success_count = 0
        for session in sessions.values():
            if await session.send_message(message):
                success_count += 1

        logger.info(f"브로드캐스트 완료: {success_count}/{len(sessions)}개 세션")
        return success_count

    async def _cleanup_inactive_sessions(self) -> None:
        """비활성 세션 정리 (백그라운드 작업)"""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)

                inactive_sessions = []
                for session_id, session in self.sessions.items():
                    if not session.is_active():
                        inactive_sessions.append(session_id)

                for session_id in inactive_sessions:
                    await self.remove_session(session_id, "비활성 상태로 인한 정리")

                if inactive_sessions:
                    logger.info(f"{len(inactive_sessions)}개 비활성 세션 정리 완료")

            except asyncio.CancelledError:
                logger.info("세션 정리 작업 취소됨")
                break
            except Exception as e:
                logger.error(f"세션 정리 중 오류: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """
        세션 통계 정보 반환

        Returns:
            Dict: 통계 정보
        """
        total_sessions = len(self.sessions)
        authenticated_sessions = len(self.get_authenticated_sessions())
        active_sessions = sum(1 for s in self.sessions.values() if s.is_active())

        return {
            "total_sessions": total_sessions,
            "authenticated_sessions": authenticated_sessions,
            "active_sessions": active_sessions,
            "inactive_sessions": total_sessions - active_sessions,
            "cleanup_interval": self._cleanup_interval
        }