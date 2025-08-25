#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
따라가기 기능 테스트 스크립트
"""

import asyncio
import websockets
import json
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestClient:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.ws = None
        self.authenticated = False

    async def connect(self):
        """서버에 연결"""
        try:
            self.ws = await websockets.connect("ws://localhost:8080/ws")
            logger.info(f"{self.username}: 서버에 연결됨")
            return True
        except Exception as e:
            logger.error(f"{self.username}: 연결 실패 - {e}")
            return False

    async def send_message(self, data):
        """메시지 전송"""
        if self.ws:
            await self.ws.send(json.dumps(data))

    async def receive_message(self):
        """메시지 수신"""
        if self.ws:
            try:
                message = await asyncio.wait_for(self.ws.recv(), timeout=1.0)
                return json.loads(message)
            except asyncio.TimeoutError:
                return None
            except Exception as e:
                logger.error(f"{self.username}: 메시지 수신 오류 - {e}")
                return None
        return None

    async def login(self):
        """로그인"""
        await self.send_message({
            "command": "login",
            "username": self.username,
            "password": self.password
        })

        # 응답 대기
        response = await self.receive_message()
        if response and response.get("status") == "success":
            self.authenticated = True
            logger.info(f"{self.username}: 로그인 성공")
            return True
        else:
            logger.error(f"{self.username}: 로그인 실패 - {response}")
            return False

    async def register(self):
        """회원가입"""
        await self.send_message({
            "command": "register",
            "username": self.username,
            "password": self.password
        })

        # 응답 대기
        response = await self.receive_message()
        if response and response.get("status") == "success":
            self.authenticated = True
            logger.info(f"{self.username}: 회원가입 성공")
            return True
        else:
            logger.error(f"{self.username}: 회원가입 실패 - {response}")
            return False

    async def send_command(self, command):
        """게임 명령어 전송"""
        if self.authenticated:
            await self.send_message({"command": command})
            logger.info(f"{self.username}: 명령어 전송 - {command}")

    async def listen_for_messages(self, duration=5):
        """메시지 수신 대기"""
        end_time = asyncio.get_event_loop().time() + duration
        while asyncio.get_event_loop().time() < end_time:
            message = await self.receive_message()
            if message:
                logger.info(f"{self.username}: 수신 - {message}")

    async def close(self):
        """연결 종료"""
        if self.ws:
            await self.ws.close()

async def test_follow_functionality():
    """따라가기 기능 테스트"""
    logger.info("=== 따라가기 기능 테스트 시작 ===")

    # 두 개의 테스트 클라이언트 생성
    leader = TestClient("leader", "password123")
    follower = TestClient("follower", "password123")

    try:
        # 1. 연결
        if not await leader.connect() or not await follower.connect():
            logger.error("연결 실패")
            return

        # 2. 회원가입 또는 로그인 시도
        logger.info("--- 계정 생성/로그인 ---")
        await leader.register()
        await asyncio.sleep(1)
        await follower.register()
        await asyncio.sleep(1)

        # 3. 초기 위치 확인
        logger.info("--- 초기 위치 확인 ---")
        await leader.send_command("look")
        await follower.send_command("look")
        await asyncio.sleep(2)

        # 4. 같은 방에 있는지 확인
        logger.info("--- 플레이어 목록 확인 ---")
        await leader.send_command("players")
        await asyncio.sleep(1)

        # 5. 따라가기 설정
        logger.info("--- 따라가기 설정 ---")
        await follower.send_command("follow leader")
        await asyncio.sleep(2)

        # 6. 리더 이동
        logger.info("--- 리더 이동 (북쪽) ---")
        await leader.send_command("north")
        await asyncio.sleep(3)

        # 7. 결과 확인
        logger.info("--- 이동 후 위치 확인 ---")
        await leader.send_command("look")
        await follower.send_command("look")
        await asyncio.sleep(2)

        # 8. 플레이어 목록 재확인
        logger.info("--- 이동 후 플레이어 목록 확인 ---")
        await leader.send_command("players")
        await asyncio.sleep(2)

        # 9. 따라가기 중지
        logger.info("--- 따라가기 중지 ---")
        await follower.send_command("follow stop")
        await asyncio.sleep(1)

        # 10. 리더 재이동 (따라가기 없이)
        logger.info("--- 따라가기 중지 후 리더 이동 ---")
        await leader.send_command("south")
        await asyncio.sleep(2)

        # 11. 최종 위치 확인
        logger.info("--- 최종 위치 확인 ---")
        await leader.send_command("look")
        await follower.send_command("look")
        await asyncio.sleep(2)

    except Exception as e:
        logger.error(f"테스트 중 오류: {e}")

    finally:
        # 연결 종료
        await leader.close()
        await follower.close()
        logger.info("=== 테스트 완료 ===")

if __name__ == "__main__":
    asyncio.run(test_follow_functionality())