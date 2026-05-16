from typing import List, Optional
from supabase import Client
from src.domain.models import Node, BaseLocation, DiscoveredNode
from src.application.interfaces import NodeRepository

class SupabaseNodeRepository(NodeRepository):
    def __init__(self, db_client: Client):
        self.db = db_client

    def _map_to_node_model(self, data: dict) -> Node:
        # DB 테이블에 저장된 데이터를 가져와 알맞은 Node 자식 객체로 변환
        node_type = data.get("node_type")
        if node_type == "BASE":
            # base_locations 테이블과 조인된 결과일 수도 있고, 여기서 단순화 처리
            return BaseLocation(**data)
        elif node_type == "DISCOVERED":
            return DiscoveredNode(**data)
        return Node(**data)

    def get_node_by_id(self, node_id: str) -> Optional[Node]:
        try:
            # 예시 쿼리: nodes 테이블에서 ID로 조회
            response = self.db.table("nodes").select("*").eq("id", node_id).execute()
            if response.data:
                return self._map_to_node_model(response.data[0])
            return None
        except Exception as e:
            print(f"Error fetching node by id: {e}")
            return None

    def get_all_nodes(self) -> List[Node]:
        try:
            response = self.db.table("nodes").select("*").execute()
            return [self._map_to_node_model(item) for item in response.data]
        except Exception as e:
            print(f"Error fetching all nodes: {e}")
            return []
