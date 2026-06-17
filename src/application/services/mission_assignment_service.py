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

class MissionAssignmentService:
    def __init__(
        self,
        node_repo: NodeRepository,
        mission_repo: MissionRepository,
        robot_repo: RobotRepository
    ):
        self.node_repo = node_repo
        self.mission_repo = mission_repo
        self.robot_repo = robot_repo

    def assign_next_mission(self, robot_name: str) -> Optional[Mission]:
        """
        로봇에 다음 임무를 할당합니다.
        1. 로봇 존재 및 Idle 상태 확인
        2. 목적지(BaseLocation) 선정
        3. Mission 생성 (status="Active")
        4. 로봇 상태 업데이트 (status="Delivery")
        """
        robot = self.robot_repo.get_robot_by_name(robot_name)
        if not robot:
            logger.error(f"Robot {robot_name} not found.")
            return None

        if robot.status != "Idle":
            logger.info(f"Robot {robot_name} is not Idle (current status: {robot.status}). Skipping assignment.")
            return None

        # 모든 노드 가져오기
        all_nodes = self.node_repo.get_all_nodes()
        base_locations = [n for n in all_nodes if isinstance(n, BaseLocation) and getattr(n, "location_usage", "") == "Destination"]

        if not base_locations:
            logger.warning("No available Destination base locations found.")
            return None

        # 임의의 목적지 선택 (추후 우선순위 로직 추가 가능)
        target = random.choice(base_locations)

        # Mission 생성
        new_mission = Mission(
            robot_id=robot.id,
            mission_type="Delivery",
            status="Active",
            to_node_id=target.id
        )
        
        created_mission = self.mission_repo.create_mission(new_mission)
        
        # 로봇 상태 업데이트
        self.robot_repo.update_robot_status(robot.id, "Delivery")

        logger.info(f"Assigned mission {created_mission.id} to robot {robot_name} (Destination: {target.name})")
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
