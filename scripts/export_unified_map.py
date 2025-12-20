#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""통합 월드 맵을 HTML로 추출하는 스크립트"""

import asyncio
import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.mud_engine.database.connection import DatabaseManager


async def get_all_rooms(db_manager: DatabaseManager):
    """모든 방 정보 가져오기"""
    cursor = await db_manager.execute("""
        SELECT id, description_ko, description_en, x, y
        FROM rooms
        WHERE x IS NOT NULL AND y IS NOT NULL
        ORDER BY x, y
    """)
    return await cursor.fetchall()



async def get_players_by_room(db_manager: DatabaseManager):
    """방별 플레이어 수 가져오기"""
    cursor = await db_manager.execute("""
        SELECT last_room_id, COUNT(*) as count
        FROM players
        WHERE last_room_id IS NOT NULL
        GROUP BY last_room_id
    """)
    result = await cursor.fetchall()
    return {row[0]: row[1] for row in result}


async def get_faction_info(db_manager: DatabaseManager):
    """종족 정보와 색상 매핑 가져오기"""
    # 종족 정보
    cursor = await db_manager.execute("""
        SELECT id, name_ko, name_en
        FROM factions
        ORDER BY id
    """)
    factions = await cursor.fetchall()

    # 종족별 색상 매핑 (CSS 색상)
    faction_colors = {
        'ash_knights': '#4a9eff',      # 파란색 (플레이어 종족)
        'goblins': '#ff4444',          # 빨간색 (적대적)
        'animals': '#ffa500',          # 주황색 (중립/동물)
        'bandits': '#8b0000',          # 진한 빨간색 (적대적)
        'merchants': '#32cd32',        # 라임그린 (우호적)
        'guards': '#4169e1',           # 로얄블루 (우호적)
        None: '#888888'                # 회색 (종족 없음)
    }

    # 종족 관계
    cursor = await db_manager.execute("""
        SELECT faction_a_id, faction_b_id, relation_value, relation_status
        FROM faction_relations
        WHERE faction_a_id = 'ash_knights'
        ORDER BY faction_b_id
    """)
    relations = await cursor.fetchall()

    return factions, relations, faction_colors


async def get_entities_by_room_and_faction(db_manager: DatabaseManager):
    """방별 엔티티를 종족별로 분류해서 가져오기"""
    entities_by_room = {}

    # 1. npcs 테이블에서 가져오기 (x, y 좌표 사용)
    cursor = await db_manager.execute("""
        SELECT r.id, n.faction_id, COUNT(*) as count
        FROM rooms r
        INNER JOIN npcs n ON (r.x = n.x AND r.y = n.y)
        WHERE n.is_active = 1
        AND n.x IS NOT NULL AND n.y IS NOT NULL
        GROUP BY r.id, n.faction_id
    """)
    npcs_result = await cursor.fetchall()

    for room_id, faction_id, count in npcs_result:
        if room_id not in entities_by_room:
            entities_by_room[room_id] = {}
        if faction_id not in entities_by_room[room_id]:
            entities_by_room[room_id][faction_id] = {'npcs': 0, 'monsters': 0}
        entities_by_room[room_id][faction_id]['npcs'] += count

    # 2. monsters 테이블에서 가져오기
    cursor = await db_manager.execute("""
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
            entities_by_room[room_id][faction_id] = {'npcs': 0, 'monsters': 0}
        entities_by_room[room_id][faction_id]['monsters'] += count

    return entities_by_room


def create_unified_grid():
    """통합 그리드 생성

    레이아웃:
    - 평원 (9x9): 상단
    - 광장: 중앙
    - 숲 (9x9): 좌측
    - 동쪽 경로: 우측 (시장→교회→성)
    - 남쪽 도로: 하단
    """
    # 그리드 크기 계산
    # 가로: 숲(9) + 광장(1) + 동쪽경로(5) = 15
    # 세로: 평원(9) + 광장(1) + 남쪽도로(8) + 선착장(1) = 19
    width = 20
    height = 25

    grid = {}

    # 좌표 매핑
    # 평원: (5, 0) ~ (13, 8)
    # 광장: (9, 9)
    # 숲: (0, 10) ~ (8, 18)
    # 동쪽 경로: (10, 9) ~ (14, 9)
    # 남쪽 도로: (9, 10) ~ (9, 18)

    return grid, width, height


def map_room_to_grid(room_id):
    """방 ID를 그리드 좌표로 매핑"""
    # 평원: plains_x_y -> (5+x, y)
    if room_id.startswith('plains_'):
        parts = room_id.split('_')
        if len(parts) == 3:
            x, y = int(parts[1]), int(parts[2])
            return (5 + x, y)

    # 숲: forest_x_y -> (x, 10+y)
    if room_id.startswith('forest_'):
        parts = room_id.split('_')
        if len(parts) == 3:
            x, y = int(parts[1]), int(parts[2])
            return (x, 10 + y)

    # 광장
    if room_id == 'town_square' or room_id == 'room_001':
        return (9, 9)

    # 동쪽 경로
    east_rooms = {
        'market': (10, 9),
        'room_003': (10, 9),  # 동쪽 시장
        'path_to_church': (11, 9),
        'church': (12, 9),
        'path_to_castle': (13, 9),
        'castle': (14, 9)
    }
    if room_id in east_rooms:
        return east_rooms[room_id]

    # 북쪽 거리
    if room_id == 'room_002':
        return (9, 8)

    # 서쪽 성문
    if room_id == 'room_gate_west':
        return (8, 9)

    # 고블린 지역
    if room_id == 'test_combat_area':
        return (7, 9)

    # 남쪽 도로
    if room_id.startswith('road_south_'):
        parts = room_id.split('_')
        if len(parts) == 3:
            num = int(parts[2])
            return (9, 9 + num)

    # 선착장
    if room_id == 'dock':
        return (9, 18)

    return None


def calculate_coordinate_based_exits(x, y, all_rooms_coords):
    """좌표 기반으로 출구를 계산합니다."""
    from src.mud_engine.utils.coordinate_utils import Direction, calculate_new_coordinates

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


def generate_html(rooms_data, entities_by_room, players_by_room, factions, relations, faction_colors):
    """HTML 생성 (종족별 색상 적용)"""
    # 방 데이터를 그리드에 매핑
    grid = {}
    room_info = {}
    all_rooms_coords = {}  # 좌표 -> 방 ID 매핑

    # 1단계: 모든 방의 좌표 정보 수집
    for room in rooms_data:
        room_id, desc_ko, desc_en, x, y = room

        # x, y 좌표가 있으면 직접 사용
        if x is not None and y is not None:
            coord = (x, y)
            all_rooms_coords[coord] = room_id
        else:
            # 좌표가 없으면 기존 매핑 함수 사용
            coord = map_room_to_grid(room_id)
            if coord:
                all_rooms_coords[coord] = room_id

    # 2단계: 각 방의 좌표 기반 출구 계산
    for room in rooms_data:
        room_id, desc_ko, desc_en, x, y = room

        # x, y 좌표가 있으면 직접 사용
        if x is not None and y is not None:
            coord = (x, y)
        else:
            # 좌표가 없으면 기존 매핑 함수 사용
            coord = map_room_to_grid(room_id)

        if coord:
            # 좌표 기반 출구 계산
            exits = calculate_coordinate_based_exits(coord[0], coord[1], all_rooms_coords)

            # description에서 첫 줄을 이름으로 사용
            name_ko = desc_ko.split('\n')[0] if desc_ko else room_id

            grid[coord] = {
                'id': room_id,
                'name_ko': name_ko,
                'exits': exits
            }
            room_info[room_id] = coord

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
        <span>총 방 개수: <strong>{{total_rooms}}</strong></span>
        <span>그리드 크기: <strong>{{width}}x{{height}}</strong></span>
    </div>

    <div class="legend">
        <div class="legend-item">
            <div class="legend-box room"></div>
            <span>방 (Room)</span>
        </div>
        <div class="legend-item">
            <div style="width: 10px; height: 10px; background-color: #00ff00; border-radius: 50%;"></div>
            <span>플레이어 (Player)</span>
        </div>
        <div class="legend-item">
            <div style="width: 10px; height: 10px; background-color: #4a9eff; border-radius: 50%;"></div>
            <span>잿빛 기사단 (Ash Knights)</span>
        </div>
        <div class="legend-item">
            <div style="width: 10px; height: 10px; background-color: #ff4444; border-radius: 50%;"></div>
            <span>고블린 (Goblins)</span>
        </div>
        <div class="legend-item">
            <div style="width: 10px; height: 10px; background-color: #ffa500; border-radius: 50%;"></div>
            <span>동물 (Animals)</span>
        </div>
        <div class="legend-item">
            <div style="width: 10px; height: 10px; background-color: #888888; border-radius: 50%;"></div>
            <span>기타 종족</span>
        </div>
    </div>

    <div class="map-container">
        <table>
"""

    # 테이블 생성
    for y in range(max_y, min_y - 1, -1):  # y 좌표를 역순으로 렌더링 (y+1이 북쪽/위쪽이 되도록)
        html += "            <tr>\n"
        for x in range(min_x, max_x + 1):
            if (x, y) in grid:
                room = grid[(x, y)]
                room_id = room['id']
                name = room['name_ko']
                exits = room['exits']

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

                    # 종족별 엔티티 인디케이터
                    for faction_id, counts in room_entities.items():
                        total_count = counts['npcs'] + counts['monsters']
                        if total_count > 0:
                            color = faction_colors.get(faction_id, faction_colors[None])

                            # 각 엔티티마다 인디케이터 생성 (최대 6개까지)
                            for i in range(min(total_count, 6)):
                                indicators_html += f'<div class="indicator" style="background-color: {color};"></div>'

                            # 종족 이름 찾기
                            faction_name = next((f[1] for f in factions if f[0] == faction_id), faction_id or '기타')

                            if counts['npcs'] > 0 and counts['monsters'] > 0:
                                entity_info.append(f"🔵{faction_name}:{counts['npcs']}NPC+{counts['monsters']}몬스터")
                            elif counts['npcs'] > 0:
                                entity_info.append(f"🔵{faction_name}:{counts['npcs']}NPC")
                            elif counts['monsters'] > 0:
                                entity_info.append(f"🔴{faction_name}:{counts['monsters']}몬스터")

                    indicators_html += '</div>'

                # tooltip에는 좌표와 엔티티 정보만 표시 (name 제외)
                entity_text = ' '.join(entity_info) if entity_info else ''
                tooltip_text = f"{exit_arrows}({x},{y}) {entity_text}"

                html += f"""                <td class="{css_class}">
                    {indicators_html}
                    <div class="tooltip">{tooltip_text}</div>
                </td>\n"""
            else:
                html += '                <td class="empty"></td>\n'
        html += "            </tr>\n"

    html += """        </table>
    </div>

    <div style="text-align: center; margin-top: 30px; color: #888;">
        <p>방 위에 마우스를 올리면 상세 정보를 볼 수 있습니다</p>
        <p>툴팁 형식: [출구화살표][방이름] (x,y) [엔티티정보]</p>
        <p>화살표: ↑북 ↓남 →동 ←서</p>
    </div>

    <div style="margin: 40px auto; max-width: 800px; padding: 20px; background-color: #2a2a2a; border-radius: 8px;">
        <h2 style="text-align: center; color: #4a9eff; margin-bottom: 20px;">🤝 종족 관계 (잿빛 기사단 기준)</h2>
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

    # 통계 정보 삽입
    html = html.replace('{total_rooms}', str(len(rooms_data)))
    html = html.replace('{width}', str(max_x - min_x + 1))
    html = html.replace('{height}', str(max_y - min_y + 1))
    html = html.replace('{faction_rows}', faction_rows)

    return html


async def main():
    """메인 실행 함수"""
    print("=== 통합 월드 맵 HTML 추출 시작 ===\n")

    db_manager = DatabaseManager()
    await db_manager.initialize()

    try:
        # 모든 방 정보 가져오기
        print("방 정보 로딩 중...")
        rooms_data = await get_all_rooms(db_manager)
        print(f"✅ {len(rooms_data)}개의 방 로딩 완료")

        # 엔티티 정보 가져오기 (종족별)
        print("엔티티 정보 로딩 중...")
        entities_by_room = await get_entities_by_room_and_faction(db_manager)
        players_by_room = await get_players_by_room(db_manager)

        # 통계 계산
        total_entities = sum(sum(counts['npcs'] + counts['monsters'] for counts in room_entities.values())
                           for room_entities in entities_by_room.values())
        total_players = sum(players_by_room.values())
        print(f"✅ 엔티티: {total_entities}개, 플레이어: {total_players}명")

        # 종족 정보 가져오기
        print("종족 정보 로딩 중...")
        factions, relations, faction_colors = await get_faction_info(db_manager)
        print(f"✅ 종족: {len(factions)}개, 관계: {len(relations)}개")

        # HTML 생성
        print("\nHTML 생성 중...")
        html_content = generate_html(rooms_data, entities_by_room, players_by_room, factions, relations, faction_colors)

        # 파일 저장
        output_file = "world_map_unified.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"✅ HTML 파일 생성 완료: {output_file}")
        print(f"\n브라우저에서 {output_file}을 열어 통합 지도를 확인하세요.")

    finally:
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
