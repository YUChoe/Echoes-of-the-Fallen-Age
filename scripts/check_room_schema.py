#!/usr/bin/env python3
"""방 테이블 스키마 확인 스크립트"""

import sqlite3
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.abspath('.'))

def check_room_schema():
    """방 테이블 스키마 확인"""
    try:
        conn = sqlite3.connect('data/mud_engine.db')
        cursor = conn.cursor()

        # 방 테이블 스키마 확인
        print("=== 방 테이블 스키마 ===")
        cursor.execute("PRAGMA table_info(rooms)")
        columns = cursor.fetchall()

        for column in columns:
            print(f"  {column[1]} {column[2]} {'NOT NULL' if column[3] else 'NULL'} {'DEFAULT ' + str(column[4]) if column[4] else ''}")

        # 방 데이터 샘플 확인
        print("\n=== 방 데이터 샘플 (처음 3개) ===")
        cursor.execute("SELECT id, name, x, y FROM rooms LIMIT 3")
        rooms = cursor.fetchall()

        for room in rooms:
            print(f"  ID: {room[0][:12]}... 이름: {room[1]} X: {room[2]} Y: {room[3]}")

        conn.close()

    except Exception as e:
        print(f"오류 발생: {e}")

if __name__ == "__main__":
    check_room_schema()