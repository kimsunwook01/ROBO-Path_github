from typing import Protocol, List, Optional
from uuid import UUID
from src.domain.models.mission import Mission

class MissionRepository(Protocol):
    def create_mission(self, mission: Mission) -> Mission:
        """Create a new mission in the repository."""
        ...

    def update_mission(self, mission: Mission) -> Optional[Mission]:
        """Update an existing mission."""
        ...

    def update_status(self, mission_id: UUID, status: str) -> Optional[Mission]:
        """Update only the status of a mission."""
        ...

    def get_mission(self, mission_id: UUID) -> Optional[Mission]:
        """Retrieve a mission by its ID."""
        ...

    def get_active_mission_by_destination(self, to_node_id: UUID) -> Optional[Mission]:
        """Retrieve an active mission heading to a specific destination node."""
        ...
