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
