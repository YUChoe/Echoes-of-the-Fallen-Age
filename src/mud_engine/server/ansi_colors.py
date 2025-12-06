# -*- coding: utf-8 -*-
"""ANSI 색상 코드 정의"""


class ANSIColors:
    """ANSI 색상 코드 상수"""

    # 기본 색상
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"
    BLINK = "\033[5m"
    REVERSE = "\033[7m"
    HIDDEN = "\033[8m"

    # 전경색 (텍스트 색상)
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # 밝은 전경색
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

    # 배경색
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"

    @staticmethod
    def colorize(text: str, color: str) -> str:
        """텍스트에 색상 적용

        Args:
            text: 색상을 적용할 텍스트
            color: ANSI 색상 코드

        Returns:
            str: 색상이 적용된 텍스트
        """
        return f"{color}{text}{ANSIColors.RESET}"

    @staticmethod
    def bold(text: str) -> str:
        """텍스트를 굵게 표시"""
        return f"{ANSIColors.BOLD}{text}{ANSIColors.RESET}"

    @staticmethod
    def error(text: str) -> str:
        """오류 메시지 (빨간색)"""
        return ANSIColors.colorize(text, ANSIColors.RED)

    @staticmethod
    def success(text: str) -> str:
        """성공 메시지 (녹색)"""
        return ANSIColors.colorize(text, ANSIColors.GREEN)

    @staticmethod
    def info(text: str) -> str:
        """정보 메시지 (청록색)"""
        return ANSIColors.colorize(text, ANSIColors.CYAN)

    @staticmethod
    def warning(text: str) -> str:
        """경고 메시지 (노란색)"""
        return ANSIColors.colorize(text, ANSIColors.YELLOW)

    @staticmethod
    def room_name(text: str) -> str:
        """방 이름 (밝은 파란색, 굵게)"""
        return f"{ANSIColors.BOLD}{ANSIColors.BRIGHT_BLUE}{text}{ANSIColors.RESET}"

    @staticmethod
    def player_name(text: str) -> str:
        """플레이어 이름 (밝은 청록색)"""
        return ANSIColors.colorize(text, ANSIColors.BRIGHT_CYAN)

    @staticmethod
    def npc_name(text: str) -> str:
        """NPC 이름 (밝은 마젠타)"""
        return ANSIColors.colorize(text, ANSIColors.BRIGHT_MAGENTA)

    @staticmethod
    def monster_name(text: str) -> str:
        """몬스터 이름 (밝은 빨간색)"""
        return ANSIColors.colorize(text, ANSIColors.BRIGHT_RED)

    @staticmethod
    def item_name(text: str) -> str:
        """아이템 이름 (밝은 노란색)"""
        return ANSIColors.colorize(text, ANSIColors.BRIGHT_YELLOW)

    @staticmethod
    def exit_direction(text: str) -> str:
        """출구 방향 (밝은 녹색)"""
        return ANSIColors.colorize(text, ANSIColors.BRIGHT_GREEN)

    @staticmethod
    def neutral_name(text: str) -> str:
        """중립 몬스터/동물 이름 (밝은 흰색)"""
        return ANSIColors.colorize(text, ANSIColors.BRIGHT_WHITE)
