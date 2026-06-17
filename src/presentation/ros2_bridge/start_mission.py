import logging
import sys
from src.infrastructure.database.client import get_supabase_admin_client
from src.infrastructure.database.supabase_edge_repo import SupabaseEdgeRepository
from src.infrastructure.database.supabase_mission_repo import SupabaseMissionRepository
from src.infrastructure.database.supabase_robot_repo import SupabaseRobotRepository
from src.infrastructure.database.supabase_node_repo import SupabaseNodeRepository
from src.application.services.mission_assignment_service import MissionAssignmentService
from src.application.services.path_planning_service import PathPlanningService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def main():
    robot_name = sys.argv[1] if len(sys.argv) > 1 else "Wheeled-01"
    
    db_client = get_supabase_admin_client()
    edge_repo = SupabaseEdgeRepository(db_client)
    mission_repo = SupabaseMissionRepository(db_client)
    robot_repo = SupabaseRobotRepository(db_client)
    node_repo = SupabaseNodeRepository(db_client)
    path_service = PathPlanningService(node_repo, edge_repo)
    
    assignment_service = MissionAssignmentService(node_repo, mission_repo, robot_repo, path_service)
    
    logging.info(f"Triggering assignment for {robot_name}...")
    mission = assignment_service.assign_next_mission(robot_name)
    
    if mission:
        logging.info("Mission successfully created and commanded.")
    else:
        logging.warning("Failed to assign mission.")

if __name__ == "__main__":
    main()
