import logging
import random
from typing import Optional
from uuid import UUID
from src.domain.models.mission import Mission
from src.domain.models.node import BaseLocation
from src.application.interfaces.node_repository import NodeRepository
from src.application.interfaces.mission_repository import MissionRepository
from src.application.interfaces.robot_repository import RobotRepository

logger = logging.getLogger(__name__)

import asyncio
from datetime import datetime
from src.application.services.path_planning_service import PathPlanningService
from src.presentation.ros2_bridge.bridge import UnityWebSocketBridge

class MissionAssignmentService:
    def __init__(
        self,
        node_repo: NodeRepository,
        mission_repo: MissionRepository,
        robot_repo: RobotRepository,
        path_service: PathPlanningService
    ):
        self.node_repo = node_repo
        self.mission_repo = mission_repo
        self.robot_repo = robot_repo
        self.path_service = path_service

    def assign_next_mission(self, robot_name: str) -> Optional[Mission]:
        """
        로봇에 다음 임무를 할당합니다.
        1. 로봇 존재 및 Idle 상태 확인
        2. 목적지(BaseLocation) 선정 및 경로 검증
        3. Mission 생성 (status="Active")
        4. Unity로 명령 전송
        5. 로봇 상태 업데이트 (status="Delivery")
        """
        robot = self.robot_repo.get_robot_by_name(robot_name)
        if not robot:
            logger.error(f"Robot {robot_name} not found.")
            return None

        if robot.status != "Idle":
            logger.info(f"Robot {robot_name} is not Idle (current status: {robot.status}). Skipping assignment.")
            return None

        all_nodes = self.node_repo.get_all_nodes()
        pickups = [n for n in all_nodes if getattr(n, "terrain_tag", "") == "Node_Pickup"]
        destinations = [n for n in all_nodes if getattr(n, "terrain_tag", "") == "Node_Destination"]
        
        logger.info(f"Found {len(pickups)} Pickups and {len(destinations)} Destinations from {len(all_nodes)} total nodes.")

        if not pickups or not destinations:
            logger.warning("No available Pickup or Destination nodes found.")
            return None

        # 무작위 셔플 후 검증
        pickup = random.choice(pickups)
        random.shuffle(destinations)
        
        valid_dest = None
        for dest in destinations:
            path = self.path_service.find_path(pickup.id, dest.id, robot)
            if path:
                valid_dest = dest
                break
                
        if not valid_dest:
            logger.warning(f"No valid path found for robot {robot_name} to any destination.")
            return None

        new_mission = Mission(
            robot_id=robot.id,
            mission_type="Delivery",
            status="Active",
            from_node_id=pickup.id,
            to_node_id=valid_dest.id,
            started_at=datetime.utcnow()
        )
        
        created_mission = self.mission_repo.create_mission(new_mission)
        self.robot_repo.update_robot_status(robot.id, "Delivery")

        # Unity 노드 ID 생성 공식 반영
        gx = round((valid_dest.x - 5) / 10)
        gz = round((valid_dest.z - 5) / 10)
        y = round(valid_dest.y)
        dest_node_id = f"Tile_Destination_x{gx}_z{gz}_y{y}_r0"

        # Unity로 명령 전송
        bridge = UnityWebSocketBridge()
        asyncio.run(bridge.connect())
        asyncio.run(bridge.assign_mission(
            robot_id=robot_name,
            dest_node_id=dest_node_id,
            dest_x=valid_dest.x,
            dest_y=valid_dest.y,
            dest_z=valid_dest.z
        ))
        asyncio.run(bridge.disconnect())

        pickup_name = getattr(pickup, "name", str(pickup.id))
        dest_name = getattr(valid_dest, "name", str(valid_dest.id))
        logger.info(f"Assigned mission {created_mission.id} to robot {robot_name} (From: {pickup_name}, To: {dest_name})")
        return created_mission

    def cancel_mission(self, mission_id: UUID) -> bool:
        """
        임무를 취소(Failed)하고 로봇을 Idle 상태로 되돌립니다.
        """
        mission = self.mission_repo.get_mission(mission_id)
        if not mission:
            logger.error(f"Mission {mission_id} not found.")
            return False

        if mission.status not in ["Pending", "Active"]:
            logger.warning(f"Mission {mission_id} is already {mission.status}.")
            return False

        # 임무 실패 처리
        self.mission_repo.update_status(mission_id, "Failed")
        
        # 로봇 Idle 복귀
        self.robot_repo.update_robot_status(mission.robot_id, "Idle")
        
        logger.info(f"Mission {mission_id} cancelled. Robot {mission.robot_id} returned to Idle.")
        return True
