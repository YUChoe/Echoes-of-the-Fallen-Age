# -*- coding: utf-8 -*-
"""좌표 관련 유틸리티 함수들"""

from enum import Enum
from typing import Tuple, Optional
from dataclasses import dataclass

class Direction(Enum):
    """방향 열거형"""
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"


def get_direction_from_string(direction_str: str) -> Optional[Direction]:
    """
    문자열을 Direction 열거형으로 변환

    Args:
        direction_str: 방향 문자열 (north, south, east, west, n, s, e, w)

    Returns:
        Direction 또는 None
    """
    direction_str = direction_str.lower().strip()

    # 축약형 매핑
    direction_map = {
        'n': Direction.NORTH,
        'north': Direction.NORTH,
        's': Direction.SOUTH,
        'south': Direction.SOUTH,
        'e': Direction.EAST,
        'east': Direction.EAST,
        'w': Direction.WEST,
        'west': Direction.WEST
    }

    return direction_map.get(direction_str)

@dataclass
class RoomCoordination():
    x:int
    y:int
    id: str  # 맘에 안듬 uuid 가 str은 아니지 않나?
    direction: Direction


async def get_exits(game_engine, current_room_id, x, y) -> list[RoomCoordination] :
    current_room = await game_engine.world_manager.get_room(current_room_id)
    if not current_room:
        return []

    exits = []
    if current_room.x is not None and current_room.y is not None:
        # 각 방향에 대해 방이 존재하는지 확인
        for direction in Direction:
            new_x, new_y = calculate_new_coordinates(current_room.x, current_room.y, direction)
            adjacent_room = await game_engine.world_manager.get_room_at_coordinates(new_x, new_y)
            if adjacent_room:
                exits.append(RoomCoordination(new_x, new_y, adjacent_room.id, direction))
    return exits


def calculate_new_coordinates(x: int, y: int, direction: Direction) -> Tuple[int, int]:
    """
    현재 좌표에서 방향에 따른 새 좌표 계산

    좌표 시스템:
    - x+1: 동쪽 (east)
    - x-1: 서쪽 (west)
    - y+1: 북쪽 (north)
    - y-1: 남쪽 (south)

    Args:
        x: 현재 X 좌표
        y: 현재 Y 좌표
        direction: 이동 방향

    Returns:
        새로운 (x, y) 좌표
    """
    if direction == Direction.EAST:
        return (x + 1, y)
    elif direction == Direction.WEST:
        return (x - 1, y)
    elif direction == Direction.NORTH:
        return (x, y + 1)
    elif direction == Direction.SOUTH:
        return (x, y - 1)
    else:
        return (x, y)  # 변화 없음


def get_opposite_direction(direction: Direction) -> Direction:
    """
    반대 방향 반환

    Args:
        direction: 원래 방향

    Returns:
        반대 방향
    """
    opposite_map = {
        Direction.NORTH: Direction.SOUTH,
        Direction.SOUTH: Direction.NORTH,
        Direction.EAST: Direction.WEST,
        Direction.WEST: Direction.EAST
    }

    return opposite_map[direction]


def get_direction_between_coordinates(from_x: int, from_y: int, to_x: int, to_y: int) -> Optional[Direction]:
    """
    두 좌표 사이의 방향 계산 (인접한 좌표만)

    Args:
        from_x: 시작 X 좌표
        from_y: 시작 Y 좌표
        to_x: 목적지 X 좌표
        to_y: 목적지 Y 좌표

    Returns:
        Direction 또는 None (인접하지 않은 경우)
    """
    dx = to_x - from_x
    dy = to_y - from_y

    # 인접한 좌표만 처리 (대각선 제외)
    if abs(dx) + abs(dy) != 1:
        return None

    if dx == 1 and dy == 0:
        return Direction.EAST
    elif dx == -1 and dy == 0:
        return Direction.WEST
    elif dx == 0 and dy == 1:
        return Direction.NORTH
    elif dx == 0 and dy == -1:
        return Direction.SOUTH

    return None


def get_available_directions_from_coordinates(x: int, y: int, room_checker=None) -> list[str]:
    """
    좌표에서 사용 가능한 방향들 반환

    Args:
        x: 현재 X 좌표
        y: 현재 Y 좌표
        room_checker: 방 존재 여부를 확인하는 함수 (선택적)

    Returns:
        사용 가능한 방향 문자열 리스트
    """
    directions = []

    # 모든 방향에 대해 확인
    for direction in Direction:
        new_x, new_y = calculate_new_coordinates(x, y, direction)

        # room_checker가 제공된 경우 실제 방 존재 여부 확인
        if room_checker:
            if room_checker(new_x, new_y):
                directions.append(direction.value)
        else:
            # 기본적으로 모든 방향 허용
            directions.append(direction.value)

    return directions


def format_coordinates(x: int, y: int) -> str:
    """
    좌표를 문자열로 포맷팅

    Args:
        x: X 좌표
        y: Y 좌표

    Returns:
        포맷팅된 좌표 문자열
    """
    return f"({x}, {y})"


def is_valid_coordinate(x: int, y: int, min_x: int = -100, max_x: int = 100, min_y: int = -100, max_y: int = 100) -> bool:
    """
    좌표가 유효한 범위 내에 있는지 확인

    Args:
        x: X 좌표
        y: Y 좌표
        min_x: 최소 X 좌표
        max_x: 최대 X 좌표
        min_y: 최소 Y 좌표
        max_y: 최대 Y 좌표

    Returns:
        유효성 여부
    """
    return min_x <= x <= max_x and min_y <= y <= max_y