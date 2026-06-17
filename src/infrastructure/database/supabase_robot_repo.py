import logging
from typing import Optional
from uuid import UUID
from supabase import Client
from src.domain.models.metadata import Robot
from src.application.interfaces.robot_repository import RobotRepository

logger = logging.getLogger(__name__)

class SupabaseRobotRepository(RobotRepository):
    def __init__(self, db_client: Client):
        self.db = db_client

    def _map_to_robot_model(self, data: dict) -> Robot:
        return Robot(**data)

    def get_robot_by_name(self, name: str) -> Optional[Robot]:
        try:
            response = self.db.table("robots").select("*").eq("name", name).execute()
            if response.data:
                return self._map_to_robot_model(response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error fetching robot by name {name}: {e}", exc_info=True)
            return None

    def get_robot_by_id(self, robot_id: UUID) -> Optional[Robot]:
        try:
            response = self.db.table("robots").select("*").eq("id", str(robot_id)).execute()
            if response.data:
                return self._map_to_robot_model(response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error fetching robot by id {robot_id}: {e}", exc_info=True)
            return None

    def update_robot_status(self, robot_id: UUID, status: str) -> bool:
        try:
            response = self.db.table("robots").update({"status": status}).eq("id", str(robot_id)).execute()
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Error updating robot status {robot_id}: {e}", exc_info=True)
            return False

    def update_robot_telemetry(self, robot_id: UUID, status: str = None,
                               battery_pct: float = None,
                               current_speed_mps: float = None) -> bool:
        """
        로봇의 상태/배터리/속도를 한 번에 갱신한다. None인 필드는 제외.
        """
        payload = {}
        if status is not None:
            payload["status"] = status
        if battery_pct is not None:
            # 0~100 범위로 클램프
            payload["battery_pct"] = max(0.0, min(100.0, battery_pct))
        if current_speed_mps is not None:
            payload["current_speed_mps"] = current_speed_mps

        if not payload:
            return True  # 갱신할 게 없으면 성공 처리

        try:
            response = self.db.table("robots").update(payload).eq("id", str(robot_id)).execute()
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Error updating robot telemetry {robot_id}: {e}", exc_info=True)
            return False
