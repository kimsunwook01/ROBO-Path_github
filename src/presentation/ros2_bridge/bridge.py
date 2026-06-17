import os
import json
import asyncio
import logging
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

class UnityWebSocketBridge:
    """
    Phase 4 Path 1: Python -> Unity 명령 송신을 위한 클라이언트.
    .env의 SIMULATOR_HOST 및 SIMULATOR_WS_PORT를 사용하여 접속하며,
    장애물 토글(HAZARD_TOGGLE) 등의 제어 명령을 보냅니다.
    (Mono의 HttpListener WebSocket 미지원 버그 우회를 위해 HTTP POST 방식으로 변경됨)
    """
    def __init__(self):
        self.host = os.getenv("SIMULATOR_HOST", "127.0.0.1")
        self.port = os.getenv("SIMULATOR_WS_PORT", "8765")
        self.uri = f"http://{self.host}:{self.port}/"

    async def connect(self):
        # HTTP는 연결 유지가 필요 없음
        logger.info(f"Targeting Unity Server at {self.uri}")

    async def disconnect(self):
        pass

    async def send_command(self, command: dict):
        try:
            payload = json.dumps(command).encode('utf-8')
            req = urllib.request.Request(self.uri, data=payload, method='POST')
            req.add_header('Content-Type', 'application/json')
            req.add_header('Connection', 'close')
            
            # TODO: 비동기 환경에서 동기 블로킹 호출(urlopen)은 이벤트 루프를 블로킹할 수 있으므로, 후속 과제로 aiohttp 또는 asyncio.to_thread()를 사용하여 비동기화해야 함.
            with urllib.request.urlopen(req, timeout=2.0) as response:
                if response.status == 200:
                    logger.info(f"Sent command to Unity: {payload.decode('utf-8')}")
                else:
                    logger.error(f"Failed to send command. Status: {response.status}")
        except urllib.error.URLError as e:
            logger.error(f"Could not send command: {e}")
        except Exception as e:
            logger.error(f"Failed to send command: {e}")

    async def toggle_hazards(self, active: bool):
        """
        Unity 내 모든 Tile_Hazard의 활성화/비활성화 상태를 토글하는 명령 전송
        """
        command = {
            "type": "HAZARD_TOGGLE",
            "active": active
        }
        await self.send_command(command)

    async def assign_mission(self, robot_id: str, dest_node_id: str, dest_x: float, dest_y: float, dest_z: float):
        """
        특정 로봇에게 목적지로 이동하라는 명령 전송
        """
        command = {
            "type": "ASSIGN_MISSION",
            "robot_id": robot_id,
            "dest_node_id": dest_node_id,
            "dest_x": dest_x,
            "dest_y": dest_y,
            "dest_z": dest_z
        }
        await self.send_command(command)

# 예제 실행용 (CLI 테스트)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    async def main():
        bridge = UnityWebSocketBridge()
        await bridge.connect()
        
        # Hazard 토글 테스트
        await bridge.toggle_hazards(True)
        await asyncio.sleep(2)
        await bridge.toggle_hazards(False)
        
        # Mission 배정 테스트 (Wheeled-01을 특정한 위치로 이동 명령)
        await asyncio.sleep(1)
        await bridge.assign_mission(
            robot_id="Wheeled-01",
            dest_node_id="Tile_Destination_x0_z-21_y2_r0",
            dest_x=5.0, dest_y=2.25, dest_z=-205.0
        )
        
        await bridge.disconnect()
        
    asyncio.run(main())
        
    asyncio.run(main())
