# [Spec A] 임무 시스템 (Pickup → Delivery 워크플로) 구현 명세서

> 작성일: 2026-06-17
> 선행 문서: ROBO-Path_Dashboard_Data_Contract.md (missions 스키마 5.2절 참조)
> 목적: 로봇이 거점에서 대기하다가 Pickup→Destination 임무를 자동으로 부여받아 주행하고, 완료/실패가 기록되는 전체 흐름을 만든다.

---

## 0. 선행 확인 사항 (반드시 먼저 해결해야 하는 기존 결함)

아래 두 가지는 본 명세서의 단계들을 시작하기 *전에* 막힌다. 실제 코드를 직접 확인해 발견한 결함이다.

### 0.1 `location_usage` 필드 매핑 버그

`src/application/services/map_import_service.py` 52~58번 줄:

```python
base_loc = BaseLocation(
    ...
    name=f"Station_{node_id[:8]}",
    location_usage=n.get("location_usage", "Station"),
    terrain_tag=n.get("tag", "Node_Destination")
)
```

`scene_dump.json`의 실제 노드 필드는 `"location_usage"`가 아니라 `"usage"`이다 (예: `{"tag": "Node_Destination", ..., "usage": "destination"}`). 따라서 `n.get("location_usage", "Station")`은 항상 기본값 `"Station"`만 반환하며, **현재 DB의 거점 34개(Station 9 + Pickup 1 + Destination 24) 전부가 `location_usage="Station"`으로 동일하게 저장되어 있다.** 다행히 `terrain_tag`는 `n.get("tag", ...)`로 정확한 키를 읽고 있어 `Node_Station`/`Node_Pickup`/`Node_Destination` 값이 제대로 들어가 있다.

**조치:** Pickup/Destination/Station 구분은 `location_usage`가 아니라 **`terrain_tag`**를 기준으로 한다. 다음 중 하나를 선택해 1-A 단계에서 처리한다.
- (권장) `map_import_service.py`의 `location_usage=n.get("location_usage", "Station")`을 `location_usage=n.get("usage", "station")`으로 고치고, 맵을 재임포트한다.
- 재임포트가 번거로우면, 이후 모든 단계에서 `location_usage` 대신 `terrain_tag`(`Node_Pickup`/`Node_Destination`/`Node_Station`)로 노드 종류를 판별한다.

### 0.2 `SetDestination()` 호출자가 전무함

`Unity/.../Robot/RobotController.cs`의 `public void SetDestination(Vector3 dest, string targetNodeId = "unknown")`은 구현되어 있으나, 저장소 전체에서 이 메서드를 호출하는 코드가 없다(`RobotSpawner.cs`는 스폰만 하고 목적지를 주지 않는다). 본 명세서의 3장이 이 공백을 채운다.

### 0.3 로봇 인스턴스 식별자 부재

`Unity/.../Robot/RobotIdentify.cs`:

```csharp
public class RobotIdentify : MonoBehaviour
{
    public RobotPlatform platform;
}
```

`platform`(wheeled/legged)만 있고, 9대 중 "이 로봇"을 가리킬 고유 식별자가 없다. Python에서 "로봇 X에게 목적지 Y로 가라"는 명령을 보내려면 식별자가 필요하다. 2장에서 추가한다.

---

## 1. 단계 1 — 거점 분류 정정 (위 0.1의 실제 수정)

**대상 파일:** `src/application/services/map_import_service.py`

1. `location_usage=n.get("location_usage", "Station")`를 `location_usage=n.get("usage", "station")`로 수정한다.
2. 수정 후 `python -c`로 `import_from_json`을 다시 실행해 재임포트한다(기존 `upsert_nodes`가 upsert이므로 안전하게 덮어쓴다).
3. **검증:** 재임포트 후 Supabase `base_locations` 테이블에서 `SELECT location_usage, COUNT(*) FROM base_locations GROUP BY location_usage;`를 실행해 `station: 9`, `pickup: 1`, `destination: 24`(혹은 덤프의 실제 `usage` 값 표기에 맞는 분포)가 나오는지 직접 확인하고 결과를 보고한다. 추측하지 말고 실제 쿼리 결과를 캡처한다.

---

## 2. 단계 2 — 로봇 인스턴스 식별자 도입

**대상 파일:** `Unity/.../Robot/RobotIdentify.cs`, `Unity/.../Robot/RobotSpawner.cs`

1. `RobotIdentify`에 `public string robotId;`와 `public string homeStationId;`(스폰된 거점의 node id)를 추가한다.
2. `RobotSpawner.SpawnAt()`에서 로봇을 만들 때 `robotId`를 `$"{platform}-{index:D2}"` 형식(예: `Wheeled-01`, `Legged-01`)으로 부여한다. platform별로 별도 카운터를 둬서 번호가 1부터 시작하게 한다.
3. `homeStationId`에는 스폰에 사용된 `Node_Station` GameObject의 이름 또는 식별 가능한 값을 넣는다(이 값이 0.1에서 DB에 저장된 node id와 매칭되어야 하므로, scene_dump의 node id 형식과 일치하는 값을 사용해야 한다 — GameObject 이름 규칙을 직접 확인하고 매칭 방식을 정한다).
4. **검증:** Unity 에디터에서 플레이 모드로 9대를 스폰시키고, Inspector에서 각 로봇의 `RobotIdentify.robotId`가 `Wheeled-01`~`Wheeled-05`, `Legged-01`~`Legged-04`로 중복 없이 부여되는지 직접 확인한다.

---

## 3. 단계 3 — Python → Unity 목적지 명령 채널

**대상 파일:** `Unity/.../Network/WebSocketServer.cs`, `src/presentation/ros2_bridge/bridge.py`

### 3.1 Unity 측 — 명령 수신 확장

`WebSocketServer.cs`의 `ProcessMessageOnMainThread`는 현재 `cmd.type == "HAZARD_TOGGLE"`만 처리한다(`CommandMessage` 클래스는 `type`, `active` 필드만 가짐). 다음을 추가한다.

1. `CommandMessage` 클래스에 `robot_id`(string), `dest_x`/`dest_y`/`dest_z`(float), `dest_node_id`(string) 필드를 추가한다.
2. `cmd.type == "ASSIGN_MISSION"` 분기를 추가한다. `FindObjectsOfType<RobotIdentify>()`로 전체 로봇을 순회해 `identify.robotId == cmd.robot_id`인 로봇을 찾고, 그 로봇의 `RobotController.SetDestination(new Vector3(cmd.dest_x, cmd.dest_y, cmd.dest_z), cmd.dest_node_id)`를 호출한다.
3. 일치하는 로봇이 없으면 `Debug.LogWarning`으로 남기고 무시한다(예외로 서버를 죽이지 않는다).

### 3.2 Python 측 — 명령 송신 메서드 추가

`bridge.py`의 `UnityWebSocketBridge`에 `toggle_hazards`와 같은 패턴으로 메서드를 추가한다.

```python
async def assign_mission(self, robot_id: str, dest_node_id: str, dest_x: float, dest_y: float, dest_z: float):
    command = {
        "type": "ASSIGN_MISSION",
        "robot_id": robot_id,
        "dest_node_id": dest_node_id,
        "dest_x": dest_x, "dest_y": dest_y, "dest_z": dest_z
    }
    await self.send_command(command)
```

**검증:** `bridge.py`를 CLI로 직접 실행해(`toggle_hazards` 예제처럼 `assign_mission`을 호출하는 임시 테스트 블록 추가) Unity 콘솔에 `ASSIGN_MISSION` 수신 로그가 뜨고, 지정한 로봇이 실제로 그 좌표로 이동을 시작하는지 직접 플레이 모드에서 확인한다.

---

## 4. 단계 4 — 임무 데이터 모델 및 저장소

**대상 파일(신규):** `supabase/migrations/`, `src/domain/models/mission.py`, `src/application/interfaces/mission_repository.py`, `src/infrastructure/database/supabase_mission_repo.py`

1. Data Contract 5.2절 스키마로 마이그레이션 SQL 작성(`missions` 테이블: id, robot_id, mission_type, status, from_node_id, to_node_id, accumulated_cost, started_at, completed_at, acknowledged).
   - `robot_id`는 기존 `robots.id`(UUID) FK로 둘지, 혹은 Unity의 `robotId`(문자열, 예: `Wheeled-01`)를 그대로 저장할지 결정해야 한다. 기존 `robots` 테이블에 실제 row 9개가 등록되어 있지 않으므로(Phase 4에서 `robot_id=None`으로 단순화했던 결정과 연결됨), **Spec B(로봇 상태 스키마)에서 robots 테이블에 9개 row를 등록하는 작업이 선행되어야** `missions.robot_id`가 의미 있는 FK가 된다. 선행 의존성으로 명시한다.
2. `Mission` Pydantic 모델 작성(`src/domain/models/mission.py`), `src/domain/models/__init__.py`에 등록.
3. `MissionRepository` Protocol 인터페이스 작성(`create_mission`, `update_status`, `get_pending_robots_and_targets` 등 — 기존 `EdgeRepository`/`NodeRepository` 패턴을 그대로 따른다).
4. `SupabaseMissionRepository` 구현 작성(기존 `supabase_edge_repo.py`/`supabase_node_repo.py` 패턴을 그대로 따른다).
5. **검증:** 단위 테스트(`tests/test_mission_repository.py`)를 작성해 mock Supabase 클라이언트로 create/update 호출이 올바른 페이로드를 만드는지 확인한다(Phase 4에서 검증했던 것과 동일한 방식 — 실제 실행 결과를 보고).

---

## 5. 단계 5 — 임무 배정 로직

**대상 파일(신규):** `src/application/services/mission_assignment_service.py`

1. `MissionAssignmentService(node_repo, mission_repo, robot_repo)`를 만든다.
2. `assign_next_mission(robot_id: str) -> Optional[Mission]`: 해당 로봇이 Idle 상태인지 확인 후(B에서 추가되는 `robots.status` 참조), `node_repo`에서 `terrain_tag == "Node_Pickup"`인 노드와 `terrain_tag == "Node_Destination"`인 노드를 조회해 하나씩 무작위로 짝지어 `mission_type="Delivery"`인 `Mission(status="Pending")`을 생성한다.
   - 단, 현재 맵에는 Pickup 노드가 **1개뿐**이다(`scene_dump.json` 확인: `Node_Pickup` 1개, `Node_Destination` 24개). 즉 모든 배달 임무의 출발 Pickup은 항상 같은 1곳이 된다. 이는 맵 설계상 사실이므로 그대로 반영하되, 로직에서 "Pickup 후보가 여러 개"라고 가정하는 코드를 짜지 않는다(과설계 방지).
3. `PathPlanningService.find_path(from, to, robot)`를 호출해 경로가 존재하는지(빈 리스트가 아닌지) 사전 검증한다. 빈 리스트면(예: 휠 로봇이 계단을 거쳐야만 닿는 목적지) 그 Destination을 후보에서 제외하고 다른 Destination으로 재시도한다.
4. 검증된 목적지 노드의 좌표(x, y, z)와 node id를 사용해 `bridge.assign_mission(robot_id, dest_node_id, x, y, z)`를 호출하고, `mission.status`를 `"Active"`로, `started_at`을 현재 시각으로 갱신한다.
5. **검증:** 임시 스크립트로 1개 로봇에 대해 `assign_next_mission`을 호출해, `missions` 테이블에 새 row가 `Pending→Active`로 바뀌는지, Unity가 실제로 명령을 받아 이동을 시작하는지 직접 확인한다.

---

## 6. 단계 6 — 임무 완료 연동

**대상 파일:** `src/infrastructure/bridge/push_feedback.py`

1. 현재 `push_feedback.py`는 `type == "FEEDBACK"`이면 `from_node_id`/`to_node_id`로 `map_edges`를 찾아 통계를 갱신하고 `mission_logs`에 L/S/E를 적재한다(기존 Phase 4 로직, 변경하지 않음).
2. 추가로, 이 `to_node_id`가 어떤 `missions` row의 목적지(`to_node_id`)와 일치하고 그 row의 `status == "Active"`이면, 해당 `missions.status`를 `"Completed"`로, `completed_at`을 현재 시각으로 갱신한다.
3. 일치하는 Active 임무가 없으면(예: 단순 구간 이동, 혹은 이미 완료 처리됨) 조용히 넘어간다(에러 아님).
4. **검증:** 5단계에서 만든 임무가 실제로 목적지에 도착했을 때, `push_feedback.py` 실행 로그와 Supabase 조회로 `missions.status`가 `Completed`로 바뀌는지 직접 확인한다.

---

## 7. 단계 7 — 통합 검증 (전체 흐름 1회 실행)

1. Unity 플레이 모드에서 9대 로봇이 스폰된 상태로 둔다.
2. Python에서 `MissionAssignmentService.assign_next_mission("Wheeled-01")`을 호출한다.
3. 다음을 순서대로 직접 확인하고 보고한다(추측이 아니라 실제 로그/쿼리 결과):
   - `missions` 테이블에 `Pending`→`Active` row 생성 확인
   - Unity 콘솔에 `ASSIGN_MISSION` 수신 로그 확인
   - 로봇이 실제로 목적지를 향해 이동 시작 확인(에디터에서 시각적으로)
   - 도착 후 `push_feedback.py` 실행 로그(FEEDBACK 타입) 확인
   - `mission_logs`에 새 row 적재 확인
   - `missions.status`가 `Completed`로 갱신 확인
4. 휠 로봇에게 계단을 거쳐야 하는 Destination을 강제로 지정해(테스트용), 5단계의 사전 검증(`find_path` 빈 리스트 시 후보 제외)이 의도대로 동작하는지도 별도로 확인한다.

---

## 부록: 본 명세서가 의존하는 Spec B 항목

- `robots` 테이블에 9개 row 등록 (Spec B 1단계) — 4장의 `missions.robot_id` FK가 의미를 가지려면 필요.
- `robots.status` 컬럼 (Spec B) — 5단계의 "Idle 상태 로봇만 배정" 조건에 필요.

두 명세서는 병행 가능하지만, 단계 4(임무 모델)와 단계 5(배정 로직)를 완전히 검증하려면 Spec B의 해당 항목이 먼저 끝나 있어야 한다.
