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
            SELECT id, description_ko, description_en, x, y
            FROM rooms
            WHERE x IS NOT NULL AND y IS NOT NULL
            ORDER BY x, y
        """)
        result = await cursor.fetchall()
        return [tuple(row) for row in result]

    async def get_monsters_by_room(self) -> Dict[str, int]:
        """방별 몬스터 수 가져오기 (모든 살아있는 몬스터)"""
        cursor = await self.db_manager.execute("""
            SELECT r.id, COUNT(*) as count
            FROM rooms r
            INNER JOIN monsters m ON (r.x = m.x AND r.y = m.y)
            WHERE m.is_alive = 1
            AND m.x IS NOT NULL AND m.y IS NOT NULL
            GROUP BY r.id
        """)
        result = await cursor.fetchall()
        return {row[0]: row[1] for row in result}

    async def get_players_by_room(self) -> Dict[str, int]:
        """방별 플레이어 수 가져오기"""
        cursor = await self.db_manager.execute("""
            SELECT last_room_id, COUNT(*) as count
            FROM players
            WHERE last_room_id IS NOT NULL
            GROUP BY last_room_id
        """)
        result = await cursor.fetchall()
        return {row[0]: row[1] for row in result}

    async def get_npcs_by_room(self) -> Dict[str, int]:
        """방별 NPC 수 가져오기 (플레이어와 우호적인 종족)"""
        # 몬스터 테이블에서 우호적인 종족 가져오기 (좌표 기반)
        cursor = await self.db_manager.execute("""
            SELECT r.id, COUNT(*) as count
            FROM rooms r
            INNER JOIN monsters m ON (r.x = m.x AND r.y = m.y)
            LEFT JOIN faction_relations fr ON (
                (fr.faction_a_id = 'ash_knights' AND fr.faction_b_id = m.faction_id)
                OR (fr.faction_b_id = 'ash_knights' AND fr.faction_a_id = m.faction_id)
            )
            WHERE m.is_alive = 1
            AND m.x IS NOT NULL AND m.y IS NOT NULL
            AND (
                m.faction_id = 'ash_knights'
                OR m.faction_id IS NULL
                OR fr.relation_status IN ('FRIENDLY', 'ALLIED', 'NEUTRAL')
            )
            GROUP BY r.id
        """)
        monsters_result = await cursor.fetchall()

        # 결과 반환
        npc_counts = {row[0]: row[1] for row in monsters_result}
        return npc_counts

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
        """모든 플레이어 정보 가져오기 (좌표 및 마지막 로그인 포함)"""
        cursor = await self.db_manager.execute("""
            SELECT p.username, p.last_room_id, r.x, r.y, p.is_admin, p.created_at, p.last_login
            FROM players p
            LEFT JOIN rooms r ON p.last_room_id = r.id
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
                'monsters': [],
                'players': [],
                'items': []
            }

        # 몬스터 정보
        cursor = await self.db_manager.execute("""
            SELECT r.id, m.name_ko, m.name_en,
                   COALESCE(
                       json_extract(m.stats, '$.level'),
                       json_extract(m.properties, '$.level'),
                       1
                   ) as level,
                   COALESCE(
                       json_extract(m.stats, '$.current_hp'),
                       json_extract(m.stats, '$.max_hp'),
                       20
                   ) as current_hp,
                   COALESCE(
                       json_extract(m.stats, '$.max_hp'),
                       20
                   ) as max_hp
            FROM rooms r
            INNER JOIN monsters m ON (r.x = m.x AND r.y = m.y)
            WHERE m.is_alive = 1 AND r.x IS NOT NULL AND r.y IS NOT NULL
            ORDER BY r.id, m.name_ko
        """)
        monsters = await cursor.fetchall()

        for monster in monsters:
            room_id, name_ko, name_en, level, current_hp, max_hp = monster
            if room_id in room_details:
                room_details[room_id]['monsters'].append({
                    'name_ko': name_ko,
                    'name_en': name_en,
                    'level': level,
                    'hp': f"{current_hp}/{max_hp}"
                })

        # 플레이어 정보
        cursor = await self.db_manager.execute("""
            SELECT p.last_room_id, p.username, p.is_admin
            FROM players p
            WHERE p.last_room_id IS NOT NULL
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
            SELECT r.id, go.name_ko, go.name_en, go.object_type
            FROM rooms r
            INNER JOIN game_objects go ON (r.id = go.location_id)
            WHERE go.location_type = 'room'
            AND go.object_type IN ('item', 'weapon', 'armor', 'consumable')
            AND r.x IS NOT NULL AND r.y IS NOT NULL
            ORDER BY r.id, go.name_ko
        """)
        items = await cursor.fetchall()

        for item in items:
            room_id, name_ko, name_en, object_type = item
            if room_id in room_details:
                room_details[room_id]['items'].append({
                    'name_ko': name_ko,
                    'name_en': name_en,
                    'type': object_type
                })

        return room_details

    def calculate_coordinate_based_exits(self, x: int, y: int, all_rooms_coords: Dict[Tuple[int, int], str]) -> Dict[str, str]:
        """좌표 기반으로 출구를 계산합니다."""
        exits = {}

        # 모든 방향에 대해 인접한 방이 있는지 확인
        for direction in Direction:
            try:
                adj_x, adj_y = calculate_new_coordinates(x, y, direction)

                # 해당 좌표에 방이 있는지 확인
                if (adj_x, adj_y) in all_rooms_coords:
                    target_room_id = all_rooms_coords[(adj_x, adj_y)]
                    exits[direction.value] = target_room_id
            except Exception:
                # UP, DOWN 등 좌표 변화가 없는 방향은 무시
                continue

        return exits

    def generate_html(self, rooms_data: List[Tuple[Any, ...]], monsters_by_room: Dict[str, int],
                     players_by_room: Dict[str, int], npcs_by_room: Dict[str, int],
                     factions: List[Tuple[Any, ...]], relations: List[Tuple[Any, ...]],
                     all_players: List[Tuple[Any, ...]], room_details: Dict[str, Dict[str, Any]]) -> str:
        """HTML 생성"""
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

            # x, y 좌표가 있으면 직접 사용
            if x is not None and y is not None:
                coord = (x, y)

                # 좌표 기반 출구 계산
                exits = self.calculate_coordinate_based_exits(coord[0], coord[1], all_rooms_coords)

                # description에서 첫 줄을 이름으로 사용
                name_ko = desc_ko.split('\n')[0] if desc_ko else room_id

                grid[coord] = {
                    'id': room_id,
                    'name_ko': name_ko,
                    'exits': exits
                }

        # 그리드 범위 계산
        if not grid:
            return "<html><body>No rooms found</body></html>"

        min_x = min(c[0] for c in grid.keys())
        max_x = max(c[0] for c in grid.keys())
        min_y = min(c[1] for c in grid.keys())
        max_y = max(c[1] for c in grid.keys())

        # CSS 스타일 정의
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
                display: block;
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
            }
            .indicator {
                width: 4px;
                height: 4px;
                border-radius: 50%;
            }
            .monster-indicator {
                background-color: #ff0000;
            }
            .player-indicator {
                background-color: #00ff00;
            }
            .npc-indicator {
                background-color: #ffff00;
            }
            .tooltip {
                display: none;
                position: absolute;
                top: -5px;
                left: 30px;
                background-color: rgba(0, 0, 0, 0.95);
                color: #fff;
                padding: 6px 10px;
                border-radius: 4px;
                white-space: nowrap;
                font-size: 13px;
                z-index: 1000;
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
    <title>The Karnas Chronicles: Divided Dominion - 통합 월드 맵</title>
    <style>
{css_style}
    </style>
</head>
<body>
    <h1>🗺️ The Karnas Chronicles: Divided Dominion - 통합 월드 맵</h1>

    <div class="stats">
        <span>총 방 개수: <strong>{len(rooms_data)}</strong></span>
        <span>그리드 크기: <strong>{max_x - min_x + 1}x{max_y - min_y + 1}</strong></span>
        <span>생성 시간: <strong>{self._get_current_time()}</strong></span>
    </div>

    <div class="legend">
        <div class="legend-item">
            <div class="legend-box room"></div>
            <span>방 (Room)</span>
        </div>
        <div class="legend-item">
            <div style="width: 10px; height: 10px; background-color: #ff0000; border-radius: 50%;"></div>
            <span>몬스터 (Monster)</span>
        </div>
        <div class="legend-item">
            <div style="width: 10px; height: 10px; background-color: #00ff00; border-radius: 50%;"></div>
            <span>플레이어 (Player)</span>
        </div>
        <div class="legend-item">
            <div style="width: 10px; height: 10px; background-color: #ffff00; border-radius: 50%;"></div>
            <span>NPC</span>
        </div>
    </div>

    <div class="main-content">
        <div class="map-container">
            <table>
"""

        # 테이블 생성
        for y in range(max_y, min_y - 1, -1):  # y 좌표를 역순으로 렌더링
            html += "            <tr>\n"
            for x in range(min_x, max_x + 1):
                if (x, y) in grid:
                    room = grid[(x, y)]
                    room_id = str(room['id'])  # type: ignore
                    exits = room['exits']  # type: ignore

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

                    # 엔티티 정보 수집
                    has_monster = room_id in monsters_by_room
                    has_player = room_id in players_by_room
                    has_npc = room_id in npcs_by_room

                    monster_count = monsters_by_room.get(room_id, 0)
                    player_count = players_by_room.get(room_id, 0)
                    npc_count = npcs_by_room.get(room_id, 0)

                    # 인디케이터 HTML 생성
                    indicators_html = ''
                    if has_monster or has_player or has_npc:
                        indicators_html = '<div class="indicators">'
                        if has_monster:
                            indicators_html += '<div class="indicator monster-indicator"></div>'
                        if has_player:
                            indicators_html += '<div class="indicator player-indicator"></div>'
                        if has_npc:
                            indicators_html += '<div class="indicator npc-indicator"></div>'
                        indicators_html += '</div>'

                    # 툴팁 텍스트 생성
                    entity_info = []
                    if has_monster:
                        entity_info.append(f"🔴몬스터:{monster_count}")
                    if has_player:
                        entity_info.append(f"🟢플레이어:{player_count}")
                    if has_npc:
                        entity_info.append(f"🟡NPC:{npc_count}")

                    entity_text = ' '.join(entity_info) if entity_info else ''
                    tooltip_text = f"{exit_arrows}({x},{y}) {entity_text}"

                    html += f"""                <td class="{css_class}" onclick="showRoomDetails('{room_id}')">
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

    <div style="margin: 40px auto; max-width: 800px; padding: 20px; background-color: #2a2a2a; border-radius: 8px;">
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
        <div style="margin-top: 20px; padding: 15px; background-color: #1a1a1a; border-radius: 4px; color: #888;">
            <p style="margin: 5px 0;"><strong>우호도 범위:</strong></p>
            <p style="margin: 5px 0;">• 50 ~ 100: <span style="color: #00ff00;">ALLIED (동맹)</span></p>
            <p style="margin: 5px 0;">• 1 ~ 49: <span style="color: #90ee90;">FRIENDLY (우호)</span></p>
            <p style="margin: 5px 0;">• 0: <span style="color: #ffff00;">NEUTRAL (중립)</span></p>
            <p style="margin: 5px 0;">• -1 ~ -49: <span style="color: #ffa500;">UNFRIENDLY (비우호)</span></p>
            <p style="margin: 5px 0;">• -50 ~ -100: <span style="color: #ff0000;">HOSTILE (적대)</span></p>
        </div>
    </div>

    <div style="margin: 40px auto; max-width: 800px; padding: 20px; background-color: #2a2a2a; border-radius: 8px;">
        <h2 style="text-align: center; color: #4a9eff; margin-bottom: 20px; font-size: 16px;">👥 플레이어 목록</h2>
        <table style="width: 100%; border-collapse: collapse;">
            <thead>
                <tr style="background-color: #1a1a1a;">
                    <th style="padding: 10px; border: 1px solid #444; color: #4a9eff;">사용자명</th>
                    <th style="padding: 10px; border: 1px solid #444; color: #4a9eff;">현재 위치</th>
                    <th style="padding: 10px; border: 1px solid #444; color: #4a9eff;">권한</th>
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

        function showRoomDetails(roomId) {{
            const details = roomDetailsData[roomId];
            if (!details) return;

            const panel = document.getElementById('roomDetails');
            const title = document.getElementById('roomTitle');
            const description = document.getElementById('roomDescription');
            const monsters = document.getElementById('roomMonsters');
            const players = document.getElementById('roomPlayers');
            const items = document.getElementById('roomItems');

            // 제목 설정
            title.textContent = `방 정보 (${details.x}, ${details.y})`;

            // 설명 설정 (한국어/영어)
            description.innerHTML = `
                <div><strong>한국어:</strong> ${details.description_ko || '설명 없음'}</div>
                <div style="margin-top: 8px;"><strong>English:</strong> ${details.description_en || 'No description'}</div>
            `;

            // 몬스터 목록
            if (details.monsters && details.monsters.length > 0) {{
                monsters.innerHTML = `
                    <div class="section-title">몬스터 (${details.monsters.length})</div>
                    <div class="item-list">
                        ${details.monsters.map(m => `• ${m.name_ko} (${m.name_en}) Lv.${m.level} HP:${m.hp}`).join('<br>')}
                    </div>
                `;
            }} else {{
                monsters.innerHTML = '';
            }}

            // 플레이어 목록
            if (details.players && details.players.length > 0) {{
                players.innerHTML = `
                    <div class="section-title">플레이어 (${details.players.length})</div>
                    <div class="item-list">
                        ${details.players.map(p => `• ${p.username}${p.is_admin ? ' (관리자)' : ''}`).join('<br>')}
                    </div>
                `;
            }} else {{
                players.innerHTML = '';
            }}

            // 아이템 목록
            if (details.items && details.items.length > 0) {{
                items.innerHTML = `
                    <div class="section-title">아이템 (${details.items.length})</div>
                    <div class="item-list">
                        ${details.items.map(i => `• ${i.name_ko} (${i.name_en}) [${i.type}]`).join('<br>')}
                    </div>
                `;
            }} else {{
                items.innerHTML = '';
            }}

            panel.style.display = 'block';
        }}

        function hideRoomDetails() {{
            document.getElementById('roomDetails').style.display = 'none';
        }}
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
        for username, last_room_id, x, y, is_admin, created_at, last_login in all_players:
            # 관리자 여부 표시
            admin_badge = "🛡️ 관리자" if is_admin else "👤 일반"
            admin_color = "#ffd700" if is_admin else "#90ee90"

            # 현재 위치 표시 (좌표 우선, 없으면 방 ID)
            if x is not None and y is not None:
                location = f"({x}, {y})"
            elif last_room_id:
                location = last_room_id
            else:
                location = "알 수 없음"

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
                    <td style="padding: 10px; border: 1px solid #444; color: #e0e0e0; font-weight: bold;">{username}</td>
                    <td style="padding: 10px; border: 1px solid #444; color: #888;">{location}</td>
                    <td style="padding: 10px; border: 1px solid #444; color: {admin_color}; text-align: center;">{admin_badge}</td>
                    <td style="padding: 10px; border: 1px solid #444; color: #888; text-align: center;">{join_date}</td>
                    <td style="padding: 10px; border: 1px solid #444; color: #888; text-align: center;">{last_login_date}</td>
                </tr>
"""

        # 템플릿 변수 치환
        html = html.replace('{faction_rows}', faction_rows)
        html = html.replace('{player_rows}', player_rows)

        # 방 상세 정보 JSON 데이터 추가
        import json
        room_details_json = json.dumps(room_details, ensure_ascii=False, indent=2)
        html = html.replace('{room_details_json}', room_details_json)

        return html

    def _get_current_time(self) -> str:
        """현재 시간을 문자열로 반환"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

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

            # 엔티티 정보 가져오기
            monsters_by_room = await self.get_monsters_by_room()
            players_by_room = await self.get_players_by_room()
            npcs_by_room = await self.get_npcs_by_room()
            logger.debug(f"엔티티 정보 로딩 완료: 몬스터 {sum(monsters_by_room.values())}마리, "
                       f"플레이어 {sum(players_by_room.values())}명, NPC {sum(npcs_by_room.values())}명")

            # 종족 관계 정보 가져오기
            factions, relations = await self.get_faction_relations()
            logger.debug(f"종족 관계 정보 로딩 완료: 종족 {len(factions)}개, 관계 {len(relations)}개")

            # 플레이어 목록 가져오기
            all_players = await self.get_all_players()
            logger.debug(f"플레이어 목록 로딩 완료: {len(all_players)}명")

            # 방 상세 정보 가져오기
            room_details = await self.get_room_details()
            logger.debug(f"방 상세 정보 로딩 완료: {len(room_details)}개")

            # HTML 생성
            html_content = self.generate_html(rooms_data, monsters_by_room, players_by_room,
                                            npcs_by_room, factions, relations, all_players, room_details)

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