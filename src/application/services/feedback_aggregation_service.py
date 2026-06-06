from uuid import UUID

from src.domain.models import Edge, Robot, MissionLog
from src.domain.models.edge import PlatformStat
from src.domain.algorithms.statistics import update_platform_stats
from src.application.interfaces.edge_repository import EdgeRepository

class FeedbackAggregationService:
    """
    새로운 주행 로그가 발생했을 때 엣지의 플랫폼(기종별) 통계를 갱신하고 DB에 반영하는 서비스입니다.
    """
    def __init__(self, edge_repo: EdgeRepository):
        self.edge_repo = edge_repo

    def process_new_log(self, edge_id: UUID, robot: Robot, new_log: MissionLog) -> Edge:
        """
        주행 로그를 바탕으로 해당 엣지의 통계를 갱신합니다.
        
        Args:
            edge_id: 주행 로그가 발생한 대상 엣지의 UUID
            robot: 주행을 수행한 로봇 모델
            new_log: 수집된 주행 완료 로그 데이터
            
        Returns:
            Edge: 통계가 갱신되어 저장된 엣지 모델 반환
        """
        # 1. 엣지 데이터 조회
        edge = self.edge_repo.get_edge_by_id(edge_id)
        if not edge:
            raise ValueError(f"Edge not found: {edge_id}")
            
        # 2. 기존 통계 조회 (없으면 빈 PlatformStat 생성)
        platform_name = robot.platform
        current_stats = edge.platform_stats.get(platform_name, PlatformStat())
        
        # 3. 새로운 통계 병합 연산 (O(1) 누적 이동 평균)
        updated_stats = update_platform_stats(current_stats, new_log)
        
        # 4. 엣지에 새로운 통계 할당 및 DB 업데이트
        edge.platform_stats[platform_name] = updated_stats
        updated_edge = self.edge_repo.update_edge(edge)
        
        return updated_edge
