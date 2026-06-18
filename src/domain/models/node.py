from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

class Node(BaseModel):
    """
    3차원 공간 상의 기본 노드(경유점)를 정의하는 부모 모델.
    DB 테이블: nodes
    """
    id: UUID = Field(default_factory=uuid4)
    x: float
    y: float
    z: float
    # node_type은 BASE 또는 DISCOVERED만 허용
    node_type: str = Field(..., pattern="^(BASE|DISCOVERED)$")
    terrain_tag: Optional[str] = Field(default=None, max_length=50)
    version_added: str = Field(default="v1.0.0", max_length=20)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    # Spec C — Fog of War: 로봇이 Raycast로 발견했는지 여부
    is_discovered: bool = Field(default=False)
    discovered_at: Optional[datetime] = Field(default=None)
    discovery_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

class BaseLocation(Node):
    """
    인간이 명시적으로 정의한 고신뢰 노드. (예: 충전소, 로비)
    DB 테이블: base_locations
    """
    node_type: str = Field(default="BASE", pattern="^BASE$")
    name: str = Field(..., max_length=100)
    priority: int = Field(default=10)
    location_usage: Optional[str] = Field(default=None, max_length=50)

class DiscoveredNode(Node):
    """
    로봇이 자율적으로 발견한 탐험 노드.
    DB 테이블: discovered_nodes
    """
    node_type: str = Field(default="DISCOVERED", pattern="^DISCOVERED$")
    # 신뢰도는 0.0 ~ 1.0 사이 값만 허용
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    visit_count: int = Field(default=1, ge=0)
    is_verified: bool = Field(default=False)
    pcd_file_url: Optional[str] = Field(default=None)
