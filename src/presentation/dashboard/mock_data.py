# 로봇 목록 (좌측 사이드바) — robots 테이블 대응
MOCK_ROBOTS = [
    {
        "id": "r1", "name": "Wheeled-01", "platform": "wheeled",
        "status": "Delivery", "battery_pct": 72.0, "current_speed_mps": 0.5,
        "current_mission_id": "m2",
    },
    {
        "id": "r2", "name": "Wheeled-02", "platform": "wheeled",
        "status": "Idle", "battery_pct": 100.0, "current_speed_mps": 0.0,
        "current_mission_id": None,
    },
    {
        "id": "r3", "name": "Legged-01", "platform": "legged",
        "status": "Exploring", "battery_pct": 45.0, "current_speed_mps": 0.3,
        "current_mission_id": "m4",
    },
    {
        "id": "r4", "name": "Wheeled-03", "platform": "wheeled",
        "status": "Charging", "battery_pct": 12.0, "current_speed_mps": 0.0,
        "current_mission_id": None,
    },
    {
        "id": "r5", "name": "Wheeled-04", "platform": "wheeled",
        "status": "Delivery", "battery_pct": 88.0, "current_speed_mps": 1.2,
        "current_mission_id": "m5",
    },
    {
        "id": "r6", "name": "Wheeled-05", "platform": "wheeled",
        "status": "Returning", "battery_pct": 30.0, "current_speed_mps": 0.8,
        "current_mission_id": "m6",
    },
    {
        "id": "r7", "name": "Legged-02", "platform": "legged",
        "status": "Exploring", "battery_pct": 65.0, "current_speed_mps": 0.2,
        "current_mission_id": "m7",
    },
    {
        "id": "r8", "name": "Legged-03", "platform": "legged",
        "status": "Charging", "battery_pct": 18.0, "current_speed_mps": 0.0,
        "current_mission_id": None,
    },
    {
        "id": "r9", "name": "Legged-04", "platform": "legged",
        "status": "Idle", "battery_pct": 98.0, "current_speed_mps": 0.0,
        "current_mission_id": None,
    }
]

# 플릿 작업 비중 (우측 사이드바 차트) — robots.status 집계 대응
MOCK_FLEET_BREAKDOWN = {
    "Idle": 2, "Charging": 2, "Delivery": 2, "Exploring": 2, "Returning": 1
}

# 임무 로그 (우측 사이드바 테이블) — missions 테이블 대응
MOCK_MISSIONS = [
    {
        "id": "m1", "robot_name": "Wheeled-01", "mission_type": "Delivery",
        "status": "Completed", "started_at": "2026-06-17T10:30:00Z",
        "completed_at": "2026-06-17T10:45:00Z", "accumulated_cost": 350.0,
    },
    {
        "id": "m2", "robot_name": "Legged-01", "mission_type": "Exploration",
        "status": "Active", "started_at": "2026-06-17T11:00:00Z",
        "completed_at": None, "accumulated_cost": 120.0,
    },
    {
        "id": "m3", "robot_name": "Wheeled-03", "mission_type": "Delivery",
        "status": "Failed", "started_at": "2026-06-17T09:00:00Z",
        "completed_at": "2026-06-17T09:12:00Z", "accumulated_cost": 0.0,
    },
    {
        "id": "m5", "robot_name": "Wheeled-04", "mission_type": "Delivery",
        "status": "Active", "started_at": "2026-06-17T11:10:00Z",
        "completed_at": None, "accumulated_cost": 50.0,
    },
    {
        "id": "m6", "robot_name": "Wheeled-05", "mission_type": "Delivery",
        "status": "Completed", "started_at": "2026-06-17T08:00:00Z",
        "completed_at": "2026-06-17T08:50:00Z", "accumulated_cost": 210.0,
    },
    {
        "id": "m7", "robot_name": "Legged-02", "mission_type": "Exploration",
        "status": "Active", "started_at": "2026-06-17T10:50:00Z",
        "completed_at": None, "accumulated_cost": 310.0,
    },
    {
        "id": "m8", "robot_name": "Wheeled-02", "mission_type": "Delivery",
        "status": "Failed", "started_at": "2026-06-17T07:00:00Z",
        "completed_at": "2026-06-17T07:12:00Z", "accumulated_cost": 0.0,
    }
]

# 시뮬레이터 온라인 상태 (상단 배너) — simulator_status 테이블 대응
MOCK_SIMULATOR_STATUS = {
    "is_online": True, "last_heartbeat": "2026-06-17T12:00:00Z"
}

def get_robots():
    return MOCK_ROBOTS

def get_fleet_breakdown():
    return MOCK_FLEET_BREAKDOWN

def get_missions():
    return MOCK_MISSIONS

def get_simulator_status():
    return MOCK_SIMULATOR_STATUS
