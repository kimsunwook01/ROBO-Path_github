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

        public bool isManualMode = false;
        public bool manualInterventionOccurred = false;
        public bool isActiveControlled = false;

        public float manualMoveSpeed = 3f;
        public float manualTurnSpeed = 10f;

        [Header("Waypoint Navigation")]
        [Tooltip("Inspector 값에 관계없이 Awake에서 코드 기본값으로 재설정됨")]
        public float waypointArrivalRadius = 8.0f;
        public float finalArrivalRadius = 8.0f;

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
            waypointArrivalRadius = 8.0f;
            finalArrivalRadius = 8.0f;
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
                        Debug.Log($"[RobotController] {identify.robotId}: emitting FEEDBACK (terrain={terrainTag}, L={metrics.L}, S={metrics.S}, E={metrics.E})");
                        telemetrySink.EmitFeedback(identify.platform, fromNodeId, finalDestNodeId, metrics.L, metrics.S, metrics.E);
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
                // 디버그: NavMeshAgent가 멈춰있는데 아직 도달 못 한 경우
                if (!agent.pathPending && !agent.hasPath && agent.velocity.sqrMagnitude < 0.01f)
                {
                    Debug.LogWarning($"[RobotController] {identify.robotId}: STUCK at wp {currentWaypointIndex}/{totalWaypoints} " +
                        $"dist={dist:F1}m (threshold={threshold:F1}m) " +
                        $"robot=({transform.position.x:F1},{transform.position.y:F1},{transform.position.z:F1}) " +
                        $"target=({currentWaypoint.Value.x:F1},{currentWaypoint.Value.y:F1},{currentWaypoint.Value.z:F1})");

                    // 도달하지 못한 웨이포인트를 건너뛰고 다음으로 진행
                    Debug.LogWarning($"[RobotController] {identify.robotId}: skipping unreachable waypoint, advancing...");
                    agent.ResetPath();
                    AdvanceToNextWaypoint();
                }
            }
        }
    }
}
