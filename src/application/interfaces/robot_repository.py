from typing import Protocol, List, Optional
from uuid import UUID
from src.domain.models.metadata import Robot

class RobotRepository(Protocol):
    def get_robot_by_name(self, name: str) -> Optional[Robot]:
        """Retrieve a robot by its string name (e.g., 'Wheeled-01')."""
        ...
    
    def get_robot_by_id(self, robot_id: UUID) -> Optional[Robot]:
        """Retrieve a robot by its UUID."""
        ...
        
    def update_robot_status(self, robot_id: UUID, status: str) -> bool:
        """Update the status of a robot."""
        ...

    def update_robot_telemetry(self, robot_id: UUID, status: str = None,
                               battery_pct: float = None,
                               current_speed_mps: float = None) -> bool:
        """
        로봇의 상태/배터리/속도를 한 번에 갱신한다.
        None인 필드는 갱신하지 않는다(부분 업데이트).
        """
        ...
