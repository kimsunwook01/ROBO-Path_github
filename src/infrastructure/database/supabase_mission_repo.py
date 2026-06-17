import logging
from typing import Optional
from uuid import UUID
from supabase import Client
from src.domain.models import Mission
from src.application.interfaces.mission_repository import MissionRepository

logger = logging.getLogger(__name__)

class SupabaseMissionRepository(MissionRepository):
    def __init__(self, db_client: Client):
        self.db = db_client

    def _map_to_mission_model(self, data: dict) -> Mission:
        # Supabase 반환 데이터를 Mission 모델로 변환 (datetime 문자열 처리 등 Pydantic이 자동 수행)
        return Mission(**data)

    def create_mission(self, mission: Mission) -> Mission:
        try:
            mission_dict = mission.model_dump(exclude_none=True)
            if "id" in mission_dict and mission_dict["id"] is None:
                del mission_dict["id"]
                
            # UUID 직렬화를 위해 문자열 변환
            for k, v in mission_dict.items():
                if isinstance(v, UUID):
                    mission_dict[k] = str(v)
            if "started_at" in mission_dict and mission_dict["started_at"]:
                mission_dict["started_at"] = mission_dict["started_at"].isoformat()
            if "completed_at" in mission_dict and mission_dict["completed_at"]:
                mission_dict["completed_at"] = mission_dict["completed_at"].isoformat()

            response = self.db.table("missions").insert(mission_dict).execute()
            if response.data:
                return self._map_to_mission_model(response.data[0])
            raise Exception("No data returned from insert")
        except Exception as e:
            logger.error(f"Error creating mission: {e}", exc_info=True)
            raise

    def update_mission(self, mission: Mission) -> Optional[Mission]:
        if not mission.id:
            logger.error("Cannot update mission without an ID")
            return None
            
        try:
            mission_dict = mission.model_dump(exclude_none=True)
            for k, v in mission_dict.items():
                if isinstance(v, UUID):
                    mission_dict[k] = str(v)
            if "started_at" in mission_dict and mission_dict["started_at"]:
                mission_dict["started_at"] = mission_dict["started_at"].isoformat()
            if "completed_at" in mission_dict and mission_dict["completed_at"]:
                mission_dict["completed_at"] = mission_dict["completed_at"].isoformat()

            response = self.db.table("missions").update(mission_dict).eq("id", str(mission.id)).execute()
            if response.data:
                return self._map_to_mission_model(response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error updating mission {mission.id}: {e}", exc_info=True)
            return None

    def update_status(self, mission_id: UUID, status: str) -> Optional[Mission]:
        try:
            response = self.db.table("missions").update({"status": status}).eq("id", str(mission_id)).execute()
            if response.data:
                return self._map_to_mission_model(response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error updating status for mission {mission_id}: {e}", exc_info=True)
            return None

    def get_mission(self, mission_id: UUID) -> Optional[Mission]:
        try:
            response = self.db.table("missions").select("*").eq("id", str(mission_id)).execute()
            if response.data:
                return self._map_to_mission_model(response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error getting mission {mission_id}: {e}", exc_info=True)
            return None

    def get_active_mission_by_destination(self, to_node_id: UUID) -> Optional[Mission]:
        try:
            # Active 상태이고 목적지가 to_node_id인 임무 조회
            response = self.db.table("missions")\
                .select("*")\
                .eq("to_node_id", str(to_node_id))\
                .eq("status", "Active")\
                .execute()
                
            if response.data:
                # 여러 개일 수 있으나 보통 로봇 하나당 하나. 첫 번째 반환
                return self._map_to_mission_model(response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error finding active mission for destination {to_node_id}: {e}", exc_info=True)
            return None
