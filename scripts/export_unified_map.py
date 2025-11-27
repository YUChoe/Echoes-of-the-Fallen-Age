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
        SELECT id, name_ko, name_en, description_ko, exits, x, y
        FROM rooms 
        WHERE x IS NOT NULL AND y IS NOT NULL
        ORDER BY x, y
    """)
    return await cursor.fetchall()


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


def generate_html(rooms_data):
    """HTML 생성"""
    # 방 데이터를 그리드에 매핑
    grid = {}
    room_info = {}
    
    for room in rooms_data:
        room_id, name_ko, name_en, desc_ko, exits_str, x, y = room
        
        # x, y 좌표가 있으면 직접 사용
        if x is not None and y is not None:
            coord = (x, y)
        else:
            # 좌표가 없으면 기존 매핑 함수 사용
            coord = map_room_to_grid(room_id)
        
        if coord:
            # exits 파싱
            try:
                exits = json.loads(exits_str) if exits_str else {}
            except:
                exits = {}
            
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
        td {
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
        .forest {
            background-color: #1a4d1a;
            color: #90ee90;
            border: 2px solid #2d6b2d;
        }
        .plains {
            background-color: #4a6b2a;
            color: #f0e68c;
            border: 2px solid #6b8b3d;
        }
        .town {
            background-color: #8b4513;
            color: #ffd700;
            font-weight: bold;
            border: 3px solid #daa520;
        }
        .special {
            background-color: #4a4a8a;
            color: #ffd700;
            font-weight: bold;
            border: 2px solid #6a6aaa;
        }
        .road {
            background-color: #5a5a5a;
            color: #ddd;
            border: 2px solid #7a7a7a;
        }
        .dock {
            background-color: #2a4a6a;
            color: #87ceeb;
            font-weight: bold;
            border: 2px solid #4a6a8a;
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
    <title>Echoes of the Fallen Age - 통합 월드 맵</title>
    <style>
{css_style}
    </style>
</head>
<body>
    <h1>🗺️ Echoes of the Fallen Age - 통합 월드 맵</h1>
    
    <div class="stats">
        <span>총 방 개수: <strong>{{total_rooms}}</strong></span>
        <span>그리드 크기: <strong>{{width}}x{{height}}</strong></span>
    </div>
    
    <div class="legend">
        <div class="legend-item">
            <div class="legend-box plains"></div>
            <span>평원 (Plains)</span>
        </div>
        <div class="legend-item">
            <div class="legend-box town"></div>
            <span>광장 (Town Square)</span>
        </div>
        <div class="legend-item">
            <div class="legend-box forest"></div>
            <span>숲 (Forest)</span>
        </div>
        <div class="legend-item">
            <div class="legend-box special"></div>
            <span>특수 지역</span>
        </div>
        <div class="legend-item">
            <div class="legend-box road"></div>
            <span>도로</span>
        </div>
        <div class="legend-item">
            <div class="legend-box dock"></div>
            <span>선착장</span>
        </div>
    </div>
    
    <div class="map-container">
        <table>
"""
    
    # 테이블 생성
    for y in range(min_y, max_y + 1):
        html += "            <tr>\n"
        for x in range(min_x, max_x + 1):
            if (x, y) in grid:
                room = grid[(x, y)]
                room_id = room['id']
                name = room['name_ko']
                exits = room['exits']
                
                # 방 타입 결정
                css_class = 'empty'
                if room_id.startswith('forest') or 'forest' in room_id.lower():
                    css_class = 'forest'
                elif room_id.startswith('plains') or 'plains' in room_id.lower():
                    css_class = 'plains'
                elif room_id in ['town_square', 'room_001'] or 'town' in room_id.lower():
                    css_class = 'town'
                elif room_id.startswith('road') or 'road' in room_id.lower():
                    css_class = 'road'
                elif room_id == 'dock' or 'dock' in room_id.lower():
                    css_class = 'dock'
                else:
                    css_class = 'special'
                
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
                
                # 툴팁 텍스트 생성
                tooltip_text = f"{exit_arrows}{name} ({x},{y}) {room_id}"
                
                html += f"""                <td class="{css_class}">
                    <div class="tooltip">{tooltip_text}</div>
                </td>\n"""
            else:
                html += '                <td class="empty"></td>\n'
        html += "            </tr>\n"
    
    html += """        </table>
    </div>
    
    <div style="text-align: center; margin-top: 30px; color: #888;">
        <p>방 위에 마우스를 올리면 상세 정보를 볼 수 있습니다</p>
        <p>툴팁 형식: [출구화살표][방이름] (x,y) [방ID]</p>
        <p>화살표: ↑북 ↓남 →동 ←서</p>
    </div>
</body>
</html>
"""
    
    # 통계 정보 삽입
    html = html.replace('{total_rooms}', str(len(rooms_data)))
    html = html.replace('{width}', str(max_x - min_x + 1))
    html = html.replace('{height}', str(max_y - min_y + 1))
    
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
        
        # HTML 생성
        print("\nHTML 생성 중...")
        html_content = generate_html(rooms_data)
        
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
