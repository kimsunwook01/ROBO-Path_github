from typing import List, Optional
import logging
from supabase import Client
from src.domain.models import Node, BaseLocation, DiscoveredNode
from src.application.interfaces import NodeRepository

logger = logging.getLogger(__name__)

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
            error_msg = str(e).lower()
            if "connection" in error_msg or "timeout" in error_msg or "network" in error_msg:
                logger.error(f"Network/Connection error fetching node by id: {e}", exc_info=True)
            else:
                logger.error(f"Data/Parsing error fetching node by id: {e}", exc_info=True)
            return None

    def get_all_nodes(self) -> List[Node]:
        try:
            response = self.db.table("nodes").select("*").execute()
            return [self._map_to_node_model(item) for item in response.data]
        except Exception as e:
            error_msg = str(e).lower()
            if "connection" in error_msg or "timeout" in error_msg or "network" in error_msg:
                logger.error(f"Network/Connection error fetching all nodes: {e}", exc_info=True)
            else:
                logger.error(f"Data/Parsing error fetching all nodes: {e}", exc_info=True)
            return []

    def upsert_nodes(self, nodes: List[Node]) -> bool:
        if not nodes:
            return True
            
        try:
            node_dicts = []
            base_dicts = []
            discovered_dicts = []
            
            for n in nodes:
                # 기본 nodes 테이블용 필드
                n_dict = {
                    "id": str(n.id),
                    "x": n.x,
                    "y": n.y,
                    "z": n.z,
                    "node_type": n.node_type,
                    "version_added": n.version_added,
                    "created_at": n.created_at.isoformat()
                }
                node_dicts.append(n_dict)
                
                # 자식 테이블용 필드 분류
                from src.domain.models import BaseLocation, DiscoveredNode
                if isinstance(n, BaseLocation):
                    base_dicts.append({
                        "node_id": str(n.id),  # 스키마 상 node_id
                        "name": n.name,
                        "priority": n.priority,
                        "location_usage": n.location_usage
                    })
                elif isinstance(n, DiscoveredNode):
                    discovered_dicts.append({
                        "node_id": str(n.id),  # 스키마 상 node_id
                        "confidence_score": n.confidence_score,
                        "visit_count": n.visit_count,
                        "is_verified": n.is_verified,
                        "pcd_file_url": n.pcd_file_url
                    })
                    
            # 1. 부모 테이블(nodes) 먼저 upsert
            if node_dicts:
                self.db.table("nodes").upsert(node_dicts).execute()
                
            # 2. 자식 테이블(base_locations, discovered_nodes) upsert
            if base_dicts:
                self.db.table("base_locations").upsert(base_dicts).execute()
            if discovered_dicts:
                self.db.table("discovered_nodes").upsert(discovered_dicts).execute()
                
            return True
        except Exception as e:
            logger.error(f"Error in upsert_nodes: {e}", exc_info=True)
            return False
