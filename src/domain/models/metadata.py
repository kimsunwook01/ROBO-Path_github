from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

class MapMetadata(BaseModel):
    """
    지도(공간)의 원점 좌표 및 스케일 등 기초 메타데이터를 정의하는 모델.
    DB 테이블: map_metadata
    """
    id: UUID = Field(default_factory=uuid4)
    origin_lat: float
    origin_lon: float
    origin_alt: float = 0.0
    unit_scale: float = 1.0
    complex_name: str = Field(..., max_length=100)
    map_version: str = Field(default="v1.0.0", max_length=20)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Robot(BaseModel):
    """
    로봇 기종 및 특성을 정의하는 모델.
    DB 테이블: robots
    """
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., max_length=100)
    # 플랫폼은 wheeled(바퀴형) 또는 legged(보행형)만 허용
    platform: str = Field(..., pattern="^(wheeled|legged)$")
    status: str = Field(default="Idle")
    battery_pct: float = Field(default=100.0)
    current_speed_mps: float = Field(default=0.0)
    current_mission_id: Optional[UUID] = None
    weight_profile: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
