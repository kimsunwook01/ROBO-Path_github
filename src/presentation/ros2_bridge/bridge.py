import os
import json
import asyncio
import logging
import websockets

logger = logging.getLogger(__name__)

class UnityWebSocketBridge:
    """
    Phase 4 Path 1: Python -> Unity 명령 송신을 위한 WebSocket 클라이언트.
    .env의 SIMULATOR_HOST 및 SIMULATOR_WS_PORT를 사용하여 접속하며,
    장애물 토글(HAZARD_TOGGLE) 등의 제어 명령을 보냅니다.
    """
    def __init__(self):
        self.host = os.getenv("SIMULATOR_HOST", "localhost")
        self.port = os.getenv("SIMULATOR_WS_PORT", "8765")
        self.uri = f"ws://{self.host}:{self.port}/"
        self.websocket = None

    async def connect(self):
        try:
            self.websocket = await websockets.connect(self.uri)
            logger.info(f"Connected to Unity WebSocket server at {self.uri}")
        except Exception as e:
            logger.error(f"Failed to connect to Unity WebSocket server at {self.uri}: {e}")

    async def disconnect(self):
        if self.websocket:
            await self.websocket.close()
            logger.info("Disconnected from Unity WebSocket server.")

    async def send_command(self, command: dict):
        if not self.websocket or self.websocket.closed:
            logger.warning("WebSocket is not connected. Attempting to reconnect...")
            await self.connect()
            
        if self.websocket and not self.websocket.closed:
            try:
                payload = json.dumps(command)
                await self.websocket.send(payload)
                logger.info(f"Sent command to Unity: {payload}")
            except Exception as e:
                logger.error(f"Failed to send command: {e}")
        else:
            logger.error("Could not send command: WebSocket connection unavailable.")

    async def toggle_hazards(self, active: bool):
        """
        Unity 내 모든 Tile_Hazard의 활성화/비활성화 상태를 토글하는 명령 전송
        """
        command = {
            "type": "HAZARD_TOGGLE",
            "active": active
        }
        await self.send_command(command)

# 예제 실행용 (CLI 테스트)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    async def main():
        bridge = UnityWebSocketBridge()
        await bridge.connect()
        await bridge.toggle_hazards(True)
        await asyncio.sleep(2)
        await bridge.toggle_hazards(False)
        await bridge.disconnect()
        
    asyncio.run(main())
