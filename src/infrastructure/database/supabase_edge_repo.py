from typing import List, Optional
import logging
from supabase import Client
from src.domain.models import Edge
from src.application.interfaces import EdgeRepository

logger = logging.getLogger(__name__)

class SupabaseEdgeRepository(EdgeRepository):
    def __init__(self, db_client: Client):
        self.db = db_client

    def get_edge_by_id(self, edge_id: str) -> Optional[Edge]:
        try:
            response = self.db.table("map_edges").select("*").eq("id", edge_id).execute()
            if response.data:
                return Edge(**response.data[0])
            return None
        except Exception as e:
            error_msg = str(e).lower()
            if "connection" in error_msg or "timeout" in error_msg or "network" in error_msg:
                logger.error(f"Network/Connection error fetching edge by id: {e}", exc_info=True)
            else:
                logger.error(f"Data/Parsing error fetching edge by id: {e}", exc_info=True)
            return None

    def get_edge_by_nodes(self, from_node_id: str, to_node_id: str) -> Optional[Edge]:
        try:
            response = self.db.table("map_edges").select("*").eq("from_node_id", from_node_id).eq("to_node_id", to_node_id).execute()
            if response.data:
                return Edge(**response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error fetching edge by nodes: {e}", exc_info=True)
            return None

    def get_edges_by_node(self, from_node_id: str) -> List[Edge]:
        try:
            response = self.db.table("map_edges").select("*").eq("from_node_id", from_node_id).execute()
            return [Edge(**item) for item in response.data]
        except Exception as e:
            error_msg = str(e).lower()
            if "connection" in error_msg or "timeout" in error_msg or "network" in error_msg:
                logger.error(f"Network/Connection error fetching edges by node: {e}", exc_info=True)
            else:
                logger.error(f"Data/Parsing error fetching edges by node: {e}", exc_info=True)
            return []

    def get_all_edges(self) -> List[Edge]:
        try:
            all_data = []
            page_size = 1000
            offset = 0
            while True:
                response = self.db.table("map_edges").select("*").range(offset, offset + page_size - 1).execute()
                if not response.data:
                    break
                all_data.extend(response.data)
                if len(response.data) < page_size:
                    break
                offset += page_size
            return [Edge(**item) for item in all_data]
        except Exception as e:
            logger.error(f"Error fetching all edges: {e}", exc_info=True)
            return []

    def update_edge(self, edge: Edge) -> Edge:
        try:
            e_dict = {
                "id": str(edge.id),
                "from_node_id": str(edge.from_node_id),
                "to_node_id": str(edge.to_node_id),
                "distance_m": edge.distance_m,
                "platform_stats": {k: v.model_dump() for k, v in edge.platform_stats.items()},
                "version_added": edge.version_added,
                "updated_at": edge.updated_at.isoformat()
            }
            response = self.db.table("map_edges").update(e_dict).eq("id", str(edge.id)).execute()
            if response.data:
                return Edge(**response.data[0])
            return edge
        except Exception as e:
            logger.error(f"Error updating edge: {e}", exc_info=True)
            return edge

    def upsert_edges(self, edges: List[Edge]) -> bool:
        if not edges:
            return True
        try:
            edge_dicts = []
            for e in edges:
                e_dict = {
                    "id": str(e.id),
                    "from_node_id": str(e.from_node_id),
                    "to_node_id": str(e.to_node_id),
                    "distance_m": e.distance_m,
                    "platform_stats": {k: v.model_dump() for k, v in e.platform_stats.items()},
                    "version_added": e.version_added,
                    "updated_at": e.updated_at.isoformat()
                }
                edge_dicts.append(e_dict)
                
            self.db.table("map_edges").upsert(edge_dicts).execute()
            return True
        except Exception as e:
            logger.error(f"Error in upsert_edges: {e}", exc_info=True)
            return False
