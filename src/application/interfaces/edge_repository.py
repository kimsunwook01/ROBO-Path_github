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
