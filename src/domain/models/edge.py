from datetime import datetime
from typing import Dict
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

class PlatformStat(BaseModel):
    """
    기종별 주행 성적 평균 데이터 구조.
    (map_edges 테이블의 platform_stats JSONB 내부 구조 검증용)
    """
    average_load_factor: float = Field(default=0.0, ge=0.0, le=1.0)
    average_stability: float = Field(default=0.0, ge=0.0, le=1.0)
    average_efficiency: float = Field(default=0.0)
    traversal_count: int = Field(default=0, ge=0)

class Edge(BaseModel):
    """
    노드와 노드 사이의 이동 경로(Edge)를 정의하는 모델.
    DB 테이블: map_edges
    """
    id: UUID = Field(default_factory=uuid4)
    from_node_id: UUID
    to_node_id: UUID
    distance_m: float = Field(..., gt=0.0)
    # 플랫폼(예: 'wheeled', 'legged')을 키로 가지고 PlatformStat을 값으로 가지는 딕셔너리
    platform_stats: Dict[str, PlatformStat] = Field(default_factory=dict)
    version_added: str = Field(default="v1.0.0", max_length=20)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
