using UnityEngine;
using UnityEngine.AI;
using System.Collections.Generic;

namespace ROBOPath.Robot
{
    [RequireComponent(typeof(NavMeshAgent))]
    [RequireComponent(typeof(RobotIdentify))]
    public class RobotController : MonoBehaviour
    {
        private NavMeshAgent agent;
        private RobotIdentify identify;
        private ITelemetrySink telemetrySink;

        // NavMesh Area 이름 (StairNavMeshSetup 에서 프리팹에 부여한 것과 일치해야 함)
        private const string STAIR_AREA_NAME = "Stair";
        private const string ROAD_AREA_NAME = "Road";
        // 보행 로봇의 Road Area 통행 비용 (A* cost_multiplier 와 일치: 보행 3).
        // 휠 로봇은 비용이 아니라 areaMask 에서 Road 를 완전 제외한다(연석: 도로 진입 불가).
        private const float ROAD_COST_LEGGED = 3f;
        // 참고: 장애물(Hazard) 통행 차단은 비용이 아니라 HazardTileController 의 NavMeshObstacle
        // carving 으로 처리한다(활성 시 NavMesh 를 도려내 모든 로봇 통행 차단). 여기서는 처리 안 함.

        public bool isManualMode = false;
        public bool manualInterventionOccurred = false;
        public bool isActiveControlled = false;

        public float manualMoveSpeed = 3f;
        public float manualTurnSpeed = 10f;

        [Header("Waypoint Navigation")]
        [Tooltip("Inspector 값에 관계없이 Awake에서 코드 기본값으로 재설정됨")]
        // 도달 반경이 너무 크면(그리드 10m 대비 8m) 로봇이 칸을 건너뛰고 대각선으로
        // 질러가 도로/계단을 가로지른다. 칸 절반 이하로 줄여 경로를 촘촘히 따르게 한다.
        // 단 너무 작으면 STUCK 이 재발하므로 절충값 사용(막히면 아래 skip 로직이 처리).
        public float waypointArrivalRadius = 3.5f;
        public float finalArrivalRadius = 5.0f;

        [Header("Battery (Spec B)")]
        public float batteryPct = 100f;
        private const float MAX_BATTERY = 100f;
        private const float CHARGE_RATE_PER_SEC = 5f;       // Node_Station 정차 시 초당 충전량
        private const float DRAIN_FLAT = 0.02f;             // 평지 1m당 소모
        private const float DRAIN_SLOPE = 0.05f;            // 경사/램프 1m당 소모
        private const float DRAIN_STAIR = 0.08f;            // 계단 1m당 소모
        private Vector3 lastBatteryCheckPos;               // 이동거리 누적용 이전 위치

        private string fromNodeId = "BASE";
        private string toNodeId = "unknown";

        private Queue<Vector3> waypointQueue = new Queue<Vector3>();
        private Vector3? currentWaypoint = null;
        private string finalDestNodeId = "unknown";
        private bool isNavigating = false;
        private int currentWaypointIndex = 0;
        private int totalWaypoints = 0;

        void Awake()
        {
            agent = GetComponent<NavMeshAgent>();
            identify = GetComponent<RobotIdentify>();
            telemetrySink = GetComponent<ITelemetrySink>();

            // public 필드는 Inspector/프리팹에 직렬화된 값이 코드 기본값을 덮어쓰므로,
            // 여기서 코드 값으로 강제 재설정한다 (Inspector를 직접 안 만져도 적용됨).
            waypointArrivalRadius = 3.5f;
            finalArrivalRadius = 5.0f;

            lastBatteryCheckPos = transform.position;

            // 휠 로봇은 계단(Stair Area)을 NavMesh 경로에서 제외한다.
            // 계단은 경사면 형상이라 NavMesh 가 덮어 물리적으로 올라탈 수 있는데,
            // areaMask 에서 Stair 비트를 끄면 NavMeshAgent 가 계단을 통과하는 경로를
            // 아예 만들지 않는다. 보행 로봇은 모든 Area 를 그대로 두어 계단을 사용한다.
            ApplyPlatformAreaMask();
        }

        /// <summary>
        /// 플랫폼별 NavMesh Area 통행 제어.
        /// - Stair Area: 휠 로봇은 areaMask 에서 완전 제외(통행 불가). 보행은 사용.
        /// - Road Area: 휠 로봇도 areaMask 에서 완전 제외(연석 — 평지에서 도로로 직접
        ///   진입 불가). 횡단보도 타일은 도로 위 0.5m 에 얹힌 블록이라 NavMesh 가 그
        ///   윗면을 별도 주행면(Road Area 아님)으로 굽기 때문에, 휠 로봇도 횡단보도로는
        ///   건널 수 있다. 보행 로봇은 단차 극복이 가능하므로 Road 를 비용(3)만 부여해
        ///   상황에 따라 감수하게 둔다.
        /// - Hazard Area: 기본은 통행 가능(비활성). 활성화되면 HazardTileController 가
        ///   SetAreaCost 로 비용을 높여 회피시킨다(이 메서드에선 기본 비용만 보장).
        /// </summary>
        private void ApplyPlatformAreaMask()
        {
            if (agent == null || identify == null) return;

            bool isWheeled = (identify.platform == RobotPlatform.Wheeled);

            // 1) 계단: 휠 로봇은 areaMask 에서 제외(완전 차단)
            if (isWheeled)
            {
                int stairAreaIndex = NavMesh.GetAreaFromName(STAIR_AREA_NAME);
                if (stairAreaIndex >= 0)
                {
                    agent.areaMask &= ~(1 << stairAreaIndex);
                    Debug.Log($"[RobotController] {identify.robotId}: 휠 로봇 — Stair Area(idx={stairAreaIndex}) 제외. areaMask={agent.areaMask}");
                }
                else
                {
                    Debug.LogWarning($"[RobotController] {identify.robotId}: 'Stair' Area 를 찾을 수 없음. " +
                        "Navigation Areas 에 Stair 가 등록됐는지, 재베이크했는지 확인하세요.");
                }
            }

            // 2) 도로(연석): 휠 로봇은 areaMask 제외(진입 불가), 보행 로봇은 비용만 부여
            int roadAreaIndex = NavMesh.GetAreaFromName(ROAD_AREA_NAME);
            if (roadAreaIndex >= 0)
            {
                if (isWheeled)
                {
                    // 도로 면을 아예 못 밟게 한다. 횡단보도 면은 Road Area 가 아니라 통행 가능.
                    agent.areaMask &= ~(1 << roadAreaIndex);
                    Debug.Log($"[RobotController] {identify.robotId}: 휠 로봇 — Road Area(idx={roadAreaIndex}) 제외(연석). areaMask={agent.areaMask}");
                }
                else
                {
                    // 보행 로봇은 단차 극복 가능 → 비용만 부여해 상황에 따라 감수
                    agent.SetAreaCost(roadAreaIndex, ROAD_COST_LEGGED);
                    Debug.Log($"[RobotController] {identify.robotId}: 보행 로봇 — Road Area(idx={roadAreaIndex}) 비용={ROAD_COST_LEGGED} 설정");
                }
            }
            else
            {
                Debug.LogWarning($"[RobotController] {identify.robotId}: 'Road' Area 를 찾을 수 없음. " +
                    "Navigation Areas 에 Road 가 등록됐는지, 재베이크했는지 확인하세요.");
            }
        }

        void Update()
        {
            if (isManualMode && isActiveControlled)
            {
                HandleManualMovement();
            }
            else if (!isManualMode && isNavigating)
            {
                CheckWaypointReached();
            }

            // 배터리 시뮬레이션은 모드와 무관하게 매 프레임 갱신
            UpdateBattery();
        }

        /// <summary>
        /// Spec B 배터리 간이 모델.
        /// - 이동 중: 이동거리 × 지형별 drain 만큼 차감
        /// - Node_Station 위 정차 중: 충전
        /// </summary>
        private void UpdateBattery()
        {
            float moved = Vector3.Distance(transform.position, lastBatteryCheckPos);
            lastBatteryCheckPos = transform.position;

            bool isMoving = agent.velocity.sqrMagnitude > 0.01f;

            if (isMoving && moved > 0f)
            {
                // 현재 밟고 있는 지형 태그로 drain율 결정
                float drainRate = DRAIN_FLAT;
                string tag = GetTerrainTagBelow();
                if (tag == "Path_Stair") drainRate = DRAIN_STAIR;
                else if (tag == "Terrain_Slope" || tag == "Path_Ramp") drainRate = DRAIN_SLOPE;

                batteryPct -= moved * drainRate;
                if (batteryPct < 0f) batteryPct = 0f;
            }
            else
            {
                // 정차 중 + Node_Station 위면 충전
                if (IsOnStation())
                {
                    batteryPct += CHARGE_RATE_PER_SEC * Time.deltaTime;
                    if (batteryPct > MAX_BATTERY) batteryPct = MAX_BATTERY;
                }
            }
        }

        private string GetTerrainTagBelow()
        {
            if (Physics.Raycast(transform.position + Vector3.up * 0.5f, Vector3.down, out RaycastHit hit, 2f))
            {
                if (!string.IsNullOrEmpty(hit.collider.tag) && hit.collider.tag != "Untagged")
                    return hit.collider.tag;
            }
            return "Terrain_Flat";
        }

        private bool IsOnStation()
        {
            if (Physics.Raycast(transform.position + Vector3.up * 0.5f, Vector3.down, out RaycastHit hit, 2f))
            {
                return hit.collider.CompareTag("Node_Station");
            }
            return false;
        }

        public void ToggleMode()
        {
            isManualMode = !isManualMode;
            if (isManualMode)
                agent.ResetPath();
            else if (currentWaypoint.HasValue)
                NavigateToCurrentWaypoint();
        }

        private void HandleManualMovement()
        {
            float v = Input.GetAxis("Vertical");
            float h = Input.GetAxis("Horizontal");

            if (Mathf.Abs(v) > 0.01f || Mathf.Abs(h) > 0.01f)
            {
                manualInterventionOccurred = true;

                Camera cam = Camera.main;
                if (cam != null)
                {
                    Vector3 camFwd = cam.transform.forward;
                    Vector3 camRight = cam.transform.right;
                    camFwd.y = 0; camRight.y = 0;
                    camFwd.Normalize(); camRight.Normalize();

                    Vector3 moveDir = (camFwd * v + camRight * h).normalized;
                    if (moveDir.sqrMagnitude > 0.01f)
                    {
                        Quaternion targetRotation = Quaternion.LookRotation(moveDir);
                        transform.rotation = Quaternion.Slerp(transform.rotation, targetRotation, manualTurnSpeed * Time.deltaTime);
                        agent.Move(moveDir * manualMoveSpeed * Time.deltaTime);
                    }
                }

                if (!agent.isOnNavMesh)
                {
                    if (NavMesh.SamplePosition(transform.position, out NavMeshHit hit, 2.0f, NavMesh.AllAreas))
                        transform.position = hit.position;
                }
            }
        }

        public void SetDestinationWithWaypoints(Vector3[] waypoints, string destNodeId)
        {
            manualInterventionOccurred = false;
            waypointQueue.Clear();

            foreach (var wp in waypoints)
                waypointQueue.Enqueue(wp);

            finalDestNodeId = destNodeId;
            toNodeId = destNodeId;
            isNavigating = true;
            totalWaypoints = waypoints.Length;
            currentWaypointIndex = 0;

            Debug.Log($"[RobotController] {identify.robotId}: received {waypoints.Length} waypoints -> {destNodeId}");
            AdvanceToNextWaypoint();
        }

        public void SetDestination(Vector3 dest, string targetNodeId = "unknown")
        {
            manualInterventionOccurred = false;
            waypointQueue.Clear();
            waypointQueue.Enqueue(dest);
            finalDestNodeId = targetNodeId;
            toNodeId = targetNodeId;
            isNavigating = true;
            totalWaypoints = 1;
            currentWaypointIndex = 0;
            AdvanceToNextWaypoint();
        }

        private void AdvanceToNextWaypoint()
        {
            if (waypointQueue.Count == 0)
            {
                currentWaypoint = null;
                isNavigating = false;
                return;
            }

            currentWaypoint = waypointQueue.Dequeue();
            currentWaypointIndex++;
            NavigateToCurrentWaypoint();
        }

        private void NavigateToCurrentWaypoint()
        {
            if (!currentWaypoint.HasValue || agent == null || !agent.isOnNavMesh) return;
            agent.SetDestination(currentWaypoint.Value);
        }

        /// <summary>
        /// 수평 거리(XZ)만으로 웨이포인트 도달을 판정한다.
        /// Y축(높이)은 무시 — 타일 중심 좌표와 NavMesh 표면 높이가 다를 수 있기 때문.
        /// </summary>
        private float HorizontalDistance(Vector3 a, Vector3 b)
        {
            float dx = a.x - b.x;
            float dz = a.z - b.z;
            return Mathf.Sqrt(dx * dx + dz * dz);
        }

        private void CheckWaypointReached()
        {
            if (!currentWaypoint.HasValue) return;

            float dist = HorizontalDistance(transform.position, currentWaypoint.Value);
            bool isFinalWaypoint = (waypointQueue.Count == 0);
            float threshold = isFinalWaypoint ? finalArrivalRadius : waypointArrivalRadius;

            if (dist <= threshold)
            {
                agent.ResetPath();

                if (isFinalWaypoint)
                {
                    currentWaypoint = null;
                    isNavigating = false;

                    Debug.Log($"[RobotController] {identify.robotId}: ARRIVED at {finalDestNodeId} (dist={dist:F1}m)");

                    if (!manualInterventionOccurred && telemetrySink != null)
                    {
                        string terrainTag = "Terrain_Flat";
                        if (Physics.Raycast(transform.position + Vector3.up * 0.5f, Vector3.down, out RaycastHit hit, 2f))
                        {
                            if (!string.IsNullOrEmpty(hit.collider.tag) && hit.collider.tag != "Untagged")
                                terrainTag = hit.collider.tag;
                        }

                        FeedbackMetrics metrics = FeedbackCalculator.ComputeMetrics(identify.platform, terrainTag);
                        Debug.Log($"[RobotController] {identify.robotId}: emitting FEEDBACK (terrain={terrainTag}, L={metrics.L}, S={metrics.S}, E={metrics.E}, battery={batteryPct:F1}%)");
                        telemetrySink.EmitFeedback(identify.platform, fromNodeId, finalDestNodeId, metrics.L, metrics.S, metrics.E, batteryPct);
                        fromNodeId = finalDestNodeId;
                    }
                    else
                    {
                        if (telemetrySink == null)
                            Debug.LogWarning($"[RobotController] {identify.robotId}: telemetrySink is NULL — feedback not sent");
                    }
                }
                else
                {
                    AdvanceToNextWaypoint();
                }
            }
            else
            {
                // NavMeshAgent가 멈춰있는데 아직 도달 못 한 경우 (경로 막힘/끊김)
                if (!agent.pathPending && !agent.hasPath && agent.velocity.sqrMagnitude < 0.01f)
                {
                    Debug.LogWarning($"[RobotController] {identify.robotId}: STUCK at wp {currentWaypointIndex}/{totalWaypoints} " +
                        $"dist={dist:F1}m (threshold={threshold:F1}m) " +
                        $"robot=({transform.position.x:F1},{transform.position.y:F1},{transform.position.z:F1}) " +
                        $"target=({currentWaypoint.Value.x:F1},{currentWaypoint.Value.y:F1},{currentWaypoint.Value.z:F1})");

                    agent.ResetPath();

                    if (isFinalWaypoint)
                    {
                        // 최종 목적지 도달 실패 → 조용히 멈추지 않고 MISSION_FAILED 를 보고한 뒤 정지한다.
                        // (이 신호가 있어야 push_feedback.py 가 임무를 Failed 처리하고 다음 임무를 재배정한다.
                        //  과거엔 여기서 그냥 멈춰 FEEDBACK 도 다음 임무도 없이 그 로봇 루프가 영구 정지했다.)
                        currentWaypoint = null;
                        isNavigating = false;

                        Debug.LogWarning($"[RobotController] {identify.robotId}: FINAL destination {finalDestNodeId} UNREACHABLE — emitting MISSION_FAILED");

                        if (!manualInterventionOccurred && telemetrySink != null)
                            telemetrySink.EmitMissionFailed(identify.robotId, finalDestNodeId, "unreachable");
                        else if (telemetrySink == null)
                            Debug.LogWarning($"[RobotController] {identify.robotId}: telemetrySink is NULL — MISSION_FAILED not sent");
                    }
                    else
                    {
                        // 중간 웨이포인트는 건너뛰고 다음으로 진행 (기존 동작 유지)
                        Debug.LogWarning($"[RobotController] {identify.robotId}: skipping unreachable waypoint, advancing...");
                        AdvanceToNextWaypoint();
                    }
                }
            }
        }
    }
}
