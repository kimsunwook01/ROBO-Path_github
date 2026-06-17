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
