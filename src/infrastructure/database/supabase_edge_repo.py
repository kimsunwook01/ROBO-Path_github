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
