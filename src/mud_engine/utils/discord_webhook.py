# -*- coding: utf-8 -*-
"""Discord 웹훅 알림 유틸리티"""

import logging
import os
from datetime import datetime

import aiohttp

logger = logging.getLogger(__name__)

# 기본 웹훅 베이스 URL
DISCORD_WEBHOOK_BASE = "https://discord.com/api/webhooks"


async def send_discord_webhook(
    env_key: str, content: str, embed: dict | None = None
) -> bool:
    """Discord 웹훅으로 메시지를 전송한다.

    Args:
        env_key: 웹훅 경로가 담긴 환경 변수 이름 (예: NOTIFY_NEWUSER)
        content: 메시지 본문
        embed: Discord embed 객체 (선택)

    Returns:
        전송 성공 여부
    """
    webhook_path = os.getenv(env_key, "")
    if not webhook_path:
        logger.debug(f"{env_key} 미설정 - 웹훅 전송 건너뜀")
        return False

    url = f"{DISCORD_WEBHOOK_BASE}/{webhook_path}"

    # 포럼 채널 지원: DISCORD_THREAD_ID가 설정되어 있으면 query parameter로 추가
    thread_id = os.getenv("DISCORD_THREAD_ID", "")
    if thread_id:
        url = f"{url}?thread_id={thread_id}"

    payload: dict = {"content": content}
    if embed:
        payload["embeds"] = [embed]

    try:
        async with aiohttp.ClientSession() as client_session:
            async with client_session.post(url, json=payload) as resp:
                if resp.status in (200, 204):
                    logger.info("Discord 웹훅 전송 성공")
                    return True
                body = await resp.text()
                logger.warning(
                    f"Discord 웹훅 전송 실패: status={resp.status}, body={body}"
                )
                return False
    except Exception as e:
        logger.error(f"Discord 웹훅 전송 오류: {e}")
        return False


async def notify_new_registration(username: str, ip_address: str) -> bool:
    """신규 회원가입을 Discord로 알린다.

    Args:
        username: 가입한 사용자명
        ip_address: 접속 IP

    Returns:
        전송 성공 여부
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    embed = {
        "title": "🆕 New Player Registered",
        "color": 0x57F287,  # 녹색
        "fields": [
            {"name": "Username", "value": username, "inline": True},
            {"name": "IP", "value": ip_address, "inline": True},
            {"name": "Time", "value": now, "inline": False},
        ],
    }
    return await send_discord_webhook("NOTIFY_NEWUSER", "", embed=embed)
