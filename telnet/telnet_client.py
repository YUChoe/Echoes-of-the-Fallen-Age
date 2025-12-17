#!/usr/bin/env python3
"""
Telnet 클라이언트 스크립트
telnet-mcp 대신 사용할 수 있는 Python 기반 telnet 클라이언트
"""

import telnetlib
import time
import sys
import json
from typing import Optional, Dict, Any

class TelnetClient:
    def __init__(self):
        self.connections: Dict[str, telnetlib.Telnet] = {}
        self.session_counter = 0

    def connect(self, host: str, port: int, timeout: int = 5) -> Dict[str, Any]:
        """Telnet 서버에 연결"""
        try:
            session_id = f"session_{self.session_counter}"
            self.session_counter += 1

            tn = telnetlib.Telnet(host, port, timeout)
            self.connections[session_id] = tn

            return {
                "success": True,
                "sessionId": session_id,
                "message": f"Connected to {host}:{port}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def send(self, session_id: str, command: str) -> Dict[str, Any]:
        """명령어 전송"""
        try:
            if session_id not in self.connections:
                return {"success": False, "error": "Session not found"}

            tn = self.connections[session_id]
            tn.write((command + "\n").encode('utf-8'))

            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def read(self, session_id: str, wait_ms: int = 1000) -> Dict[str, Any]:
        """응답 읽기"""
        try:
            if session_id not in self.connections:
                return {"success": False, "error": "Session not found"}

            tn = self.connections[session_id]

            # 대기 시간을 초 단위로 변환
            timeout = wait_ms / 1000.0

            # 데이터 읽기 (타임아웃 적용)
            data = tn.read_very_eager()
            if not data:
                time.sleep(timeout)
                data = tn.read_very_eager()

            return {
                "success": True,
                "data": data.decode('utf-8', errors='ignore')
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def disconnect(self, session_id: str) -> Dict[str, Any]:
        """연결 종료"""
        try:
            if session_id not in self.connections:
                return {"success": False, "error": "Session not found"}

            tn = self.connections[session_id]
            tn.close()
            del self.connections[session_id]

            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_sessions(self) -> Dict[str, Any]:
        """활성 세션 목록"""
        return {
            "success": True,
            "sessions": list(self.connections.keys())
        }

def main():
    """명령행 인터페이스"""
    if len(sys.argv) < 2:
        print("사용법: python telnet_client.py <command> [args...]")
        print("명령어:")
        print("  connect <host> <port> [timeout]")
        print("  send <session_id> <command>")
        print("  read <session_id> [wait_ms]")
        print("  disconnect <session_id>")
        print("  list")
        return

    client = TelnetClient()
    command = sys.argv[1]

    if command == "connect":
        if len(sys.argv) < 4:
            print("사용법: connect <host> <port> [timeout]")
            return

        host = sys.argv[2]
        port = int(sys.argv[3])
        timeout = int(sys.argv[4]) if len(sys.argv) > 4 else 5

        result = client.connect(host, port, timeout)
        print(json.dumps(result, indent=2))

    elif command == "send":
        if len(sys.argv) < 4:
            print("사용법: send <session_id> <command>")
            return

        session_id = sys.argv[2]
        cmd = " ".join(sys.argv[3:])

        result = client.send(session_id, cmd)
        print(json.dumps(result, indent=2))

    elif command == "read":
        if len(sys.argv) < 3:
            print("사용법: read <session_id> [wait_ms]")
            return

        session_id = sys.argv[2]
        wait_ms = int(sys.argv[3]) if len(sys.argv) > 3 else 1000

        result = client.read(session_id, wait_ms)
        print(json.dumps(result, indent=2))

    elif command == "disconnect":
        if len(sys.argv) < 3:
            print("사용법: disconnect <session_id>")
            return

        session_id = sys.argv[2]
        result = client.disconnect(session_id)
        print(json.dumps(result, indent=2))

    elif command == "list":
        result = client.list_sessions()
        print(json.dumps(result, indent=2))

    else:
        print(f"알 수 없는 명령어: {command}")

if __name__ == "__main__":
    main()