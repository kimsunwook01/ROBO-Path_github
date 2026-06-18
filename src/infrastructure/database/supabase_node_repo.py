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
        if node_type == "BASE" and "name" in data and data["name"] is not None:
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
            all_data = []
            page_size = 1000
            offset = 0
            while True:
                response = self.db.table("nodes").select("*").range(offset, offset + page_size - 1).execute()
                if not response.data:
                    break
                all_data.extend(response.data)
                if len(response.data) < page_size:
                    break
                offset += page_size
            return [self._map_to_node_model(item) for item in all_data]
        except Exception as e:
            logger.error(f"Error fetching all nodes: {e}", exc_info=True)
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
                node_dicts.append({
                    "id": str(n.id),
                    "x": n.x,
                    "y": n.y,
                    "z": n.z,
                    "node_type": n.node_type,
                    "terrain_tag": n.terrain_tag,
                    "version_added": n.version_added,
                    "created_at": n.created_at.isoformat(),
                    "is_discovered": n.is_discovered,
                    "discovered_at": n.discovered_at.isoformat() if n.discovered_at else None,
                    "discovery_confidence": n.discovery_confidence,
                })
                
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

    def get_node_near(self, x: float, y: float, z: float, tolerance: float = 1.0) -> Optional[Node]:
        """
        좌표 범위(x±tol, z±tol) 필터로 노드를 조회한다.
        타일은 10m 그리드 고정 위치라 tolerance 1m면 하나만 잡힌다.
        여러 개면 가장 가까운 것을 반환.
        """
        try:
            response = (
                self.db.table("nodes")
                .select("*")
                .gte("x", x - tolerance).lte("x", x + tolerance)
                .gte("z", z - tolerance).lte("z", z + tolerance)
                .execute()
            )
            if not response.data:
                return None

            # 가장 가까운 노드 선택 (수평거리 기준)
            best = None
            best_dist_sq = float("inf")
            for item in response.data:
                dx = item["x"] - x
                dz = item["z"] - z
                d_sq = dx * dx + dz * dz
                if d_sq < best_dist_sq:
                    best_dist_sq = d_sq
                    best = item

            return self._map_to_node_model(best) if best else None
        except Exception as e:
            logger.error(f"Error in get_node_near ({x},{y},{z}): {e}", exc_info=True)
            return None

    def mark_discovered(self, node_id: str, confidence: float = 0.6) -> bool:
        """
        노드를 발견됨으로 표시. is_discovered=True, discovered_at=now(UTC), confidence 갱신.
        """
        from datetime import datetime, timezone
        try:
            payload = {
                "is_discovered": True,
                "discovered_at": datetime.now(timezone.utc).isoformat(),
                "discovery_confidence": max(0.0, min(1.0, confidence)),
            }
            response = self.db.table("nodes").update(payload).eq("id", node_id).execute()
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Error in mark_discovered {node_id}: {e}", exc_info=True)
            return False
