#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""통합 월드 맵 HTML 생성 유틸리티"""

import json
import logging
from typing import Dict, List, Tuple, Optional, Any, cast
from pathlib import Path

from ..database.connection import DatabaseManager
from .coordinate_utils import Direction, calculate_new_coordinates

logger = logging.getLogger(__name__)


class MapExporter:
    """월드 맵 HTML 생성기"""

    def __init__(self, db_manager: DatabaseManager):
        """
        MapExporter 초기화

        Args:
            db_manager: 데이터베이스 매니저 인스턴스
        """
        self.db_manager = db_manager

    async def get_all_rooms(self) -> List[Tuple[Any, ...]]:
        """모든 방 정보 가져오기"""
        cursor = await self.db_manager.execute("""
            SELECT id, description_ko, description_en, x, y, blocked_exits
            FROM rooms
            WHERE x IS NOT NULL AND y IS NOT NULL
            ORDER BY x, y
        """)
        result = await cursor.fetchall()
        return [tuple(row) for row in result]

    async def get_monsters_by_room(self) -> Dict[str, int]:
        """방별 몬스터 수 가져오기 (하위 호환성을 위한 메서드)"""
        factions_by_room = await self.get_factions_by_room()
        monsters_by_room = {}

        for room_id, factions in factions_by_room.items():
            total_monsters = sum(factions.values())
            if total_monsters > 0:
                monsters_by_room[room_id] = total_monsters

        return monsters_by_room



    async def get_entities_by_room_and_faction(self) -> Dict[str, Dict[str, Dict[str, int]]]:
        """방별 엔티티를 종족별로 분류해서 가져오기"""
        entities_by_room: Dict[str, Dict[str, Dict[str, int]]] = {}

        # monsters 테이블에서 가져오기
        cursor = await self.db_manager.execute("""
            SELECT r.id, m.faction_id, COUNT(*) as count
            FROM rooms r
            INNER JOIN monsters m ON (r.x = m.x AND r.y = m.y)
            WHERE m.is_alive = 1
            AND m.x IS NOT NULL AND m.y IS NOT NULL
            GROUP BY r.id, m.faction_id
        """)
        monsters_result = await cursor.fetchall()

        for room_id, faction_id, count in monsters_result:
            if room_id not in entities_by_room:
                entities_by_room[room_id] = {}
            if faction_id not in entities_by_room[room_id]:
                entities_by_room[room_id][faction_id] = {'monsters': 0}
            entities_by_room[room_id][faction_id]['monsters'] += count

        return entities_by_room

    def get_faction_colors(self) -> Dict[str, str]:
        """종족별 색상 매핑 반환"""
        return {
            'ash_knights': '#4a9eff',      # 파란색 (플레이어 종족)
            'goblins': '#ff4444',          # 빨간색 (적대적)
            'animals': '#ffa500',          # 주황색 (중립/동물)
            'bandits': '#8b0000',          # 진한 빨간색 (적대적)
            'merchants': '#32cd32',        # 라임그린 (우호적)
            'guards': '#4169e1',           # 로얄블루 (우호적)
            None: '#888888'                # 회색 (종족 없음)
        }

    async def get_factions_by_room(self) -> Dict[str, Dict[str, int]]:
        cursor = await self.db_manager.execute("""
            SELECT r.id, m.faction_id, COUNT(*) as count
            FROM rooms r
            INNER JOIN monsters m ON (r.x = m.x AND r.y = m.y)
            WHERE m.is_alive = 1
            AND m.x IS NOT NULL AND m.y IS NOT NULL
            GROUP BY r.id, m.faction_id
        """)
        result = await cursor.fetchall()

        # 방별 종족 카운트 딕셔너리 생성
        factions_by_room: Dict[str, Dict[str, int]] = {}
        for room_id, faction_id, count in result:
            if room_id not in factions_by_room:
                factions_by_room[room_id] = {}
            factions_by_room[room_id][faction_id or 'unknown'] = count

        return factions_by_room

    async def get_players_by_room(self) -> Dict[str, int]:
        """방별 플레이어 수 가져오기 (좌표 기반)"""
        cursor = await self.db_manager.execute("""
            SELECT r.id, COUNT(*) as count
            FROM players p
            INNER JOIN rooms r ON (p.last_room_x = r.x AND p.last_room_y = r.y)
            GROUP BY r.id
        """)
        result = await cursor.fetchall()
        return {row[0]: row[1] for row in result}


    async def get_faction_relations(self) -> Tuple[List[Tuple[Any, ...]], List[Tuple[Any, ...]]]:
        """종족 관계 정보 가져오기"""
        # 종족 정보
        cursor = await self.db_manager.execute("""
            SELECT id, name_ko, name_en
            FROM factions
            ORDER BY id
        """)
        factions_result = await cursor.fetchall()

        # 종족 관계
        cursor = await self.db_manager.execute("""
            SELECT faction_a_id, faction_b_id, relation_value, relation_status
            FROM faction_relations
            WHERE faction_a_id = 'ash_knights'
            ORDER BY faction_b_id
        """)
        relations_result = await cursor.fetchall()

        return [tuple(row) for row in factions_result], [tuple(row) for row in relations_result]

    async def get_all_players(self) -> List[Tuple[Any, ...]]:
        """모든 플레이어 정보 가져오기 (좌표 기반)"""
        cursor = await self.db_manager.execute("""
            SELECT p.username, p.last_room_x, p.last_room_y, p.is_admin, p.created_at, p.last_login
            FROM players p
            ORDER BY p.username
        """)
        result = await cursor.fetchall()
        return [tuple(row) for row in result]

    async def get_room_details(self) -> Dict[str, Dict[str, Any]]:
        """모든 방의 상세 정보를 가져오기 (클릭 시 표시용)"""
        room_details = {}

        # 방 기본 정보
        cursor = await self.db_manager.execute("""
            SELECT id, description_ko, description_en, x, y
            FROM rooms
            WHERE x IS NOT NULL AND y IS NOT NULL
        """)
        rooms = await cursor.fetchall()

        for room in rooms:
            room_id, desc_ko, desc_en, x, y = room
            room_details[room_id] = {
                'description_ko': desc_ko,
                'description_en': desc_en,
                'x': x,
                'y': y,
                'creatures': [],  # 몬스터와 NPC를 통합
                'players': [],
                'items': []
            }

        # 모든 생명체 정보 (몬스터/NPC 구분 없이 종족별로)
        cursor = await self.db_manager.execute("""
            SELECT r.id, m.name_ko, m.name_en,
                   COALESCE(
                       json_extract(m.stats, '$.current_hp'),
                       json_extract(m.stats, '$.max_hp'),
                       20
                   ) as current_hp,
                   COALESCE(
                       json_extract(m.stats, '$.max_hp'),
                       20
                   ) as max_hp,
                   m.faction_id
            FROM rooms r
            INNER JOIN monsters m ON (r.x = m.x AND r.y = m.y)
            WHERE m.is_alive = 1 AND r.x IS NOT NULL AND r.y IS NOT NULL
            ORDER BY r.id, m.faction_id, m.name_ko
        """)
        creatures = await cursor.fetchall()

        for creature in creatures:
            room_id, name_ko, name_en, current_hp, max_hp, faction_id = creature
            if room_id in room_details:
                room_details[room_id]['creatures'].append({
                    'name_ko': name_ko,
                    'name_en': name_en,
                    'hp': f"{current_hp}/{max_hp}",
                    'faction': faction_id or 'unknown'
                })

        # 플레이어 정보 (좌표 기반)
        cursor = await self.db_manager.execute("""
            SELECT r.id, p.username, p.is_admin
            FROM players p
            INNER JOIN rooms r ON (p.last_room_x = r.x AND p.last_room_y = r.y)
            ORDER BY p.username
        """)
        players = await cursor.fetchall()

        for player in players:
            room_id, username, is_admin = player
            if room_id in room_details:
                room_details[room_id]['players'].append({
                    'username': username,
                    'is_admin': is_admin
                })

        # 아이템 정보 (게임 오브젝트에서)
        cursor = await self.db_manager.execute("""
            SELECT r.id, go.name_ko, go.name_en
            FROM rooms r
            INNER JOIN game_objects go ON (r.id = go.location_id)
            WHERE go.location_type = 'room'
            AND r.x IS NOT NULL AND r.y IS NOT NULL
            ORDER BY r.id, go.name_ko
        """)
        items = await cursor.fetchall()

        for item in items:
            room_id, name_ko, name_en = item
            if room_id in room_details:
                room_details[room_id]['items'].append({
                    'name_ko': name_ko,
                    'name_en': name_en,
                    'type': 'item'  # object_type 제거됨, 기본값 사용
                })

        # enter 연결 정보 추가
        cursor = await self.db_manager.execute("""
            SELECT r.id, rc.to_x, rc.to_y
            FROM rooms r
            INNER JOIN room_connections rc ON (r.x = rc.from_x AND r.y = rc.from_y)
            WHERE r.x IS NOT NULL AND r.y IS NOT NULL
        """)
        enter_connections = await cursor.fetchall()

        for connection in enter_connections:
            room_id, to_x, to_y = connection
            if room_id in room_details:
                if 'enter_connections' not in room_details[room_id]:
                    room_details[room_id]['enter_connections'] = []
                room_details[room_id]['enter_connections'].append({
                    'to_x': to_x,
                    'to_y': to_y
                })

        return room_details

    def calculate_coordinate_based_exits(self, x: int, y: int, all_rooms_coords: Dict[Tuple[int, int], str], enter_connections: Dict[Tuple[int, int], Tuple[int, int]] = None, blocked_exits: List[str] = None) -> Dict[str, str]:
        """좌표 기반으로 출구를 계산합니다 (enter 연결 포함)."""
        exits = {}
        blocked = set(blocked_exits) if blocked_exits else set()

        # 모든 방향에 대해 인접한 방이 있는지 확인
        for direction in Direction:
            try:
                if direction.value in blocked:
                    continue  # 막힌 방향은 건너뜀

                adj_x, adj_y = calculate_new_coordinates(x, y, direction)

                # 해당 좌표에 방이 있는지 확인
                if (adj_x, adj_y) in all_rooms_coords:
                    target_room_id = all_rooms_coords[(adj_x, adj_y)]
                    exits[direction.value] = target_room_id
            except Exception:
                # UP, DOWN 등 좌표 변화가 없는 방향은 무시
                continue

        # enter 연결 확인 (미리 가져온 데이터 사용)
        if enter_connections and (x, y) in enter_connections:
            to_x, to_y = enter_connections[(x, y)]
            if (to_x, to_y) in all_rooms_coords:
                target_room_id = all_rooms_coords[(to_x, to_y)]
                exits['enter'] = target_room_id

        return exits

    def generate_html_with_factions(self, rooms_data: List[Tuple[Any, ...]], entities_by_room: Dict[str, Dict[str, Dict[str, int]]],
                                   players_by_room: Dict[str, int], factions: List[Tuple[Any, ...]], relations: List[Tuple[Any, ...]],
                                   all_players: List[Tuple[Any, ...]], room_details: Dict[str, Dict[str, Any]],
                                   faction_colors: Dict[str, str], enter_connections: Dict[Tuple[int, int], Tuple[int, int]] = None) -> str:
        """종족별 색상을 적용한 HTML 생성"""
        # 방 데이터를 그리드에 매핑
        grid: Dict[Tuple[int, int], Dict[str, Any]] = {}
        all_rooms_coords: Dict[Tuple[int, int], str] = {}  # 좌표 -> 방 ID 매핑

        # 1단계: 모든 방의 좌표 정보 수집
        for room in rooms_data:
            room_id = room[0]
            desc_ko = room[1]
            desc_en = room[2]
            x = room[3]
            y = room[4]

            # x, y 좌표가 있으면 직접 사용
            if x is not None and y is not None:
                coord = (x, y)
                all_rooms_coords[coord] = room_id

        # 2단계: 각 방의 좌표 기반 출구 계산
        for room in rooms_data:
            room_id = room[0]
            desc_ko = room[1]
            desc_en = room[2]
            x = room[3]
            y = room[4]
            raw_blocked = room[5] if len(room) > 5 else "[]"

            room_blocked: List[str] = []
            if isinstance(raw_blocked, str):
                try:
                    room_blocked = json.loads(raw_blocked)
                except (json.JSONDecodeError, TypeError):
                    room_blocked = []

            # x, y 좌표가 있으면 직접 사용
            if x is not None and y is not None:
                coord = (x, y)

                # 좌표 기반 출구 계산
                exits = self.calculate_coordinate_based_exits(coord[0], coord[1], all_rooms_coords, blocked_exits=room_blocked)

                # description에서 첫 줄을 이름으로 사용
                name_ko = desc_ko.split('\n')[0] if desc_ko else room_id

                grid[coord] = {
                    'id': room_id,
                    'name_ko': name_ko,
                    'exits': exits,
                    'blocked_exits': room_blocked,
                }

        # 그리드 범위 계산
        if not grid:
            return "<html><body>No rooms found</body></html>"

        min_x = min(c[0] for c in grid.keys())
        max_x = max(c[0] for c in grid.keys())
        min_y = min(c[1] for c in grid.keys())
        max_y = max(c[1] for c in grid.keys())

        # CSS 스타일 정의 (종족별 색상 지원)
        css_style = """
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 20px;
                background-color: #1a1a1a;
                color: #e0e0e0;
                overflow: auto;
            }
            h1 {
                text-align: center;
                color: #4a9eff;
                text-shadow: 0 0 10px rgba(74, 158, 255, 0.5);
            }
            .map-container {
                margin: 20px auto;
                overflow: auto;
                max-width: 100%;
            }
            table {
                border-collapse: collapse;
                margin: 20px auto;
                background-color: #2a2a2a;
                box-shadow: 0 0 20px rgba(0, 0, 0, 0.5);
            }
            .map-container td {
                width: 15px;
                height: 15px;
                border: 1px solid #333;
                text-align: center;
                vertical-align: middle;
                font-size: 0;
                padding: 0;
                position: relative;
                cursor: pointer;
            }
            td:hover {
                z-index: 100;
                box-shadow: 0 0 15px rgba(74, 158, 255, 0.8);
                border: 2px solid #4a9eff;
            }
            td:hover .tooltip {
                display: none;
            }
            .empty {
                background-color: #1a1a1a;
                border: 1px solid #222;
            }
            .room {
                background-color: #d0d0d0;
                color: #333;
                border: 1px solid #999;
                position: relative;
            }
            .indicators {
                position: absolute;
                top: 2px;
                left: 2px;
                display: flex;
                gap: 1px;
                pointer-events: none;
                flex-wrap: wrap;
                max-width: 11px;
            }
            .indicator {
                width: 3px;
                height: 3px;
                border-radius: 50%;
                border: 0.5px solid rgba(0,0,0,0.3);
            }
            .player-indicator {
                background-color: #00ff00;
            }
            .tooltip {
                display: none;
                position: fixed;
                background-color: rgba(0, 0, 0, 0.95);
                color: #fff;
                padding: 6px 10px;
                border-radius: 4px;
                white-space: nowrap;
                font-size: 13px;
                z-index: 10000;
                border: 1px solid #4a9eff;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
                pointer-events: none;
            }
            .legend {
                display: flex;
                justify-content: center;
                gap: 20px;
                margin: 20px 0;
                flex-wrap: wrap;
            }
            .legend-item {
                display: flex;
                align-items: center;
                gap: 10px;
            }
            .legend-box {
                width: 30px;
                height: 30px;
                border: 2px solid #444;
            }
            .stats {
                text-align: center;
                margin: 20px 0;
                padding: 15px;
                background-color: #2a2a2a;
                border-radius: 8px;
            }
            .stats span {
                margin: 0 15px;
                color: #4a9eff;
            }
            .main-content {
                display: flex;
                gap: 20px;
                align-items: flex-start;
            }
            .room-details {
                position: fixed;
                right: 20px;
                top: 120px;
                width: 300px;
                background-color: #2a2a2a;
                border: 1px solid #444;
                border-radius: 8px;
                padding: 15px;
                display: none;
                max-height: 70vh;
                overflow-y: auto;
                z-index: 1000;
            }
            .room-details h3 {
                margin-top: 0;
                color: #4a9eff;
                font-size: 13px;
            }
            .room-details .description {
                font-size: 13px;
                line-height: 1.4;
                margin-bottom: 15px;
                color: #e0e0e0;
            }
            .room-details .section {
                margin-bottom: 10px;
            }
            .room-details .section-title {
                font-size: 13px;
                font-weight: bold;
                color: #4a9eff;
                margin-bottom: 5px;
            }
            .room-details .item-list {
                font-size: 13px;
                color: #ccc;
                margin-left: 10px;
            }
            .room-details .close-btn {
                position: absolute;
                top: 5px;
                right: 10px;
                background: none;
                border: none;
                color: #999;
                font-size: 16px;
                cursor: pointer;
            }
            .room-details .close-btn:hover {
                color: #fff;
            }
        """

        html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>The Chronicles of Karnas: Divided Dominion - 통합 월드 맵</title>
    <style>
{css_style}
    </style>
</head>
<body>
    <h1>🗺️ The Chronicles of Karnas: Divided Dominion - 통합 월드 맵</h1>

    <div class="stats">
        <span>총 방 개수: <strong>{len(rooms_data)}</strong></span>
        <span>그리드 크기: <strong>{max_x - min_x + 1}x{max_y - min_y + 1}</strong></span>
        <span>생성 시간: <strong>{self._get_current_time()}</strong></span>
        <span>자동 새로고침: <strong id="refreshCountdown">60</strong>초 후</span>
    </div>

    <div class="main-content">
        <div class="map-container">
            <table>
"""

        # 테이블 생성 (종족별 색상 적용)
        for y in range(max_y, min_y - 1, -1):  # y 좌표를 역순으로 렌더링
            html += "            <tr>\n"
            for x in range(min_x, max_x + 1):
                if (x, y) in grid:
                    room_data = grid[(x, y)]
                    room_id = str(room_data['id'])
                    exits = cast(Dict[str, str], room_data['exits'])

                    # 모든 방을 동일한 스타일로 표시
                    css_class = 'room'

                    # 출구 화살표
                    exit_arrows = ''
                    if 'north' in exits:
                        exit_arrows += '↑'
                    if 'south' in exits:
                        exit_arrows += '↓'
                    if 'east' in exits:
                        exit_arrows += '→'
                    if 'west' in exits:
                        exit_arrows += '←'
                    if 'enter' in exits:
                        exit_arrows += '🚪'

                    # 엔티티 정보 수집 (종족별)
                    has_player = room_id in players_by_room
                    player_count = players_by_room.get(room_id, 0)

                    room_entities = entities_by_room.get(room_id, {})

                    # 인디케이터 HTML 생성 (종족별 색상)
                    indicators_html = ''
                    entity_info = []

                    if has_player or room_entities:
                        indicators_html = '<div class="indicators">'

                        # 플레이어 인디케이터
                        if has_player:
                            indicators_html += '<div class="indicator player-indicator"></div>'
                            entity_info.append(f"🟢플레이어:{player_count}")

                        # 종족별 엔티티 인디케이터 (종족당 1개씩만)
                        for faction_id, counts in room_entities.items():
                            total_count = counts['monsters']
                            if total_count > 0:
                                color = faction_colors.get(faction_id, faction_colors[None])
                                # 종족당 인디케이터 1개만 생성
                                indicators_html += f'<div class="indicator" style="background-color: {color};"></div>'

                                # 종족 이름 찾기
                                faction_name = next((f[1] for f in factions if f[0] == faction_id), faction_id or '기타')

                                if counts['monsters'] > 0:
                                    entity_info.append(f"🔴{faction_name}:{counts['monsters']}몬스터")

                        indicators_html += '</div>'

                    # tooltip에는 좌표와 엔티티 정보만 표시
                    entity_text = ' '.join(entity_info) if entity_info else ''
                    tooltip_text = f"{exit_arrows}({x},{y}) {entity_text}"

                    # 막힌 방향에 두꺼운 border 적용
                    blocked = room_data.get('blocked_exits', [])
                    border_style = ''
                    if blocked:
                        borders = []
                        if 'north' in blocked:
                            borders.append('border-top: 3px solid #ff4444')
                        if 'south' in blocked:
                            borders.append('border-bottom: 3px solid #ff4444')
                        if 'east' in blocked:
                            borders.append('border-right: 3px solid #ff4444')
                        if 'west' in blocked:
                            borders.append('border-left: 3px solid #ff4444')
                        if borders:
                            border_style = f' style="{"; ".join(borders)}"'

                    html += f"""                <td class="{css_class}"{border_style} onclick="showRoomDetails('{room_id}')">
                        {indicators_html}
                        <div class="tooltip">{tooltip_text}</div>
                    </td>\n"""
                else:
                    html += '                <td class="empty"></td>\n'
            html += "            </tr>\n"

        html += """        </table>
        </div>

        <!-- 방 상세 정보 패널 -->
        <div id="roomDetails" class="room-details">
            <button class="close-btn" onclick="hideRoomDetails()">×</button>
            <h3 id="roomTitle">방 정보</h3>
            <div id="roomDescription" class="description"></div>
            <div id="roomMonsters" class="section"></div>
            <div id="roomPlayers" class="section"></div>
            <div id="roomItems" class="section"></div>
        </div>
    </div>

    <div style="margin: 40px auto; margin-top: 0px; max-width: 800px; padding: 20px; padding-top: 10px; background-color: #2a2a2a; border-radius: 8px;">
        <h2 style="text-align: center; color: #4a9eff; margin-bottom: 20px; font-size: 16px;">🤝 종족 관계 (잿빛 기사단 기준)</h2>
        <table style="width: 100%; border-collapse: collapse;">
            <thead>
                <tr style="background-color: #1a1a1a;">
                    <th style="padding: 10px; border: 1px solid #444; color: #4a9eff;">종족</th>
                    <th style="padding: 10px; border: 1px solid #444; color: #4a9eff;">관계</th>
                    <th style="padding: 10px; border: 1px solid #444; color: #4a9eff;">우호도</th>
                    <th style="padding: 10px; border: 1px solid #444; color: #4a9eff;">설명</th>
                </tr>
            </thead>
            <tbody>
{faction_rows}
            </tbody>
        </table>
    </div>

    <div style="margin: 40px auto; margin-top: 0px; max-width: 800px; padding: 20px; padding-top: 10px; background-color: #2a2a2a; border-radius: 8px;">
        <h2 style="text-align: center; color: #4a9eff; margin-bottom: 20px; font-size: 16px;">👥 플레이어 목록</h2>
        <table style="width: 100%; border-collapse: collapse;">
            <thead>
                <tr style="background-color: #1a1a1a;">
                    <th style="padding: 10px; border: 1px solid #444; color: #4a9eff;">사용자명</th>
                    <th style="padding: 10px; border: 1px solid #444; color: #4a9eff;">현재 위치</th>
                    <th style="padding: 10px; border: 1px solid #444; color: #4a9eff;">가입일</th>
                    <th style="padding: 10px; border: 1px solid #444; color: #4a9eff;">마지막 로그인</th>
                </tr>
            </thead>
            <tbody>
{player_rows}
            </tbody>
        </table>
    </div>

    <script>
        // 방 상세 정보 데이터
        const roomDetailsData = {room_details_json};

        // 60초마다 페이지 자동 새로고침
        let refreshTimer;
        let refreshCountdown = 60;

        function startRefreshTimer() {
            refreshTimer = setInterval(function() {
                refreshCountdown--;
                updateRefreshDisplay();

                if (refreshCountdown <= 0) {
                    location.reload();
                }
            }, 1000);
        }

        function updateRefreshDisplay() {
            const refreshElement = document.getElementById('refreshCountdown');
            if (refreshElement) {
                refreshElement.textContent = refreshCountdown;
            }
        }

        function resetRefreshTimer() {
            clearInterval(refreshTimer);
            refreshCountdown = 60;
            updateRefreshDisplay();
            startRefreshTimer();
        }

        // 페이지 로드 시 타이머 시작
        window.addEventListener('load', function() {
            startRefreshTimer();
            updateRefreshDisplay();
        });

        // 클릭 이벤트에서 타이머 리셋 제거 - 자동 새로고침이 방해받지 않도록 함

        function showRoomDetails(roomId) {
            const details = roomDetailsData[roomId];
            if (!details) return;

            const panel = document.getElementById('roomDetails');
            const title = document.getElementById('roomTitle');
            const description = document.getElementById('roomDescription');
            const monsters = document.getElementById('roomMonsters');
            const players = document.getElementById('roomPlayers');
            const items = document.getElementById('roomItems');

            // 제목 설정
            title.textContent = '방 정보 (' + details.x + ', ' + details.y + ')';

            // 설명 설정 (한국어/영어)
            description.innerHTML =
                '<div><strong>한국어:</strong> ' + (details.description_ko || '설명 없음') + '</div>' +
                '<div style="margin-top: 8px;"><strong>English:</strong> ' + (details.description_en || 'No description') + '</div>';

            // 생명체 목록 (몬스터/NPC 통합)
            if (details.creatures && details.creatures.length > 0) {
                const creatureList = details.creatures.map(c =>
                    '• ' + c.name_ko + ' (' + c.name_en + ') HP:' + c.hp + ' [' + c.faction + ']'
                ).join('<br>');
                monsters.innerHTML =
                    '<div class="section-title">생명체 (' + details.creatures.length + ')</div>' +
                    '<div class="item-list">' + creatureList + '</div>';
            } else {
                monsters.innerHTML = '';
            }

            // 플레이어 목록
            if (details.players && details.players.length > 0) {
                const playerList = details.players.map(p =>
                    '• ' + p.username + (p.is_admin ? ' (관리자)' : '')
                ).join('<br>');
                players.innerHTML =
                    '<div class="section-title">플레이어 (' + details.players.length + ')</div>' +
                    '<div class="item-list">' + playerList + '</div>';
            } else {
                players.innerHTML = '';
            }

            // 아이템 목록
            if (details.items && details.items.length > 0) {
                const itemList = details.items.map(i =>
                    '• ' + i.name_ko + ' (' + i.name_en + ') [' + i.type + ']'
                ).join('<br>');
                items.innerHTML =
                    '<div class="section-title">아이템 (' + details.items.length + ')</div>' +
                    '<div class="item-list">' + itemList + '</div>';
            } else {
                items.innerHTML = '';
            }

            // Enter 연결 정보
            if (details.enter_connections && details.enter_connections.length > 0) {
                const enterSection =
                    '<div class="section-title">🚪 Enter 연결</div>' +
                    '<div class="item-list">' +
                    details.enter_connections.map(c => '• → (' + c.to_x + ', ' + c.to_y + ')').join('<br>') +
                    '</div>';
                items.innerHTML += enterSection;
            }

            panel.style.display = 'block';
        }

        function hideRoomDetails() {
            document.getElementById('roomDetails').style.display = 'none';
        }

        // tooltip을 마우스 커서 위치에 표시
        document.querySelectorAll('.map-container td.room').forEach(function(td) {
            var tooltip = td.querySelector('.tooltip');
            if (!tooltip) return;
            td.addEventListener('mouseenter', function(e) {
                tooltip.style.display = 'block';
                tooltip.style.left = (e.clientX + 15) + 'px';
                tooltip.style.top = (e.clientY - 10) + 'px';
            });
            td.addEventListener('mousemove', function(e) {
                tooltip.style.left = (e.clientX + 15) + 'px';
                tooltip.style.top = (e.clientY - 10) + 'px';
            });
            td.addEventListener('mouseleave', function() {
                tooltip.style.display = 'none';
            });
        });
    </script>
</body>
</html>
"""

        # 종족 관계 테이블 생성
        faction_rows = ""
        relation_colors = {
            'ALLIED': '#00ff00',
            'FRIENDLY': '#90ee90',
            'NEUTRAL': '#ffff00',
            'UNFRIENDLY': '#ffa500',
            'HOSTILE': '#ff0000'
        }

        for faction_a, faction_b, value, status in relations:
            # 종족 이름 찾기
            faction_name = next((f[1] for f in factions if f[0] == faction_b), faction_b)
            color = relation_colors.get(status, '#888')

            # 설명 생성
            if status == 'HOSTILE':
                desc = '적대적 - 공격 대상'
            elif status == 'UNFRIENDLY':
                desc = '비우호적 - 경계 대상'
            elif status == 'NEUTRAL':
                desc = '중립 - 무관심'
            elif status == 'FRIENDLY':
                desc = '우호적 - 협력 가능'
            elif status == 'ALLIED':
                desc = '동맹 - 강력한 협력'
            else:
                desc = '-'

            faction_rows += f"""                <tr>
                    <td style="padding: 10px; border: 1px solid #444; color: #e0e0e0;">{faction_name}</td>
                    <td style="padding: 10px; border: 1px solid #444; color: {color}; font-weight: bold;">{status}</td>
                    <td style="padding: 10px; border: 1px solid #444; color: #e0e0e0; text-align: center;">{value}</td>
                    <td style="padding: 10px; border: 1px solid #444; color: #888;">{desc}</td>
                </tr>
"""

        # 플레이어 목록 테이블 생성
        player_rows = ""
        for username, x, y, is_admin, created_at, last_login in all_players:
            # 관리자 여부 표시
            admin_badge = "🛡️" if is_admin else "👤"
            # admin_color = "#ffd700" if is_admin else "#90ee90"

            # 현재 위치 표시 (좌표 기반)
            location = f"({x}, {y})"

            # 가입일 포맷팅
            if created_at:
                try:
                    from datetime import datetime
                    if isinstance(created_at, str):
                        join_date = datetime.fromisoformat(created_at.replace('Z', '+00:00')).strftime('%Y-%m-%d')
                    else:
                        join_date = created_at.strftime('%Y-%m-%d')
                except:
                    join_date = str(created_at)
            else:
                join_date = "알 수 없음"

            # 마지막 로그인 포맷팅
            if last_login:
                try:
                    from datetime import datetime
                    if isinstance(last_login, str):
                        last_login_date = datetime.fromisoformat(last_login.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M')
                    else:
                        last_login_date = last_login.strftime('%Y-%m-%d %H:%M')
                except:
                    last_login_date = str(last_login)
            else:
                last_login_date = "없음"

            player_rows += f"""                <tr>
                    <td style="padding: 5px; border: 1px solid #444; color: #e0e0e0; font-weight: bold;">{admin_badge}{username}</td>
                    <td style="padding: 5px; border: 1px solid #444; color: #888;">{location}</td>
                    <td style="padding: 5px; border: 1px solid #444; color: #888; text-align: center;">{join_date}</td>
                    <td style="padding: 5px; border: 1px solid #444; color: #888; text-align: center;">{last_login_date}</td>
                </tr>
"""

        # 템플릿 변수 치환
        html = html.replace('{faction_rows}', faction_rows)
        html = html.replace('{player_rows}', player_rows)

        # 방 상세 정보 JSON 데이터 추가
        room_details_json = json.dumps(room_details, ensure_ascii=False, indent=2)
        html = html.replace('{room_details_json}', room_details_json)

        return html

    def _get_current_time(self) -> str:
        """현재 시간을 문자열로 반환"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def _get_auto_refresh_script(self) -> str:
        """60초 자동 새로고침 JavaScript 코드 반환"""
        return """
        // 60초마다 페이지 자동 새로고침
        let refreshTimer;
        let refreshCountdown = 60;

        function startRefreshTimer() {
            refreshTimer = setInterval(function() {
                refreshCountdown--;
                updateRefreshDisplay();

                if (refreshCountdown <= 0) {
                    location.reload();
                }
            }, 1000);
        }

        function updateRefreshDisplay() {
            const refreshElement = document.getElementById('refreshCountdown');
            if (refreshElement) {
                refreshElement.textContent = refreshCountdown;
            }
        }

        function resetRefreshTimer() {
            clearInterval(refreshTimer);
            refreshCountdown = 60;
            updateRefreshDisplay();
            startRefreshTimer();
        }

        // 페이지 로드 시 타이머 시작
        window.addEventListener('load', function() {
            startRefreshTimer();
            updateRefreshDisplay();
        });

        // 클릭 이벤트에서 타이머 리셋 제거 - 자동 새로고침이 방해받지 않도록 함
        """

    async def export_to_file(self, output_path: str) -> bool:
        """
        통합 맵을 HTML 파일로 내보내기

        Args:
            output_path: 출력 파일 경로

        Returns:
            bool: 성공 여부
        """
        try:
            logger.info("통합 월드 맵 HTML 생성 시작")

            # 모든 방 정보 가져오기
            rooms_data = await self.get_all_rooms()
            logger.debug(f"방 정보 로딩 완료: {len(rooms_data)}개")

            # 엔티티 정보 가져오기 (종족별)
            entities_by_room = await self.get_entities_by_room_and_faction()
            players_by_room = await self.get_players_by_room()

            # 하위 호환성을 위한 기존 형식 데이터 생성
            monsters_by_room = await self.get_monsters_by_room()

            # 통계 계산
            total_entities = sum(sum(counts['monsters'] for counts in room_entities.values())
                               for room_entities in entities_by_room.values())
            total_players = sum(players_by_room.values())
            logger.debug(f"엔티티 정보 로딩 완료: 엔티티 {total_entities}개, 플레이어 {total_players}명")

            # 종족 관계 정보 가져오기
            factions, relations = await self.get_faction_relations()
            logger.debug(f"종족 관계 정보 로딩 완료: 종족 {len(factions)}개, 관계 {len(relations)}개")

            # 플레이어 목록 가져오기
            all_players = await self.get_all_players()
            logger.debug(f"플레이어 목록 로딩 완료: {len(all_players)}명")

            # 방 상세 정보 가져오기
            room_details = await self.get_room_details()
            logger.debug(f"방 상세 정보 로딩 완료: {len(room_details)}개")

            # 방 상세 정보 가져오기
            room_details = await self.get_room_details()
            logger.debug(f"방 상세 정보 로딩 완료: {len(room_details)}개")

            # HTML 생성 (종족별 색상 지원)
            faction_colors = self.get_faction_colors()
            html_content = self.generate_html_with_factions(rooms_data, entities_by_room, players_by_room,
                                                          factions, relations, all_players, room_details, faction_colors)

            # 파일 저장
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)

            logger.debug(f"통합 월드 맵 HTML 생성 완료: {output_path}")
            return True

        except Exception as e:
            logger.error(f"통합 월드 맵 HTML 생성 실패: {e}", exc_info=True)
            return False