from typing import Protocol, List, Optional
from src.domain.models import Edge

class EdgeRepository(Protocol):
    """
    Edge 데이터 조회를 위한 인터페이스 (Protocol)
    """
    def get_edge_by_id(self, edge_id: str) -> Optional[Edge]:
        ...

    def get_edges_by_node(self, from_node_id: str) -> List[Edge]:
        """
        특정 노드에서 출발하는 모든 엣지 조회
        """
        ...

    def get_all_edges(self) -> List[Edge]:
        """
        전체 엣지 목록 조회 (A* 그래프 빌드용)
        """
        ...

    def update_edge(self, edge: Edge) -> Edge:
        """
        변경된 엣지 정보(플랫폼 통계 등)를 저장
        """
        ...
