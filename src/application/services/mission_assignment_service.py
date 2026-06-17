import logging
import random
import asyncio
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from src.domain.models.mission import Mission
from src.application.interfaces.node_repository import NodeRepository
from src.application.interfaces.mission_repository import MissionRepository
from src.application.interfaces.robot_repository import RobotRepository
from src.application.services.path_planning_service import PathPlanningService
from src.presentation.ros2_bridge.bridge import UnityWebSocketBridge

logger = logging.getLogger(__name__)


def _generate_scene_dump_id(name_prefix: str, x: float, y: float, z: float) -> str:
    """SceneDumpExporter.cs 의 GenerateId() 공식과 동일한 문자열 ID 생성."""
    gx = round((x - 5) / 10)
    gz = round((z - 5) / 10)
    iy = round(y)
    return f"{name_prefix}_x{gx}_z{gz}_y{iy}_r0"


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
        2. 목적지 선정 및 A* 경로 검증
        3. Mission 생성 (status="Active")
        4. A* 경로를 웨이포인트로 변환해 Unity로 전송
        5. 로봇 상태 업데이트 (status="Delivery")
        """
        robot = self.robot_repo.get_robot_by_name(robot_name)
        if not robot:
            logger.error(f"Robot {robot_name} not found.")
            return None

        if robot.status != "Idle":
            logger.info(f"Robot {robot_name} is not Idle (current: {robot.status}). Skipping.")
            return None

        all_nodes = self.node_repo.get_all_nodes()
        node_map = {n.id: n for n in all_nodes}

        pickups = [n for n in all_nodes if getattr(n, "terrain_tag", "") == "Node_Pickup"]
        destinations = [n for n in all_nodes if getattr(n, "terrain_tag", "") == "Node_Destination"]

        logger.info(f"Found {len(pickups)} Pickups, {len(destinations)} Destinations ({len(all_nodes)} total nodes)")

        if not pickups or not destinations:
            logger.warning("No Pickup or Destination nodes found.")
            return None

        pickup = random.choice(pickups)
        random.shuffle(destinations)

        valid_dest = None
        valid_path: List[UUID] = []

        for dest in destinations:
            path = self.path_service.find_path(pickup.id, dest.id, robot)
            if path:
                valid_dest = dest
                valid_path = path
                break

        if not valid_dest:
            logger.warning(f"No valid path for {robot_name} to any destination.")
            return None

        # A* 경로(UUID 리스트)를 좌표 웨이포인트로 변환
        waypoints = []
        for node_id in valid_path:
            node = node_map.get(node_id)
            if node:
                waypoints.append({"x": node.x, "y": node.y, "z": node.z})

        if not waypoints:
            logger.error("Path found but could not convert to waypoints.")
            return None

        logger.info(f"A* path: {len(valid_path)} nodes -> {len(waypoints)} waypoints")

        # Mission 생성
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

        # 목적지의 scene_dump ID 생성
        dest_node_id = _generate_scene_dump_id("Tile_Destination", valid_dest.x, valid_dest.y, valid_dest.z)

        # Unity로 웨이포인트 경로 전송
        bridge = UnityWebSocketBridge()
        asyncio.run(bridge.assign_mission(
            robot_id=robot_name,
            dest_node_id=dest_node_id,
            waypoints=waypoints
        ))

        logger.info(f"Assigned mission {created_mission.id} to {robot_name} -> {dest_node_id} ({len(waypoints)} waypoints)")
        return created_mission

    def cancel_mission(self, mission_id: UUID) -> bool:
        mission = self.mission_repo.get_mission(mission_id)
        if not mission:
            logger.error(f"Mission {mission_id} not found.")
            return False

        if mission.status not in ["Pending", "Active"]:
            logger.warning(f"Mission {mission_id} is already {mission.status}.")
            return False

        self.mission_repo.update_status(mission_id, "Failed")
        self.robot_repo.update_robot_status(mission.robot_id, "Idle")

        logger.info(f"Mission {mission_id} cancelled.")
        return True
