# -*- coding: utf-8 -*-
"""Telnet 세션 관리"""

import asyncio
import json
import logging
import uuid
from typing import Optional, Dict, Any
from datetime import datetime

from ..game.models import Player
from .serialization import build_event, encode_line
from .serialization import error as protocol_error
from .session.util import short_session_id as _short_id
from .session.transport import TelnetTransport
from .session.protocol import TelnetProtocol
from .session.state import SessionState

logger = logging.getLogger(__name__)


class TelnetSession:
    """Telnet 클라이언트 세션을 관리하는 클래스"""

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        session_id: Optional[str] = None,
    ):
        """
        TelnetSession 초기화

        Args:
            reader: asyncio StreamReader 객체
            writer: asyncio StreamWriter 객체
            session_id: 세션 ID (없으면 자동 생성)
        """
        self.session_id: str = session_id or str(uuid.uuid4())
        self.reader: asyncio.StreamReader = reader
        self.writer: asyncio.StreamWriter = writer

        # 도메인 상태 (SessionState로 분리, 아래 프로퍼티로 프록시)
        self.state = SessionState()

        # 연결 메타데이터
        self.created_at: datetime = datetime.now()
        self.last_activity: datetime = datetime.now()
        self.ip_address: Optional[str] = None
        self.metadata: Dict[str, Any] = {}
        self.game_engine: Optional[Any] = None  # GameEngine 참조

        # IP 주소 추출
        peername = writer.get_extra_info("peername")
        if peername:
            self.ip_address = peername[0]

        # 전송(Transport) 구성요소 - 바이트 IO 위임
        self._transport = TelnetTransport(
            reader, writer, self.session_id, self.update_activity
        )
        # 프로토콜(Protocol) 구성요소 - IAC 협상/필터링 위임
        self._protocol = TelnetProtocol(writer)

        short_session_id = _short_id(self.session_id)
        logger.info(f"새 Telnet 세션 생성: {short_session_id} (IP: {self.ip_address})")

    # ── 도메인 상태 프록시 (SessionState 위임, 외부 API 보존) ──

    @property
    def player(self) -> Optional[Player]:
        return self.state.player

    @player.setter
    def player(self, value: Optional[Player]) -> None:
        self.state.player = value

    @property
    def is_authenticated(self) -> bool:
        return self.state.is_authenticated

    @is_authenticated.setter
    def is_authenticated(self, value: bool) -> None:
        self.state.is_authenticated = value

    @property
    def current_room_id(self) -> Optional[str]:
        return self.state.current_room_id

    @current_room_id.setter
    def current_room_id(self, value: Optional[str]) -> None:
        self.state.current_room_id = value

    @property
    def current_room_type(self) -> str:
        return self.state.current_room_type

    @current_room_type.setter
    def current_room_type(self, value: str) -> None:
        self.state.current_room_type = value

    @property
    def following_player(self) -> Optional[str]:
        return self.state.following_player

    @following_player.setter
    def following_player(self, value: Optional[str]) -> None:
        self.state.following_player = value

    @property
    def in_combat(self) -> bool:
        return self.state.in_combat

    @in_combat.setter
    def in_combat(self, value: bool) -> None:
        self.state.in_combat = value

    @property
    def original_room_id(self) -> Optional[str]:
        return self.state.original_room_id

    @original_room_id.setter
    def original_room_id(self, value: Optional[str]) -> None:
        self.state.original_room_id = value

    @property
    def combat_id(self) -> Optional[str]:
        return self.state.combat_id

    @combat_id.setter
    def combat_id(self, value: Optional[str]) -> None:
        self.state.combat_id = value

    @property
    def in_dialogue(self) -> bool:
        return self.state.in_dialogue

    @in_dialogue.setter
    def in_dialogue(self, value: bool) -> None:
        self.state.in_dialogue = value

    @property
    def dialogue_id(self) -> Optional[str]:
        return self.state.dialogue_id

    @dialogue_id.setter
    def dialogue_id(self, value: Optional[str]) -> None:
        self.state.dialogue_id = value

    @property
    def stamina(self) -> float:
        return self.state.stamina

    @stamina.setter
    def stamina(self, value: float) -> None:
        self.state.stamina = value

    @property
    def max_stamina(self) -> float:
        return self.state.max_stamina

    @max_stamina.setter
    def max_stamina(self, value: float) -> None:
        self.state.max_stamina = value

    @property
    def last_command(self) -> Optional[str]:
        return self.state.last_command

    @last_command.setter
    def last_command(self, value: Optional[str]) -> None:
        self.state.last_command = value

    async def initialize_telnet(self) -> None:
        """
        Telnet 프로토콜 초기화 및 협상 (Protocol 위임)
        """
        await self._protocol.initialize()

    def authenticate(self, player: Player) -> None:
        """
        세션에 플레이어 인증 정보 설정

        Args:
            player: 인증된 플레이어 객체
        """
        self.player = player
        self.is_authenticated = True
        self.update_activity()
        short_session_id = _short_id(self.session_id)
        logger.info(
            f"Telnet 세션 {short_session_id}에 플레이어 '{player.username}' 인증 완료"
        )

    def deauthenticate(self) -> None:
        """인증과 게임 도메인 상태만 해제한다. 연결은 유지한다.

        계약(`docs/protocol/client-to-server.md` logout)이 `logout` 을 연결 종료가
        아니라 인증 해제로 정의한다. 클라이언트는 로그인 화면으로 돌아가 같은
        연결에서 다른 계정으로 접속할 수 있다.

        상태 컨테이너를 새로 만든다. 필드를 하나씩 되돌리면 나중에 추가된 필드가
        남는다.
        """
        username = self.state.player.username if self.state.player else None
        self.state = SessionState()
        self.update_activity()
        logger.info(
            f"Telnet 세션 {_short_id(self.session_id)} 인증 해제: {username}"
        )

    def update_activity(self) -> None:
        """마지막 활동 시간 업데이트"""
        self.last_activity = datetime.now()

    async def send_message(self, message: Dict[str, Any]) -> bool:
        """구조화 메시지를 JSON 라인으로 전송한다.

        메시지를 가공하지 않는다. 텍스트 조립과 번역은 클라이언트 책임이다.

        Args:
            message: `type` 을 가진 메시지 딕셔너리

        Returns:
            전송 성공 여부
        """
        try:
            if "type" not in message:
                logger.error(
                    f"Telnet 세션 {_short_id(self.session_id)}: "
                    "type 없는 메시지 전송 시도"
                )
                return False

            return await self._transport.send_line(encode_line(message))

        except ValueError as e:
            # 직렬화 결과에 개행이 포함된 경우
            logger.error(f"Telnet 세션 {self.session_id} 인코딩 실패: {e}")
            return False
        except Exception as e:
            logger.error(f"Telnet 세션 {self.session_id} 메시지 전송 실패: {e}")
            return False

    async def send_event(
        self,
        key: str,
        params: Optional[Dict[str, Any]] = None,
        category: str = "system",
        seq: Optional[int] = None,
    ) -> bool:
        """번역 키 기반 알림을 전송한다.

        서버는 완성된 문장을 만들지 않는다. 수신 클라이언트가 각자의 언어로
        번역하므로 브로드캐스트에서 발신자 언어가 전파되지 않는다.

        Args:
            key: 번역 키
            params: 치환 파라미터. 값이 언어별 dict 이면 클라이언트가 골라 쓴다
            category: 로그 채널 분류 (combat/movement/item/social/system/dialogue)
            seq: 요청에 대한 응답이면 그 번호

        Returns:
            전송 성공 여부
        """
        return await self.send_message(
            build_event(key, params, category=category, seq=seq)
        )

    async def send_protocol_error(
        self, reason_code: str, detail: str = "", seq: Optional[int] = None
    ) -> bool:
        """프로토콜 계약 위반을 알린다.

        JSON 파싱 실패, 필수 필드 누락처럼 계약 위반에만 사용한다. 게임 로직의
        거절에는 `action_rejected` 를 쓴다.
        """
        return await self.send_message(protocol_error(reason_code, detail, seq))

    async def read_message(
        self, timeout: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """클라이언트로부터 유효한 JSON 메시지 한 건을 읽는다.

        라인 → UTF-8 디코딩 → json.loads → 봉투 검증 순서로 처리한다. 계약을
        위반한 라인은 `error` 를 보내고 다음 라인을 계속 읽으므로, None 은 연결
        종료 또는 타임아웃만을 뜻한다.

        Args:
            timeout: 라인 하나를 기다리는 시간 (초)

        Returns:
            검증을 통과한 메시지. 연결이 끝났거나 타임아웃이면 None
        """
        while True:
            line = await self.read_line(timeout)

            if line is None:
                return None

            if line == "":
                # Telnet 협상 바이트만 있었던 경우로 오류가 아니다
                continue

            try:
                message = json.loads(line)
            except json.JSONDecodeError as e:
                logger.warning(
                    f"Telnet 세션 {_short_id(self.session_id)} JSON 파싱 실패: {e}"
                )
                await self.send_protocol_error(
                    "MALFORMED_MESSAGE", "line is not valid JSON"
                )
                continue

            if not isinstance(message, dict):
                await self.send_protocol_error(
                    "MALFORMED_MESSAGE", "message must be a JSON object"
                )
                continue

            if not isinstance(message.get("type"), str):
                await self.send_protocol_error(
                    "MALFORMED_MESSAGE", "missing type field"
                )
                continue

            return message

    def _filter_telnet_commands(self, data: bytes) -> bytes:
        """
        Telnet 프로토콜 명령어를 필터링 (Protocol 위임)

        Args:
            data: 원본 바이트 데이터

        Returns:
            bytes: 필터링된 데이터
        """
        return TelnetProtocol.filter_commands(data)

    async def read_line(self, timeout: Optional[float] = None) -> Optional[str]:
        """
        클라이언트로부터 한 줄 읽기 (백스페이스/IAC 처리 포함, Transport 위임)

        Args:
            timeout: 타임아웃 시간 (초)

        Returns:
            Optional[str]: 읽은 문자열 (타임아웃 또는 연결 종료 시 None, 빈 줄은 "")
        """
        return await self._transport.read_line(timeout)

    async def close(self, message: str = "Connection closed") -> None:
        """
        Telnet 연결 종료 (Transport 위임)

        Args:
            message: 종료 메시지
        """
        await self._transport.close(message)

    def is_active(self, timeout_seconds: int = 300) -> bool:
        """
        세션이 활성 상태인지 확인

        Args:
            timeout_seconds: 타임아웃 시간 (초)

        Returns:
            bool: 활성 상태 여부
        """
        if self.writer.is_closing():
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
            "is_active": self.is_active(),
            "connection_closed": self.writer.is_closing(),
        }

    def __str__(self) -> str:
        """세션 문자열 표현"""
        player_info = f"({self.player.username})" if self.player else "(미인증)"
        short_session_id = _short_id(self.session_id)
        return f"TelnetSession[{short_session_id}]{player_info}"

    def __repr__(self) -> str:
        """세션 상세 표현"""
        return (
            f"TelnetSession(session_id='{self.session_id}', "
            f"player={self.player.username if self.player else None}, "
            f"authenticated={self.is_authenticated}, "
            f"active={self.is_active()})"
        )
