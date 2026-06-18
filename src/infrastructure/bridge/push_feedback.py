import sys
import json
import logging
import os
from datetime import datetime, timezone
from uuid import uuid4

from src.infrastructure.database.client import get_supabase_admin_client
from src.infrastructure.database.supabase_edge_repo import SupabaseEdgeRepository
from src.application.services.feedback_aggregation_service import FeedbackAggregationService
from src.domain.models import MissionLog, Robot

# 로그를 파일에도 기록 (Unity 서브프로세스로 실행될 때 콘솔 출력이 유실되는 경우를 대비)
_log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "logs")
_log_dir = os.path.abspath(_log_dir)
os.makedirs(_log_dir, exist_ok=True)
_log_file = os.path.join(_log_dir, "push_feedback.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(_log_file, mode="a", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def _handle_discovery(disc: dict):
    """
    DISCOVERY 페이로드 처리 (Spec C).
    disc = {"x": float, "y": float, "z": float}
    좌표 근처의 기존 노드를 찾아 is_discovered=True 로 표시한다.
    """
    x = disc.get("x")
    y = disc.get("y")
    z = disc.get("z")

    if x is None or y is None or z is None:
        logger.error(f"DISCOVERY payload missing coordinates: {disc}")
        return

    from src.infrastructure.database.supabase_node_repo import SupabaseNodeRepository
    db_client = get_supabase_admin_client()
    node_repo = SupabaseNodeRepository(db_client)

    node = node_repo.get_node_near(x, y, z, tolerance=1.0)
    if node is None:
        logger.warning(f"DISCOVERY: no node near ({x:.1f}, {y:.1f}, {z:.1f}). Skipping.")
        return

    if node.is_discovered:
        # 이미 발견된 노드는 재갱신 불필요 (중복 서브프로세스 호출 방지는 Unity가 하지만, 이중 안전장치)
        logger.info(f"DISCOVERY: node {str(node.id)[:8]} already discovered. Skipping.")
        return

    ok = node_repo.mark_discovered(str(node.id), confidence=0.6)
    if ok:
        logger.info(f"DISCOVERY: node {str(node.id)[:8]} at ({node.x:.1f},{node.z:.1f}) marked discovered.")
    else:
        logger.error(f"DISCOVERY: failed to mark node {str(node.id)[:8]} discovered.")


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

    payload_type = data.get("type")

    # === DISCOVERY 분기 (Spec C) ===
    # 로봇이 Raycast로 발견한 타일 좌표를 받아, 가장 가까운 기존 노드를
    # '발견됨'으로 표시한다. FEEDBACK과 달리 임무/배터리 로직은 거치지 않는다.
    if payload_type == "DISCOVERY":
        _handle_discovery(data.get("data", {}))
        sys.exit(0)

    if payload_type != "FEEDBACK":
        logger.info(f"Ignored unknown payload type: {payload_type}")
        sys.exit(0)
        
    import uuid
    fb = data.get("data", {})
    from_node_id_raw = fb.get("from_node_id")
    to_node_id_raw = fb.get("to_node_id")
    platform = fb.get("platform")
    load = fb.get("L")
    stability = fb.get("S")
    efficiency = fb.get("E")
    battery_pct = fb.get("battery_pct")  # Unity가 현재 배터리를 실어 보냄 (없으면 None)
    
    if not (from_node_id_raw and to_node_id_raw and platform and load is not None and stability is not None and efficiency is not None):
        logger.error(f"Missing required fields in feedback data: {fb}")
        sys.exit(1)

    try:
        from_node_id = str(uuid.UUID(from_node_id_raw))
    except ValueError:
        from_node_id = str(uuid.uuid5(uuid.NAMESPACE_OID, from_node_id_raw))
        
    try:
        to_node_id = str(uuid.UUID(to_node_id_raw))
    except ValueError:
        to_node_id = str(uuid.uuid5(uuid.NAMESPACE_OID, to_node_id_raw))
        
    # Init Repos (Admin)
    db_client = get_supabase_admin_client()
    edge_repo = SupabaseEdgeRepository(db_client)
    from src.infrastructure.database.supabase_mission_repo import SupabaseMissionRepository
    from src.infrastructure.database.supabase_robot_repo import SupabaseRobotRepository
    from src.infrastructure.database.supabase_node_repo import SupabaseNodeRepository
    from src.application.services.mission_assignment_service import MissionAssignmentService
    from src.application.services.path_planning_service import PathPlanningService
    
    mission_repo = SupabaseMissionRepository(db_client)
    robot_repo = SupabaseRobotRepository(db_client)
    node_repo = SupabaseNodeRepository(db_client)
    path_service = PathPlanningService(node_repo, edge_repo)
    assignment_service = MissionAssignmentService(node_repo, mission_repo, robot_repo, path_service)
    agg_service = FeedbackAggregationService(edge_repo)
    
    # Create MissionLog domain model
    mission_log = MissionLog(
        id=uuid4(),
        robot_id=None, # 나중에 active mission 찾으면 채워질 수 있음
        operating_mode="Task",
        load_factor=load,
        stability_index=stability,
        efficiency_index=efficiency,
        created_at=datetime.utcnow()
    )
    
    # 0. Active 임무 확인 및 완료 처리
    active_mission = mission_repo.get_active_mission_by_destination(to_node_id)
    robot_name_for_next = None
    
    if active_mission:
        mission_repo.update_status(active_mission.id, "Completed")
        
        # update completed_at and accumulated_cost
        active_mission.status = "Completed"
        active_mission.completed_at = datetime.utcnow()
        # 간단히 기존 누적 비용에 이번 로그 비용을 추가 (임의로 효율 지수를 누적비용으로 산정)
        active_mission.accumulated_cost += efficiency
        mission_repo.update_mission(active_mission)
        
        # mission_log 에 로봇 아이디 연결
        mission_log.robot_id = active_mission.robot_id
        
        # 로봇을 Idle 로 변경 + 도착 시점의 배터리 값도 함께 갱신 (Spec B: A안 — 상태 변경 시점에 갱신)
        # 도착했으므로 속도는 0으로 설정
        robot_repo.update_robot_telemetry(
            active_mission.robot_id,
            status="Idle",
            battery_pct=battery_pct,
            current_speed_mps=0.0,
        )
        
        # 어떤 로봇인지 알아내기 위해 다시 조회
        robot_obj = robot_repo.get_robot_by_id(active_mission.robot_id)
        if robot_obj:
            robot_name_for_next = robot_obj.name
            
        logger.info(f"Mission {active_mission.id} completed by {robot_name_for_next}. battery={battery_pct}")
    
    # 1. 엣지 매핑 시도
    edge = edge_repo.get_edge_by_nodes(from_node_id, to_node_id)
    if edge:
        robot = Robot(name=robot_name_for_next or "dummy_robot", platform=platform)
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
            "robot_id": str(mission_log.robot_id) if mission_log.robot_id else None,
            "operating_mode": mission_log.operating_mode,
            "load_factor": mission_log.load_factor,
            "stability_index": mission_log.stability_index,
            "efficiency_index": mission_log.efficiency_index,
            "profile_version": mission_log.profile_version,
            "created_at": mission_log.created_at.isoformat()
        }
        db_client.table("mission_logs").insert(log_dict).execute()
        logger.info(f"Inserted mission_log {mission_log.id} successfully.")
    except Exception as e:
        logger.error(f"Failed to insert mission_log: {e}")

    # 3. 로봇이 연속 주행을 하도록 다음 임무 배정 (연속 주행 루프 완성)
    if robot_name_for_next:
        assignment_service.assign_next_mission(robot_name_for_next)

if __name__ == "__main__":
    main()
