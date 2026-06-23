# -*- coding: utf-8 -*-
"""Telnet 세션 관리"""

import asyncio
import logging
import uuid
from typing import Optional, Dict, Any
from datetime import datetime

from ..game.models import Player
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

        # Telnet 관련 속성
        self.use_ansi_colors: bool = True  # ANSI 색상 코드 사용 여부
        self.terminal_width: int = 80  # 터미널 너비
        self.terminal_height: int = 24  # 터미널 높이

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
    def locale(self) -> str:
        return self.state.locale

    @locale.setter
    def locale(self, value: str) -> None:
        self.state.locale = value

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

    @property
    def room_entity_map(self) -> Dict[int, Dict[str, Any]]:
        return self.state.room_entity_map

    @room_entity_map.setter
    def room_entity_map(self, value: Dict[int, Dict[str, Any]]) -> None:
        self.state.room_entity_map = value

    @property
    def inventory_entity_map(self) -> Dict[int, Dict[str, Any]]:
        return self.state.inventory_entity_map

    @inventory_entity_map.setter
    def inventory_entity_map(self, value: Dict[int, Dict[str, Any]]) -> None:
        self.state.inventory_entity_map = value

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
        self.locale = player.preferred_locale
        self.update_activity()
        short_session_id = _short_id(self.session_id)
        logger.info(
            f"Telnet 세션 {short_session_id}에 플레이어 '{player.username}' 인증 완료"
        )

    def update_activity(self) -> None:
        """마지막 활동 시간 업데이트"""
        self.last_activity = datetime.now()

    def update_locale(self) -> None:
        """플레이어의 선호 언어로 세션 locale 업데이트"""
        if self.player:
            self.locale = self.player.preferred_locale
            logger.debug(f"세션 {self.session_id} 언어 업데이트: {self.locale}")

    async def send_message(self, message: Dict[str, Any]) -> bool:
        """
        클라이언트에게 메시지 전송 (WebSocket 호환 인터페이스)

        Args:
            message: 전송할 메시지 딕셔너리

        Returns:
            bool: 전송 성공 여부
        """
        try:
            # 디버깅: 전송되는 메시지 타입 확인
            msg_type = message.get("type", "")
            # print(f"DEBUG: send_message called with type: {msg_type}")
            logger.info(f"send_message called with type: {msg_type}")

            if msg_type == "room_info":
                # print(f"DEBUG: room_info message detected!")
                logger.info(f"room_info message detected!")
                entity_map = message.get("entity_map", {})
                # print(f"DEBUG: entity_map in room_info: {entity_map is not None}")
                logger.info(f"entity_map in room_info: {entity_map is not None}")

            # 메시지 타입에 따라 적절한 포맷으로 변환
            text = self._format_message(message)

            # 빈 문자열이면 전송하지 않음 (내부 업데이트 메시지)
            if not text or text.strip() == "":
                return True
            text = f"\n{text}\n".replace("\n\n", "\n")
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
        from ..core.localization import get_localization_manager

        msg_type = message.get("type", "")
        # localization = get_localization_manager()

        # 에러 메시지
        if "error" in message:
            return ANSIColors.error(f"❌ {message['error']}")

        # 성공 메시지
        if message.get("status") == "success":
            msg_text = message.get("message", "")
            return ANSIColors.success(f"✅ {msg_text}")

        # 방 정보
        if msg_type == "room_info":
            room_data = message.get("room", {})
            entity_map = message.get("entity_map", {})
            return self._format_room_info(room_data, entity_map)

        # 방 메시지
        if msg_type == "room_message":
            return message.get("message", "")

        # 시스템 메시지
        if msg_type == "system_message":
            return ANSIColors.info(message.get("message", ""))

        # 내부 업데이트 메시지 (클라이언트에 표시하지 않음)
        if msg_type in ["room_players_update", "player_status_update"]:
            return ""

        # 일반 응답
        if "response" in message:
            return message["response"]

        # 일반 메시지
        if "message" in message:
            return message["message"]

        # 기본값
        return str(message)

    def _format_room_info(
        self, room_data: Dict[str, Any], entity_map: Dict[int, Dict[str, Any]] = None
    ) -> str:
        """방 정보를 Telnet 포맷으로 변환

        Args:
            room_data: 방 정보 딕셔너리
            entity_map: 엔티티 번호 매핑

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
        if self.game_engine and hasattr(self.game_engine, "time_manager"):
            from ..core.localization import get_localization_manager

            localization = get_localization_manager()

            time_of_day = self.game_engine.time_manager.get_current_time()
            if time_of_day.value == "day":
                lines.append(localization.get_message("room.time_day", self.locale))
            else:
                lines.append(localization.get_message("room.time_night", self.locale))
            lines.append("")

        # 출구
        exits = room_data.get("exits", {})
        if exits:
            from ..core.localization import get_localization_manager

            localization = get_localization_manager()

            exit_list = ", ".join(
                [ANSIColors.exit_direction(direction) for direction in exits.keys()]
            )
            lines.append(
                localization.get_message("room.exits", self.locale, exits=exit_list)
            )

        # 플레이어
        players = room_data.get("players", [])
        if players:
            from ..core.localization import get_localization_manager

            localization = get_localization_manager()

            lines.append("")
            lines.append(localization.get_message("room.players_here", self.locale))
            for player in players:
                player_name = player.get("username", "Unknown" if self.locale == "en" else "알 수 없음")
                lines.append(f"  • {ANSIColors.player_name(player_name)}")

        # 디버깅: entity_map 로깅
        logger.debug(f"_format_room_info - entity_map: {entity_map}")
        if entity_map:
            logger.debug(f"entity_map keys: {list(entity_map.keys())}")
            for num, info in entity_map.items():
                logger.debug(f"  {num}: {info.get('type')} - {info.get('name')}")

        # 엔티티 번호 매핑 사용 (파라미터로 전달받음)
        if entity_map is None:
            entity_map = {}

        # 번호로 엔티티 ID 역매핑 생성 (아이템 처리 전에 먼저 생성)
        id_to_number = {}
        for num, entity_info in entity_map.items():
            id_to_number[entity_info["id"]] = num

        # 객체
        objects = room_data.get("objects", [])
        if objects:
            from ..core.localization import get_localization_manager

            localization = get_localization_manager()

            lines.append("")
            lines.append(localization.get_message("room.objects_here", self.locale))

            # 그룹화된 오브젝트 사용 (있는 경우)
            grouped_objects = room_data.get("grouped_objects", [])
            logger.debug(f"grouped_objects: {grouped_objects}")
            logger.debug(f"regular objects: {objects}")

            if grouped_objects:
                for group in grouped_objects:
                    if self.locale == "ko":
                        display_name = group.get(
                            "display_name_ko", group.get("name_ko", "Unknown" if self.locale == "en" else "알 수 없음")
                        )
                    else:
                        display_name = group.get(
                            "display_name_en", group.get("name_en", "Unknown")
                        )

                    # 아이템 번호 찾기 - 그룹의 첫 번째 객체 ID로 매칭
                    item_number = None
                    first_obj_id = None
                    if group.get("objects") and len(group["objects"]) > 0:
                        # GameObject 인스턴스에서 ID 추출
                        first_obj = group["objects"][0]
                        first_obj_id = getattr(first_obj, "id", None)

                    # id_to_number 딕셔너리 사용 (NPC와 동일한 방식)
                    if first_obj_id and first_obj_id in id_to_number:
                        item_number = id_to_number[first_obj_id]

                    if item_number:
                        lines.append(
                            f"• [{item_number}] {ANSIColors.item_name(display_name)}"
                        )
                    else:
                        lines.append(f"• {ANSIColors.item_name(display_name)}")
            else:
                # 기존 방식 (fallback) - 개별 객체들을 번호와 함께 표시
                for obj in objects:
                    obj_name = obj.get("name", "Unknown" if self.locale == "en" else "알 수 없음")
                    obj_id = obj.get("id", "")

                    # id_to_number 딕셔너리 사용 (NPC와 동일한 방식)
                    item_number = id_to_number.get(obj_id)

                    if item_number:
                        lines.append(
                            f"• [{item_number}] {ANSIColors.item_name(obj_name)}"
                        )
                    else:
                        lines.append(f"• {ANSIColors.item_name(obj_name)}")

        # NPC 및 몬스터 분류
        monsters = room_data.get("monsters", [])

        # 몬스터를 우호도에 따라 분류
        friendly_monsters = []
        neutral_monsters = []
        hostile_monsters = []

        if monsters and self.player:
            player_faction = self.player.faction_id or "ash_knights"

            for monster in monsters:
                monster_faction = monster.get("faction_id")

                # 같은 종족이면 우호적
                if monster_faction == player_faction:
                    friendly_monsters.append(monster)
                # 중립 종족 확인
                elif self._is_neutral_faction(player_faction, monster_faction):
                    neutral_monsters.append(monster)
                # 그 외는 적대적
                else:
                    hostile_monsters.append(monster)
        elif monsters:
            # 플레이어 정보가 없으면 모두 적대적으로 처리
            hostile_monsters = monsters

        # NPC와 우호적인 몬스터를 함께 표시
        all_npcs = friendly_monsters
        if all_npcs:
            from ..core.localization import get_localization_manager

            localization = get_localization_manager()

            lines.append("")
            lines.append(localization.get_message("room.npcs_here", self.locale))
            for npc in all_npcs:
                npc_name = npc.get("name", "Unknown" if self.locale == "en" else "알 수 없음")
                npc_id = npc.get("id", "")
                entity_num = id_to_number.get(npc_id, "?")

                # 우호적인 몬스터
                lines.append(f"  [{entity_num}] 👤 {ANSIColors.npc_name(npc_name)}")

        # 중립 몬스터 표시
        if neutral_monsters:
            from ..core.localization import get_localization_manager

            localization = get_localization_manager()

            lines.append("")
            lines.append(localization.get_message("room.animals_here", self.locale))
            for monster in neutral_monsters:
                monster_name = monster.get("name", "Unknown" if self.locale == "en" else "알 수 없음")
                monster_id = monster.get("id", "")
                entity_num = id_to_number.get(monster_id, "?")
                lines.append(
                    f"  [{entity_num}] 🐾 {ANSIColors.neutral_name(monster_name)}"
                )

        # 적대적인 몬스터 표시
        if hostile_monsters:
            from ..core.localization import get_localization_manager

            localization = get_localization_manager()

            lines.append("")
            lines.append(localization.get_message("room.monsters_here", self.locale))
            for monster in hostile_monsters:
                monster_name = monster.get("name", "Unknown" if self.locale == "en" else "알 수 없음")
                monster_id = monster.get("id", "")
                entity_num = id_to_number.get(monster_id, "?")
                lines.append(
                    f"  [{entity_num}] {ANSIColors.monster_name(monster_name)}"
                )

        lines.append("")
        return "\r\n".join(lines)

    def _is_friendly_faction(
        self, player_faction: str, monster_faction: Optional[str]
    ) -> bool:
        """플레이어와 몬스터 종족 간의 우호 관계 확인

        Args:
            player_faction: 플레이어 종족 ID
            monster_faction: 몬스터 종족 ID

        Returns:
            bool: 우호 관계이면 True (같은 종족 또는 동맹)
        """
        # 같은 종족이면 우호적
        if monster_faction == player_faction:
            return True

        # 몬스터 종족이 없으면 적대적으로 간주
        if not monster_faction:
            return False

        # 하드코딩된 우호 종족 관계 (추후 DB에서 동적으로 로드 가능)
        friendly_factions = {
            "ash_knights": ["ash_knights"],  # 같은 종족만 우호적
            # 추가 동맹 종족은 여기에 추가
        }

        # 우호 종족이면 True
        if player_faction in friendly_factions:
            if monster_faction in friendly_factions[player_faction]:
                return True

        return False

    def _is_neutral_faction(
        self, player_faction: str, monster_faction: Optional[str]
    ) -> bool:
        """플레이어와 몬스터 종족 간의 중립 관계 확인

        Args:
            player_faction: 플레이어 종족 ID
            monster_faction: 몬스터 종족 ID

        Returns:
            bool: 중립 관계이면 True
        """
        # 몬스터 종족이 없으면 중립이 아님
        if not monster_faction:
            return False

        # 하드코딩된 중립 종족 관계 (추후 DB에서 동적으로 로드 가능)
        neutral_factions = {
            "ash_knights": ["animals"],  # 동물은 중립
        }

        # 중립 종족이면 True
        if player_faction in neutral_factions:
            if monster_faction in neutral_factions[player_faction]:
                return True

        return False

    async def send_text(self, text: str, newline: bool = True) -> bool:
        """
        클라이언트에게 텍스트 전송 (Transport 위임)

        Args:
            text: 전송할 텍스트
            newline: 줄바꿈 추가 여부

        Returns:
            bool: 전송 성공 여부
        """
        return await self._transport.send_text(text, newline)

    async def send_colored_text(
        self, text: str, color_code: str = "", newline: bool = True
    ) -> bool:
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

    async def send_success(
        self, message: str, data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        클라이언트에게 성공 메시지 전송 (녹색)

        Args:
            message: 성공 메시지
            data: 추가 데이터 (선택사항, Telnet에서는 무시됨)

        Returns:
            bool: 전송 성공 여부
        """
        return await self.send_colored_text(f"\n{message}", "\033[32m")

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
        클라이언트에게 프롬프트 전송 (줄바꿈 없음, Transport 위임)

        Args:
            prompt: 프롬프트 문자열

        Returns:
            bool: 전송 성공 여부
        """
        return await self._transport.send_prompt(prompt)

    async def disable_echo(self) -> None:
        """클라이언트 에코 비활성화 (패스워드 입력용, Transport 위임)"""
        await self._transport.disable_echo()

    async def enable_echo(self) -> None:
        """클라이언트 에코 활성화 (일반 입력용, Transport 위임)"""
        await self._transport.enable_echo()

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
            "locale": self.locale,
            "use_ansi_colors": self.use_ansi_colors,
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
