"""
DB 상태 모니터링 도구 (Spec B 검증용)

robots / missions 테이블의 현재 상태를 logs/db_snapshot.log 에 기록한다.
Claude가 이 파일을 직접 읽어, 배터리/상태/임무가 의도대로 갱신되는지 검증할 수 있다.

사용법:
    # 1회 스냅샷 (현재 상태 한 번 기록)
    python src/scripts/db_monitor.py

    # watch 모드 (N초 간격으로 계속 기록 — 배터리 변화 추적용)
    python src/scripts/db_monitor.py --watch          # 기본 3초 간격, 60초 동안
    python src/scripts/db_monitor.py --watch --interval 2 --duration 120

watch 모드는 테스트 중에 켜두면, 시간에 따라 배터리가 줄어드는 과정이
타임스탬프와 함께 파일에 남는다. 그 파일을 Claude가 읽으면 시계열로 확인 가능.
"""
import os
import sys
import time
import argparse
from datetime import datetime

# 프로젝트 루트를 PYTHONPATH에 추가 (단독 실행 대비)
_root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

from src.infrastructure.database.client import get_supabase_client

# 로그 파일 경로
_log_dir = os.path.join(_root, "logs")
os.makedirs(_log_dir, exist_ok=True)
_log_file = os.path.join(_log_dir, "db_snapshot.log")


def _fmt_robot(r: dict) -> str:
    name = r.get("name", "?")
    status = r.get("status", "?")
    battery = r.get("battery_pct")
    speed = r.get("current_speed_mps")
    mission = r.get("current_mission_id")

    battery_str = f"{battery:5.1f}%" if isinstance(battery, (int, float)) else "  N/A"
    speed_str = f"{speed:4.1f}" if isinstance(speed, (int, float)) else " N/A"
    mission_str = str(mission)[:8] if mission else "-"

    return f"  {name:<12} | {status:<10} | bat {battery_str} | spd {speed_str} | mission {mission_str}"


def _fmt_mission(m: dict) -> str:
    mid = str(m.get("id", "?"))[:8]
    mtype = m.get("mission_type", "?")
    status = m.get("status", "?")
    cost = m.get("accumulated_cost")
    cost_str = f"{cost:.1f}" if isinstance(cost, (int, float)) else "N/A"
    return f"  {mid} | {mtype:<10} | {status:<10} | cost {cost_str}"


def snapshot(client, log_handle):
    """현재 robots/missions 상태를 한 번 기록한다."""
    ts = datetime.now().strftime("%H:%M:%S")

    lines = [f"\n===== SNAPSHOT {ts} ====="]

    # robots
    try:
        robots = client.table("robots").select(
            "name, status, battery_pct, current_speed_mps, current_mission_id"
        ).order("name").execute().data
        lines.append(f"[ROBOTS] {len(robots)}대")
        for r in robots:
            lines.append(_fmt_robot(r))
    except Exception as e:
        lines.append(f"[ROBOTS] 조회 실패: {e}")

    # missions (최근 10개)
    try:
        missions = client.table("missions").select(
            "id, mission_type, status, accumulated_cost, started_at"
        ).order("started_at", desc=True).limit(10).execute().data
        lines.append(f"[MISSIONS] 최근 {len(missions)}개")
        for m in missions:
            lines.append(_fmt_mission(m))

        # 상태별 집계
        from collections import Counter
        all_missions = client.table("missions").select("status").execute().data
        counts = Counter(m["status"] for m in all_missions)
        lines.append(f"[MISSION 상태 집계] {dict(counts)}")
    except Exception as e:
        lines.append(f"[MISSIONS] 조회 실패: {e}")

    text = "\n".join(lines)
    print(text)
    log_handle.write(text + "\n")
    log_handle.flush()


def main():
    parser = argparse.ArgumentParser(description="ROBO-Path DB 상태 모니터")
    parser.add_argument("--watch", action="store_true", help="일정 간격으로 계속 기록")
    parser.add_argument("--interval", type=float, default=3.0, help="watch 간격(초), 기본 3")
    parser.add_argument("--duration", type=float, default=60.0, help="watch 총 시간(초), 기본 60")
    args = parser.parse_args()

    try:
        client = get_supabase_client()
    except Exception as e:
        print(f"Supabase 클라이언트 초기화 실패: {e}")
        sys.exit(1)

    # watch 모드는 매 실행마다 파일을 새로 시작, 1회 모드는 append
    mode = "w" if args.watch else "a"
    with open(_log_file, mode, encoding="utf-8") as log_handle:
        header = f"\n########## DB MONITOR 시작 {datetime.now():%Y-%m-%d %H:%M:%S} " \
                 f"({'watch' if args.watch else 'single'}) ##########"
        print(header)
        log_handle.write(header + "\n")
        log_handle.flush()

        if args.watch:
            end_time = time.time() + args.duration
            count = 0
            while time.time() < end_time:
                snapshot(client, log_handle)
                count += 1
                time.sleep(args.interval)
            footer = f"\n########## DB MONITOR 종료 (스냅샷 {count}회) ##########"
            print(footer)
            log_handle.write(footer + "\n")
            log_handle.flush()
        else:
            snapshot(client, log_handle)


if __name__ == "__main__":
    main()
