import sys
import json
import logging
from datetime import datetime, timezone
from uuid import uuid4

from src.infrastructure.database.client import get_supabase_client
from src.infrastructure.database.supabase_edge_repo import SupabaseEdgeRepository
from src.application.services.feedback_aggregation_service import FeedbackAggregationService
from src.domain.models import MissionLog, Robot

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def main():
    if len(sys.argv) < 2:
        logger.error("No JSON payload provided.")
        sys.exit(1)
        
    payload_str = sys.argv[1]
    try:
        data = json.loads(payload_str)
    except Exception as e:
        logger.error(f"Failed to parse JSON payload: {e}")
        sys.exit(1)
        
    if data.get("type") != "FEEDBACK":
        logger.info(f"Ignored non-feedback payload type: {data.get('type')}")
        sys.exit(0)
        
    fb = data.get("data", {})
    from_node_id = fb.get("from_node_id")
    to_node_id = fb.get("to_node_id")
    platform = fb.get("platform")
    load = fb.get("L")
    stability = fb.get("S")
    efficiency = fb.get("E")
    
    if not (from_node_id and to_node_id and platform and load is not None and stability is not None and efficiency is not None):
        logger.error(f"Missing required fields in feedback data: {fb}")
        sys.exit(1)
        
    # Init Repos
    db_client = get_supabase_client()
    edge_repo = SupabaseEdgeRepository(db_client)
    agg_service = FeedbackAggregationService(edge_repo)
    
    # Create MissionLog domain model
    mission_log = MissionLog(
        id=uuid4(),
        robot_id=platform, # Simplified for now
        start_node_id=from_node_id,
        end_node_id=to_node_id,
        status="completed",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        metrics={"L": load, "S": stability, "E": efficiency}
    )
    
    # 1. 엣지 매핑 시도
    edge = edge_repo.get_edge_by_nodes(from_node_id, to_node_id)
    if edge:
        robot = Robot(id=platform, platform=platform, weight_profile_id="default")
        try:
            agg_service.process_new_log(edge.id, robot, mission_log)
            logger.info(f"Successfully updated platform_stats for edge {edge.id}")
        except Exception as e:
            logger.error(f"Failed to update edge stats: {e}")
    else:
        logger.warning(f"No direct edge found from {from_node_id} to {to_node_id}. Skipping stats update.")
        
    # 2. MissionLogs 테이블에 적재 (Fallback 포함)
    try:
        log_dict = {
            "id": str(mission_log.id),
            "robot_id": mission_log.robot_id,
            "start_node_id": mission_log.start_node_id,
            "end_node_id": mission_log.end_node_id,
            "status": mission_log.status,
            "started_at": mission_log.started_at.isoformat(),
            "completed_at": mission_log.completed_at.isoformat(),
            "metrics": mission_log.metrics
        }
        db_client.table("mission_logs").insert(log_dict).execute()
        logger.info(f"Inserted mission_log {mission_log.id} successfully.")
    except Exception as e:
        logger.error(f"Failed to insert mission_log: {e}")

if __name__ == "__main__":
    main()
