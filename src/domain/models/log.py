from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

class MissionLog(BaseModel):
    """
    개별 주행 임무 완료 후 도출된 플랫폼별 성적표 모델.
    DB 테이블: mission_logs
    """
    id: UUID = Field(default_factory=uuid4)
    robot_id: Optional[UUID] = None
    # 운영 모드는 정해진 3가지만 허용
    operating_mode: Optional[str] = Field(default=None, pattern="^(Exploration|Task|Hybrid)$")
    # 부하율 및 안정성 지수는 0.0 ~ 1.0 범위 검증
    load_factor: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    stability_index: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    efficiency_index: Optional[float] = None
    log_file_url: Optional[str] = None
    profile_version: str = Field(default="v1.0.0", max_length=20)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Incident(BaseModel):
    """
    사건/사고 및 인간 피드백 지식화 모델. (LLM 분석 결과)
    DB 테이블: incidents
    """
    id: UUID = Field(default_factory=uuid4)
    edge_id: Optional[UUID] = None
    robot_id: Optional[UUID] = None
    raw_feedback: str = Field(..., min_length=1)
    llm_analysis: Dict[str, Any] = Field(default_factory=dict)
    is_applied: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
