"""
대시보드 데이터 액세스 계층.

이전에는 MOCK 데이터를 반환했으나, Spec D에서 실제 Supabase 쿼리로 교체했다.
app.py는 이 4개 함수(get_robots/get_fleet_breakdown/get_missions/get_simulator_status)를
그대로 호출하므로, 함수 시그니처와 반환 키 구조는 유지한다.

읽기 전용 조회이므로 get_supabase_client()(publishable 키)를 사용한다.
조회 실패 시 빈 결과/기본값을 반환해 대시보드가 죽지 않게 한다.
"""
import sys
import os
import logging

# 프로젝트 루트를 sys.path에 추가 (Streamlit이 dashboard 디렉터리에서 실행되어도 src 모듈 import 가능하게)
_root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

logger = logging.getLogger(__name__)


def get_robots():
    """
    robots 테이블 전체를 조회한다.
    반환 키: id, name, platform, status, battery_pct, current_speed_mps, current_mission_id
    """
    try:
        from src.infrastructure.database.client import get_supabase_client
        client = get_supabase_client()
        response = client.table("robots").select(
            "id, name, platform, status, battery_pct, current_speed_mps, current_mission_id"
        ).order("name").execute()
        return response.data or []
    except Exception as e:
        logger.error(f"get_robots failed: {e}")
        return []


def get_fleet_breakdown():
    """
    robots.status 분포를 집계한다. PostgREST가 GROUP BY를 직접 지원하지 않으므로
    전체 status를 가져와 Python에서 센다(로봇 9대라 부담 없음).
    반환: {status: count}
    """
    try:
        from src.infrastructure.database.client import get_supabase_client
        client = get_supabase_client()
        response = client.table("robots").select("status").execute()
        counts = {}
        for row in (response.data or []):
            s = row.get("status", "Unknown")
            counts[s] = counts.get(s, 0) + 1
        return counts
    except Exception as e:
        logger.error(f"get_fleet_breakdown failed: {e}")
        return {}


def get_missions():
    """
    missions 테이블을 최근순으로 조회한다. app.py가 m['robot_name']을 참조하므로,
    robots 테이블과 조인해 이름을 가져와 robot_name 키로 재매핑한다.
    반환 키: id, robot_name, mission_type, status, started_at, completed_at, accumulated_cost
    """
    try:
        from src.infrastructure.database.client import get_supabase_client
        client = get_supabase_client()
        # PostgREST foreign table 조회: robots(name) 으로 조인
        response = (
            client.table("missions")
            .select("id, robot_id, mission_type, status, started_at, completed_at, accumulated_cost, robots(name)")
            .order("started_at", desc=True)
            .limit(50)
            .execute()
        )

        result = []
        for row in (response.data or []):
            # robots 서브오브젝트에서 name 추출 (조인 결과)
            robot_info = row.get("robots")
            if isinstance(robot_info, dict):
                robot_name = robot_info.get("name", "Unknown")
            elif isinstance(robot_info, list) and robot_info:
                robot_name = robot_info[0].get("name", "Unknown")
            else:
                robot_name = "Unknown"

            result.append({
                "id": row.get("id"),
                "robot_name": robot_name,
                "mission_type": row.get("mission_type"),
                "status": row.get("status"),
                "started_at": row.get("started_at"),
                "completed_at": row.get("completed_at"),
                "accumulated_cost": row.get("accumulated_cost", 0.0),
            })
        return result
    except Exception as e:
        logger.error(f"get_missions failed: {e}")
        return []


def get_simulator_status():
    """
    simulator_status 테이블에서 가장 최근 행을 조회한다.
    반환 키: is_online, last_heartbeat
    """
    try:
        from src.infrastructure.database.client import get_supabase_client
        client = get_supabase_client()
        response = (
            client.table("simulator_status")
            .select("is_online, last_heartbeat")
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )
        if response.data:
            return response.data[0]
        return {"is_online": False, "last_heartbeat": None}
    except Exception as e:
        logger.error(f"get_simulator_status failed: {e}")
        return {"is_online": False, "last_heartbeat": None}
