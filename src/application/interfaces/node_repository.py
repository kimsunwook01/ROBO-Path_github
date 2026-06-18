from typing import Protocol, List, Optional
from src.domain.models import Node

class NodeRepository(Protocol):
    """
    Node 데이터 조회를 위한 인터페이스 (Protocol)
    """
    def get_node_by_id(self, node_id: str) -> Optional[Node]:
        ...

    def get_all_nodes(self) -> List[Node]:
        ...

    def upsert_nodes(self, nodes: List[Node]) -> bool:
        """
        다수의 Node(및 자식 객체)를 DB에 일괄 삽입/갱신(Upsert)
        """
        ...

    def get_node_near(self, x: float, y: float, z: float, tolerance: float = 1.0) -> Optional[Node]:
        """
        주어진 좌표 근처(tolerance 이내)의 노드를 찾는다. 없으면 None.
        명세 C 3단계: Discovery 좌표를 기존 타일과 매칭하는 데 사용.
        """
        ...

    def mark_discovered(self, node_id: str, confidence: float = 0.6) -> bool:
        """
        노드를 '발견됨'으로 표시한다 (is_discovered=True, discovered_at=now, confidence 갱신).
        """
        ...
