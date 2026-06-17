# [Spec B] 로봇 상태 / 배터리 스키마 구현 명세서

> 작성일: 2026-06-17
> 선행 문서: ROBO-Path_Dashboard_Data_Contract.md (2장, 7장 참조)
> 목적: `robots` 테이블에 실제 row를 등록하고, 상태(status)·배터리(battery_pct) 등을 주기적으로 갱신하는 경로를 만든다.

---

## 0. 선행 확인 사항

### 0.1 `robots` 테이블에 row가 없다

`supabase/migrations/20260516190000_init_schema.sql`의 `robots` 테이블은 스키마만 정의되어 있고, 9대 로봇에 대응하는 실제 row를 만드는 시드(seed) 작업이 어디에도 없다. `src/infrastructure/bridge/push_feedback.py`는 Phase 4에서 `MissionLog.robot_id=None`으로 FK 위반을 피하는 방식으로 단순화했으므로(이전 작업 기록 확인됨), 지금까지 `robots` 테이블에 실제로 INSERT를 시도한 코드가 없다.

### 0.2 효율성(E) 지표는 배터리를 실측하지 않음

`0_Document/ROBO-Path_Design_Report.md`(원안)는 E를 "배터리 전력량 소모 효율"로 정의했으나, 이후 `0_Document/ROBO-Path_Unity_Simulator_Architecture.md`(구현 기준 문서)는 "예상 이동시간 대비 실제 소요 시간 비율"로 재정의했다. 실제 `Unity/.../Robot/FeedbackCalculator.cs`도 시간 비율 정의를 따른다(직접 확인됨). 따라서 배터리 시스템은 이 E 지표를 그대로 재사용할 수 없고, 별도의 단순 소모 모델을 새로 둔다(7장 참조).

---

## 1. 단계 1 — `robots` 테이블 시드 및 Python 모델 확장

**대상 파일:** 신규 마이그레이션, `src/domain/models/metadata.py`

1. 마이그레이션 SQL로 `robots` 테이블에 컬럼을 추가한다.
   ```sql
   ALTER TABLE robots ADD COLUMN status VARCHAR(20) DEFAULT 'Idle'
       CHECK (status IN ('Idle', 'Charging', 'Delivery', 'Exploring', 'Returning'));
   ALTER TABLE robots ADD COLUMN battery_pct FLOAT DEFAULT 100.0
       CHECK (battery_pct >= 0.0 AND battery_pct <= 100.0);
   ALTER TABLE robots ADD COLUMN current_speed_mps FLOAT DEFAULT 0.0;
   ALTER TABLE robots ADD COLUMN current_mission_id UUID REFERENCES missions(id) ON DELETE SET NULL;
   ```
   `current_mission_id`는 Spec A의 `missions` 테이블이 먼저 존재해야 FK가 성립한다. Spec A 4단계 이후에 이 마이그레이션을 적용한다(순서 의존성).
2. `src/domain/models/metadata.py`의 `Robot` 모델에 위 필드를 추가한다(`status: str`, `battery_pct: float`, `current_speed_mps: float`, `current_mission_id: Optional[UUID]`).
3. 9개 row를 시드하는 1회성 스크립트(`src/scripts/seed_robots.py`)를 작성한다. Spec A 2단계에서 정한 Unity `robotId` 명명 규칙(`Wheeled-01`~`05`, `Legged-01`~`04`)과 **동일한 이름**으로 `robots.name`을 채운다. `robots.id`(UUID)는 자동 생성되므로, 이 UUID와 Unity의 문자열 `robotId`를 매핑하는 테이블이 필요한지 검토한다 — 가장 단순한 방법은 `robots.name`을 매칭 키로 쓰는 것이다(Spec A의 모든 통신은 `robotId` 문자열 기준이므로, Python 쪽에서 `SELECT * FROM robots WHERE name = 'Wheeled-01'`로 UUID를 조회).
4. **검증:** 시드 스크립트 실행 후 `SELECT name, platform, status, battery_pct FROM robots;`로 9행이 의도대로 들어갔는지 직접 조회해 결과를 보고한다.

---

## 2. 단계 2 — 상태 갱신 경로 (Unity → Python → Supabase)

**대상 파일(신규):** `Unity/.../Network/RobotStatusReporter.cs`(또는 기존 `SubprocessTelemetrySink.cs` 확장), `src/infrastructure/bridge/push_robot_status.py`(신규)

기존 `push_feedback.py`(FEEDBACK/DISCOVERY 타입 처리)와 책임을 분리하기 위해 별도 스크립트로 만든다. 같은 디렉토리에 같은 서브프로세스 호출 패턴(`SubprocessTelemetrySink.cs`가 쓰는 fire-and-forget 방식)을 그대로 따른다.

1. Unity 측: `RobotController`가 `status`(Idle/Delivery/Exploring/Returning, Charging은 3단계에서 추가)가 바뀌는 시점마다, 그리고 이동 중에는 일정 주기(예: 2초)로 `{"type":"STATUS","data":{"robot_id":"Wheeled-01","status":"Delivery","battery_pct":72.0,"current_speed_mps":0.5}}` 형태 페이로드로 `push_robot_status.py`를 호출한다.
   - `status` 변경 감지는 `RobotController`에 `private string lastReportedStatus`를 두고 비교하는 방식으로 구현한다.
   - 주기 호출은 `InvokeRepeating` 또는 코루틴으로 구현한다(기존 `RaycastScanner`의 `scanInterval` 코루틴 패턴을 참고).
2. Python 측: `push_robot_status.py`는 `robot_id`(이름 문자열)로 `robots` 테이블의 row를 찾아 `status`, `battery_pct`, `current_speed_mps`를 UPDATE한다. `get_supabase_admin_client()`(Phase 4에서 만든 service_role 클라이언트)를 사용한다.
3. **검증:** 임시로 한 로봇의 `status`를 수동으로 바꾸는 코드를 실행해(혹은 Spec A의 임무 배정 흐름과 연결해), Supabase `robots` row가 실제로 갱신되는지 직접 조회로 확인한다.

---

## 3. 단계 3 — 배터리 모델 (간이)

**대상 파일:** `Unity/.../Robot/RobotController.cs`

Data Contract 7장의 파라미터를 사용한다.

1. `RobotController`에 다음 필드를 추가한다.
   ```csharp
   public float batteryPct = 100f;
   private const float MAX_BATTERY = 100f;
   private const float CHARGE_RATE_PER_SEC = 5f;
   ```
2. 지형별 `drain_per_meter`는 `Path_Stair`/`Terrain_Slope`/`Terrain_Flat` 태그에 따라 차등 적용한다. `ValidatePath`가 이미 `Physics.Raycast`로 지형 태그를 읽는 패턴을 갖고 있으므로, 같은 방식으로 `Update()`(또는 이동 중 일정 간격)에서 현재 위치 아래 태그를 읽어 드레인율을 결정한다.
3. 이동 거리는 `agent.velocity.magnitude * Time.deltaTime`으로 매 프레임 누적하고, `batteryPct -= distance * drainRate`로 차감한다(0 미만으로 내려가지 않게 클램프).
4. `Node_Station` 콜라이더 위에 있고 `agent.velocity`가 0이면(정차 상태) `status`를 `"Charging"`으로 전환하고 `batteryPct += CHARGE_RATE_PER_SEC * Time.deltaTime`로 충전한다(100 초과 금지). 충전 완료(100.0) 또는 다음 임무 배정 시 `status`를 `"Idle"`로 되돌린다.
5. **검증:** 로봇을 수동 조작(WASD)으로 일정 거리 이동시켜 `batteryPct`가 Inspector에서 실제로 줄어드는지, 거점에 세워두면 다시 차는지 직접 확인한다. (수동 조작 중 배터리 소모도 반영할지, 자율 이동만 반영할지는 구현 시 결정하고 보고한다 — 명세에서는 강제하지 않는다.)

---

## 4. 단계 4 — 저배터리 처리 (선택, 후속 과제)

Data Contract 7장의 `low_battery_threshold = 15.0` 기준 자동 귀환 트리거는 본 명세서 범위에서 제외한다(Spec A의 임무 시스템이 먼저 안정화된 후 추가). 이번 단계에서는 `batteryPct` 값 자체가 정확히 추적되고 Supabase에 반영되는 것까지만 구현한다.

---

## 5. 통합 검증

1. 임의의 로봇 1대를 자율 모드로 일정 거리 이동시킨다(Spec A 연동 시 임무 배정으로, 독립 테스트 시 임시 `SetDestination` 호출로).
2. 이동 중 `robots.battery_pct`가 Supabase에서 감소 추세로 갱신되는지 일정 간격으로 조회해 확인한다.
3. 거점에 도착시켜 `status`가 `Charging`으로 바뀌고 `battery_pct`가 회복되는지 확인한다.
4. 모든 확인은 실제 쿼리 결과/콘솔 로그로 보고하며, "구현했다"는 진술만으로 완료 처리하지 않는다.
