# -*- coding: utf-8 -*-
"""Telnet 세션 관리"""

import asyncio
import logging
import uuid
from typing import Optional, Dict, Any
from datetime import datetime

from ..game.models import Player

logger = logging.getLogger(__name__)


class TelnetSession:
    """Telnet 클라이언트 세션을 관리하는 클래스"""

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
                 session_id: Optional[str] = None):
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
        self.player: Optional[Player] = None
        self.is_authenticated: bool = False
        self.created_at: datetime = datetime.now()
        self.last_activity: datetime = datetime.now()
        self.ip_address: Optional[str] = None
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

        # Telnet 관련 속성
        self.use_ansi_colors: bool = True  # ANSI 색상 코드 사용 여부
        self.terminal_width: int = 80  # 터미널 너비
        self.terminal_height: int = 24  # 터미널 높이

        # IP 주소 추출
        peername = writer.get_extra_info('peername')
        if peername:
            self.ip_address = peername[0]

        logger.info(f"새 Telnet 세션 생성: {self.session_id} (IP: {self.ip_address})")

    async def initialize_telnet(self) -> None:
        """
        Telnet 프로토콜 초기화 및 협상
        """
        # Telnet 옵션 협상 응답
        # WONT ECHO - 서버가 에코를 처리하지 않음 (클라이언트가 에코함)
        # WILL SUPPRESS_GO_AHEAD - Go-Ahead 신호 억제
        # DONT LINEMODE - 라인 모드 사용 안 함
        
        IAC = bytes([255])  # Interpret As Command
        WILL = bytes([251])
        WONT = bytes([252])
        DO = bytes([253])
        DONT = bytes([254])
        
        ECHO = bytes([1])
        SUPPRESS_GO_AHEAD = bytes([3])
        LINEMODE = bytes([34])
        
        try:
            # 서버 옵션 전송
            self.writer.write(IAC + WILL + SUPPRESS_GO_AHEAD)
            self.writer.write(IAC + WONT + ECHO)  # 기본적으로 클라이언트가 에코
            self.writer.write(IAC + DONT + LINEMODE)
            await self.writer.drain()
        except Exception as e:
            logger.debug(f"Telnet 프로토콜 협상 오류 (무시됨): {e}")

    def authenticate(self, player: Player) -> None:
        """
        세션에 플레이어 인증 정보 설정

        Args:
            player: 인증된 플레이어 객체
        """
        self.player = player
        self.is_authenticated = True
        self.locale = player.preferred_locale
        self.update_activity()
        logger.info(f"Telnet 세션 {self.session_id}에 플레이어 '{player.username}' 인증 완료")

    def update_activity(self) -> None:
        """마지막 활동 시간 업데이트"""
        self.last_activity = datetime.now()

    async def send_message(self, message: Dict[str, Any]) -> bool:
        """
        클라이언트에게 메시지 전송 (WebSocket 호환 인터페이스)

        Args:
            message: 전송할 메시지 딕셔너리

        Returns:
            bool: 전송 성공 여부
        """
        try:
            # 메시지 타입에 따라 적절한 포맷으로 변환
            text = self._format_message(message)
            return await self.send_text(text)

        except Exception as e:
            logger.error(f"Telnet 세션 {self.session_id} 메시지 전송 실패: {e}")
            return False

    def _format_message(self, message: Dict[str, Any]) -> str:
        """메시지 딕셔너리를 Telnet 텍스트 포맷으로 변환

        Args:
            message: 메시지 딕셔너리

        Returns:
            str: 포맷된 텍스트
        """
        from .ansi_colors import ANSIColors

        msg_type = message.get("type", "")
        
        # 에러 메시지
        if "error" in message:
            return ANSIColors.error(f"❌ {message['error']}")
        
        # 성공 메시지
        if message.get("status") == "success":
            msg_text = message.get("message", "")
            return ANSIColors.success(f"✅ {msg_text}")
        
        # 방 정보
        if msg_type == "room_info":
            return self._format_room_info(message.get("room", {}))
        
        # 방 메시지
        if msg_type == "room_message":
            return message.get("message", "")
        
        # 시스템 메시지
        if msg_type == "system_message":
            return ANSIColors.info(message.get("message", ""))
        
        # 일반 응답
        if "response" in message:
            return message["response"]
        
        # 일반 메시지
        if "message" in message:
            return message["message"]
        
        # 기본값
        return str(message)

    def _format_room_info(self, room_data: Dict[str, Any]) -> str:
        """방 정보를 Telnet 포맷으로 변환

        Args:
            room_data: 방 정보 딕셔너리

        Returns:
            str: 포맷된 방 정보
        """
        from .ansi_colors import ANSIColors

        lines = []
        
        lines.append("")
        lines.append("=" * 60)
        
        # 방 설명
        description = room_data.get("description", "")
        if description:
            lines.append(description)
            lines.append("")
        
        # 시간대 정보
        if self.game_engine and hasattr(self.game_engine, 'time_manager'):
            time_of_day = self.game_engine.time_manager.get_current_time()
            if time_of_day.value == "day":
                lines.append("☀️  낮")
            else:
                lines.append("🌙 밤")
            lines.append("")
        
        # 출구
        exits = room_data.get("exits", {})
        if exits:
            exit_list = ", ".join([ANSIColors.exit_direction(direction) for direction in exits.keys()])
            lines.append(f"🚪 출구: {exit_list}")
        
        # 플레이어
        players = room_data.get("players", [])
        if players:
            lines.append("")
            lines.append("👥 이곳에 있는 플레이어들:")
            for player in players:
                player_name = player.get("username", "알 수 없음")
                lines.append(f"  • {ANSIColors.player_name(player_name)}")
        
        # 객체
        objects = room_data.get("objects", [])
        if objects:
            lines.append("")
            lines.append("📦 이곳에 있는 물건들:")
            for obj in objects:
                obj_name = obj.get("name", "알 수 없음")
                lines.append(f"  • {ANSIColors.item_name(obj_name)}")
        
        # 몬스터 (각각 개별 표시)
        monsters = room_data.get("monsters", [])
        if monsters:
            lines.append("")
            lines.append("👹 이곳에 있는 몬스터들:")
            for i, monster in enumerate(monsters, 1):
                monster_name = monster.get("name", "알 수 없음")
                monster_id = monster.get("id", "")
                level = monster.get("level", 1)
                hp = monster.get("current_hp", 0)
                max_hp = monster.get("max_hp", 0)
                
                # 각 몬스터를 개별 ID로 구분하여 표시
                # ID의 마지막 4자리를 사용하여 구분
                id_suffix = monster_id[-4:] if len(monster_id) >= 4 else monster_id
                lines.append(f"  • {ANSIColors.monster_name(monster_name)} #{id_suffix} (레벨 {level}, HP: {hp}/{max_hp})")
        
        lines.append("")
        return "\r\n".join(lines)

    async def send_text(self, text: str, newline: bool = True) -> bool:
        """
        클라이언트에게 텍스트 전송

        Args:
            text: 전송할 텍스트
            newline: 줄바꿈 추가 여부

        Returns:
            bool: 전송 성공 여부
        """
        try:
            if self.writer.is_closing():
                logger.warning(f"Telnet 세션 {self.session_id}: 연결이 이미 닫혀있음")
                return False

            # 텍스트 인코딩 및 전송
            if newline:
                text += "\r\n"

            self.writer.write(text.encode('utf-8'))
            await self.writer.drain()
            self.update_activity()
            return True

        except Exception as e:
            logger.error(f"Telnet 세션 {self.session_id} 텍스트 전송 실패: {e}")
            return False

    async def send_colored_text(self, text: str, color_code: str = "",
                               newline: bool = True) -> bool:
        """
        ANSI 색상 코드를 사용하여 텍스트 전송

        Args:
            text: 전송할 텍스트
            color_code: ANSI 색상 코드
            newline: 줄바꿈 추가 여부

        Returns:
            bool: 전송 성공 여부
        """
        if self.use_ansi_colors and color_code:
            colored_text = f"{color_code}{text}\033[0m"
        else:
            colored_text = text

        return await self.send_text(colored_text, newline)

    async def send_error(self, error_message: str) -> bool:
        """
        클라이언트에게 오류 메시지 전송 (빨간색)

        Args:
            error_message: 오류 메시지

        Returns:
            bool: 전송 성공 여부
        """
        return await self.send_colored_text(f"❌ {error_message}", "\033[31m")

    async def send_success(self, message: str, data: Optional[Dict[str, Any]] = None) -> bool:
        """
        클라이언트에게 성공 메시지 전송 (녹색)

        Args:
            message: 성공 메시지
            data: 추가 데이터 (선택사항, Telnet에서는 무시됨)

        Returns:
            bool: 전송 성공 여부
        """
        return await self.send_colored_text(f"✅ {message}", "\033[32m")

    async def send_ui_update(self, ui_data: Dict[str, Any]) -> bool:
        """
        클라이언트에게 UI 업데이트 정보 전송 (Telnet에서는 무시)

        Args:
            ui_data: UI 업데이트 데이터

        Returns:
            bool: 항상 True (Telnet은 UI 업데이트가 없음)
        """
        # Telnet 클라이언트는 UI 업데이트가 없으므로 무시
        return True

    async def send_info(self, message: str) -> bool:
        """
        클라이언트에게 정보 메시지 전송 (파란색)

        Args:
            message: 정보 메시지

        Returns:
            bool: 전송 성공 여부
        """
        return await self.send_colored_text(message, "\033[36m")

    async def send_prompt(self, prompt: str = "> ") -> bool:
        """
        클라이언트에게 프롬프트 전송 (줄바꿈 없음)

        Args:
            prompt: 프롬프트 문자열

        Returns:
            bool: 전송 성공 여부
        """
        return await self.send_text(prompt, newline=False)

    async def disable_echo(self) -> None:
        """
        클라이언트 에코 비활성화 (패스워드 입력용)
        """
        IAC = bytes([255])  # Interpret As Command
        WILL = bytes([251])
        ECHO = bytes([1])
        
        try:
            # 서버가 에코를 처리하겠다고 알림 (클라이언트 에코 비활성화)
            self.writer.write(IAC + WILL + ECHO)
            await self.writer.drain()
        except Exception as e:
            logger.debug(f"에코 비활성화 오류 (무시됨): {e}")

    async def enable_echo(self) -> None:
        """
        클라이언트 에코 활성화 (일반 입력용)
        """
        IAC = bytes([255])  # Interpret As Command
        WONT = bytes([252])
        ECHO = bytes([1])
        
        try:
            # 서버가 에코를 처리하지 않겠다고 알림 (클라이언트 에코 활성화)
            self.writer.write(IAC + WONT + ECHO)
            await self.writer.drain()
        except Exception as e:
            logger.debug(f"에코 활성화 오류 (무시됨): {e}")

    def _filter_telnet_commands(self, data: bytes) -> bytes:
        """
        Telnet 프로토콜 명령어를 필터링

        Args:
            data: 원본 바이트 데이터

        Returns:
            bytes: 필터링된 데이터
        """
        # Telnet 명령어 바이트
        IAC = 255  # 0xFF - Interpret As Command
        DONT = 254  # 0xFE
        DO = 253    # 0xFD
        WONT = 252  # 0xFC
        WILL = 251  # 0xFB
        
        result = bytearray()
        i = 0
        while i < len(data):
            if data[i] == IAC:
                # IAC 명령어 처리
                if i + 1 < len(data):
                    cmd = data[i + 1]
                    if cmd in (DO, DONT, WILL, WONT):
                        # 3바이트 명령어 (IAC + 명령 + 옵션)
                        if i + 2 < len(data):
                            i += 3
                            continue
                    elif cmd == IAC:
                        # IAC IAC는 실제 0xFF 바이트를 의미
                        result.append(IAC)
                        i += 2
                        continue
                    else:
                        # 2바이트 명령어
                        i += 2
                        continue
                i += 1
            else:
                result.append(data[i])
                i += 1
        
        return bytes(result)

    async def read_line(self, timeout: Optional[float] = None) -> Optional[str]:
        """
        클라이언트로부터 한 줄 읽기

        Args:
            timeout: 타임아웃 시간 (초)

        Returns:
            Optional[str]: 읽은 문자열 (타임아웃 또는 연결 종료 시 None, 빈 줄은 "")
        """
        try:
            if timeout:
                line = await asyncio.wait_for(
                    self.reader.readline(),
                    timeout=timeout
                )
            else:
                line = await self.reader.readline()

            # 연결 종료 확인 (빈 바이트)
            if not line:
                logger.debug(f"Telnet 세션 {self.session_id}: 연결 종료 감지 (빈 바이트)")
                return None

            # Telnet 프로토콜 명령어 필터링
            filtered_line = self._filter_telnet_commands(line)

            # 필터링 후 아무것도 남지 않은 경우 (프로토콜 바이트만 있었음)
            if not filtered_line or filtered_line == b'\r\n' or filtered_line == b'\n':
                logger.debug(f"Telnet 세션 {self.session_id}: 프로토콜 바이트만 수신, 계속 대기")
                return ""  # 빈 문자열 반환 (연결은 유지)

            # 디코딩 및 공백 제거
            try:
                decoded_line = filtered_line.decode('utf-8', errors='ignore').strip()
                self.update_activity()
                return decoded_line
            except Exception as e:
                logger.warning(f"Telnet 세션 {self.session_id} 디코딩 오류: {e}")
                return ""  # 빈 문자열 반환 (연결은 유지)

        except asyncio.TimeoutError:
            logger.debug(f"Telnet 세션 {self.session_id} 읽기 타임아웃")
            return None
        except Exception as e:
            logger.error(f"Telnet 세션 {self.session_id} 읽기 오류: {e}")
            return None

    async def close(self, message: str = "Connection closed") -> None:
        """
        Telnet 연결 종료

        Args:
            message: 종료 메시지
        """
        try:
            if not self.writer.is_closing():
                await self.send_text(f"\r\n{message}\r\n")
                self.writer.close()
                await self.writer.wait_closed()
                logger.info(f"Telnet 세션 {self.session_id} 연결 종료: {message}")
        except Exception as e:
            logger.error(f"Telnet 세션 {self.session_id} 종료 중 오류: {e}")

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
            "locale": self.locale,
            "use_ansi_colors": self.use_ansi_colors
        }

    def __str__(self) -> str:
        """세션 문자열 표현"""
        player_info = f"({self.player.username})" if self.player else "(미인증)"
        return f"TelnetSession[{self.session_id[:8]}...]{player_info}"

    def __repr__(self) -> str:
        """세션 상세 표현"""
        return (f"TelnetSession(session_id='{self.session_id}', "
                f"player={self.player.username if self.player else None}, "
                f"authenticated={self.is_authenticated}, "
                f"active={self.is_active()})")
