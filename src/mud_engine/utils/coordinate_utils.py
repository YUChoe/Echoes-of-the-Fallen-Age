# -*- coding: utf-8 -*-
"""좌표 기반 이동 시스템 유틸리티"""

from typing import Dict, Tuple, Optional
from enum import Enum


class Direction(Enum):
    """방향 열거형"""
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"
    NORTHEAST = "northeast"
    NORTHWEST = "northwest"
    SOUTHEAST = "southeast"
    SOUTHWEST = "southwest"
    UP = "up"
    DOWN = "down"


# 방향별 좌표 변화량
DIRECTION_OFFSETS: Dict[Direction, Tuple[int, int]] = {
    Direction.NORTH: (0, 1),
    Direction.SOUTH: (0, -1),
    Direction.EAST: (1, 0),
    Direction.WEST: (-1, 0),
    Direction.NORTHEAST: (1, 1),
    Direction.NORTHWEST: (-1, 1),
    Direction.SOUTHEAST: (1, -1),
    Direction.SOUTHWEST: (-1, -1),
    Direction.UP: (0, 0),  # 수직 이동은 좌표 변화 없음
    Direction.DOWN: (0, 0),  # 수직 이동은 좌표 변화 없음
}

# 반대 방향 매핑
OPPOSITE_DIRECTIONS: Dict[Direction, Direction] = {
    Direction.NORTH: Direction.SOUTH,
    Direction.SOUTH: Direction.NORTH,
    Direction.EAST: Direction.WEST,
    Direction.WEST: Direction.EAST,
    Direction.NORTHEAST: Direction.SOUTHWEST,
    Direction.SOUTHWEST: Direction.NORTHEAST,
    Direction.NORTHWEST: Direction.SOUTHEAST,
    Direction.SOUTHEAST: Direction.NORTHWEST,
    Direction.UP: Direction.DOWN,
    Direction.DOWN: Direction.UP,
}


def get_direction_from_string(direction_str: str) -> Optional[Direction]:
    """문자열을 Direction 열거형으로 변환"""
    direction_str = direction_str.lower().strip()
    
    # 축약형 지원
    abbreviations = {
        'n': Direction.NORTH,
        's': Direction.SOUTH,
        'e': Direction.EAST,
        'w': Direction.WEST,
        'ne': Direction.NORTHEAST,
        'nw': Direction.NORTHWEST,
        'se': Direction.SOUTHEAST,
        'sw': Direction.SOUTHWEST,
        'u': Direction.UP,
        'd': Direction.DOWN,
    }
    
    # 축약형 확인
    if direction_str in abbreviations:
        return abbreviations[direction_str]
    
    # 전체 이름 확인
    for direction in Direction:
        if direction.value == direction_str:
            return direction
    
    return None


def calculate_new_coordinates(x: int, y: int, direction: Direction) -> Tuple[int, int]:
    """현재 좌표에서 특정 방향으로 이동했을 때의 새 좌표 계산"""
    if direction not in DIRECTION_OFFSETS:
        raise ValueError(f"지원되지 않는 방향입니다: {direction}")
    
    dx, dy = DIRECTION_OFFSETS[direction]
    return x + dx, y + dy


def get_direction_between_coordinates(from_x: int, from_y: int, to_x: int, to_y: int) -> Optional[Direction]:
    """두 좌표 사이의 방향 계산"""
    dx = to_x - from_x
    dy = to_y - from_y
    
    # 정확한 방향 매칭
    for direction, (offset_x, offset_y) in DIRECTION_OFFSETS.items():
        if dx == offset_x and dy == offset_y:
            return direction
    
    return None


def is_adjacent_coordinates(x1: int, y1: int, x2: int, y2: int) -> bool:
    """두 좌표가 인접한지 확인"""
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    
    # 8방향 인접 (대각선 포함) 또는 같은 위치
    return dx <= 1 and dy <= 1


def get_distance(x1: int, y1: int, x2: int, y2: int) -> float:
    """두 좌표 사이의 거리 계산 (유클리드 거리)"""
    return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5


def get_manhattan_distance(x1: int, y1: int, x2: int, y2: int) -> int:
    """두 좌표 사이의 맨하탄 거리 계산"""
    return abs(x2 - x1) + abs(y2 - y1)