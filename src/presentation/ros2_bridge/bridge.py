import os
import json
import asyncio
import logging
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

class UnityWebSocketBridge:
    """
    Phase 4 Path 1: Python -> Unity 명령 송신 클라이언트.
    HTTP POST 방식으로 Unity HttpListener에 명령을 전달한다.
    """
    def __init__(self):
        self.host = os.getenv("SIMULATOR_HOST", "127.0.0.1")
        # 0.0.0.0 은 서버 바인드(수신) 전용 주소라 '접속' 대상으로는 쓸 수 없다(특히 Windows).
        # Unity 서버는 0.0.0.0 으로 바인드해도, 클라이언트는 루프백으로 접속한다.
        if self.host == "0.0.0.0":
            self.host = "127.0.0.1"
        self.port = os.getenv("SIMULATOR_WS_PORT", "8765")
        self.uri = f"http://{self.host}:{self.port}/"

    async def connect(self):
        logger.info(f"Targeting Unity Server at {self.uri}")

    async def disconnect(self):
        pass

    async def send_command(self, command: dict):
        try:
            payload = json.dumps(command).encode('utf-8')
            req = urllib.request.Request(self.uri, data=payload, method='POST')
            req.add_header('Content-Type', 'application/json')
            req.add_header('Connection', 'close')

            with urllib.request.urlopen(req, timeout=5.0) as response:
                if response.status == 200:
                    logger.info(f"Sent command to Unity (type={command.get('type')})")
                else:
                    logger.error(f"Failed to send command. Status: {response.status}")
        except urllib.error.URLError as e:
            logger.error(f"Could not send command: {e}")
        except Exception as e:
            logger.error(f"Failed to send command: {e}")

    async def toggle_hazards(self, active: bool):
        command = {
            "type": "HAZARD_TOGGLE",
            "active": active
        }
        await self.send_command(command)

    async def assign_mission(self, robot_id: str, dest_node_id: str, waypoints: list):
        """
        로봇에게 웨이포인트 경로를 따라 목적지로 이동하라는 명령 전송.
        waypoints: [{"x": float, "y": float, "z": float}, ...]
        마지막 웨이포인트가 최종 목적지.
        """
        command = {
            "type": "ASSIGN_MISSION",
            "robot_id": robot_id,
            "dest_node_id": dest_node_id,
            "waypoints": waypoints
        }
        await self.send_command(command)
