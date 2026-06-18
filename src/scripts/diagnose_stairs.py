"""
계단 문제 진단 스크립트 (일회성).

두 가지를 확인한다:
1. nodes 테이블의 terrain_tag 분포 — Path_Stair 가 실제로 저장돼 있는가?
   (없으면 A* 가 계단을 식별할 수 없어 차단도 못 한다)
2. 가장 최근 Active/Completed 임무의 경로를 A* 로 다시 계산해, 그 경로에
   Path_Stair 노드가 포함되는지 확인한다.
   - 경로에 계단이 없는데 로봇이 계단을 올랐다면 → Unity NavMesh 물리 문제
   - 경로에 계단이 있다면 → A* 차단이 여전히 무력화된 것

실행: python src/scripts/diagnose_stairs.py
결과는 logs/diagnose_stairs.log 에 기록된다.
"""
import os
import sys
from collections import Counter
from datetime import datetime

_root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

from src.infrastructure.database.client import get_supabase_admin_client
from src.infrastructure.database.supabase_node_repo import SupabaseNodeRepository
from src.infrastructure.database.supabase_edge_repo import SupabaseEdgeRepository
from src.infrastructure.database.supabase_robot_repo import SupabaseRobotRepository
from src.infrastructure.database.supabase_mission_repo import SupabaseMissionRepository
from src.application.services.path_planning_service import PathPlanningService
from src.application.services.cost_profile_loader import inject_cost_profiles

_log_dir = os.path.join(_root, "logs")
os.makedirs(_log_dir, exist_ok=True)
_log_file = os.path.join(_log_dir, "diagnose_stairs.log")


def log(msg, fh):
    print(msg)
    fh.write(msg + "\n")
    fh.flush()


def main():
    db = get_supabase_admin_client()
    node_repo = SupabaseNodeRepository(db)
    edge_repo = SupabaseEdgeRepository(db)
    robot_repo = SupabaseRobotRepository(db)
    mission_repo = SupabaseMissionRepository(db)

    with open(_log_file, "w", encoding="utf-8") as fh:
        log(f"===== 계단 진단 {datetime.now():%Y-%m-%d %H:%M:%S} =====", fh)

        # === 1. terrain_tag 분포 ===
        log("\n[1] nodes 테이블의 terrain_tag 분포", fh)
        all_nodes = node_repo.get_all_nodes()
        tag_counts = Counter(getattr(n, "terrain_tag", None) for n in all_nodes)
        for tag, cnt in sorted(tag_counts.items(), key=lambda x: -x[1]):
            log(f"  {str(tag):20} : {cnt}", fh)

        stair_count = tag_counts.get("Path_Stair", 0)
        log(f"\n  => Path_Stair 노드: {stair_count}개", fh)
        if stair_count == 0:
            log("  *** 경고: Path_Stair 노드가 0개! terrain_tag 가 제대로 저장 안 됨.", fh)
            log("  *** 이게 원인이면 A* 가 계단을 식별조차 못 한다.", fh)

        # === 2. 최근 임무 경로에 계단이 포함되는지 ===
        log("\n[2] 최근 임무의 A* 경로에 Path_Stair 가 포함되는가?", fh)

        # 가장 최근 임무 조회
        missions = db.table("missions").select(
            "id, robot_id, from_node_id, to_node_id, status, started_at"
        ).order("started_at", desc=True).limit(1).execute().data

        if not missions:
            log("  최근 임무가 없음. start_mission.py 를 한 번 실행한 뒤 다시 진단하세요.", fh)
            return

        m = missions[0]
        log(f"  대상 임무: {m['id'][:8]} (status={m['status']})", fh)

        # 로봇 조회 + cost_profiles 주입 (실제 배정과 동일 조건)
        robot = robot_repo.get_robot_by_id(m["robot_id"])
        if not robot:
            log("  로봇 조회 실패", fh)
            return
        inject_cost_profiles(robot)
        log(f"  로봇: {robot.name} (platform={robot.platform})", fh)

        # 경로 재계산
        path_service = PathPlanningService(node_repo, edge_repo)
        try:
            path = path_service.find_path(m["from_node_id"], m["to_node_id"], robot)
        except Exception as e:
            log(f"  경로 계산 실패: {e}", fh)
            return

        if not path:
            log("  A* 가 빈 경로를 반환함 (목적지 도달 불가).", fh)
            return

        # 경로의 각 노드 terrain_tag 확인
        node_by_id = {n.id: n for n in all_nodes}
        path_tags = []
        stair_in_path = 0
        for nid in path:
            node = node_by_id.get(nid)
            tag = getattr(node, "terrain_tag", "?") if node else "?"
            path_tags.append(tag)
            if tag == "Path_Stair":
                stair_in_path += 1

        log(f"  경로 길이: {len(path)} 노드", fh)
        log(f"  경로 지형 구성: {dict(Counter(path_tags))}", fh)
        log(f"\n  => 경로 내 Path_Stair 노드: {stair_in_path}개", fh)

        # === 결론 ===
        log("\n[결론]", fh)
        if stair_count == 0:
            log("  terrain_tag 자체가 비어 있어 A* 가 계단을 식별 못 함.", fh)
            log("  → 원인: 노드 임포트 시 terrain_tag 누락. 재임포트 또는 임포트 로직 점검 필요.", fh)
        elif stair_in_path > 0:
            log("  A* 경로에 계단이 여전히 포함됨. cost_profiles 차단이 무력화된 상태.", fh)
            log("  → build_graph 의 is_traversable 호출/terrain_tag 매칭을 점검해야 함.", fh)
        else:
            log("  A* 경로에는 계단이 없음(정상 차단됨).", fh)
            log("  → 그런데도 로봇이 계단을 올랐다면, 이는 Unity NavMesh 물리 문제다.", fh)
            log("  → A* 가 준 웨이포인트 사이를 NavMesh 가 직선으로 계단을 가로지른 것.", fh)
            log("  → cost_profiles 로는 해결 불가. NavMesh Area 분리가 필요(별도 작업).", fh)


if __name__ == "__main__":
    main()
