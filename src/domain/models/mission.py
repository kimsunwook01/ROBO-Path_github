from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

class Mission(BaseModel):
    id: Optional[UUID] = None
    robot_id: UUID
    mission_type: str = Field(description="'Delivery' or 'Exploration'")
    status: str = Field(description="'Pending', 'Active', 'Completed', 'Failed'")
    from_node_id: Optional[UUID] = None
    to_node_id: Optional[UUID] = None
    accumulated_cost: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    acknowledged: bool = False
