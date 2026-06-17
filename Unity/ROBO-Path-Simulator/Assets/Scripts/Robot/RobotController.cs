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
        public float waypointArrivalRadius = 5.0f;  // 웨이포인트 도달 판정 반경 (m)
        public float finalArrivalRadius = 3.0f;      // 최종 목적지 도달 판정 반경 (m)

        private string fromNodeId = "BASE";
        private string toNodeId = "unknown";

        // 웨이포인트 내비게이션
        private Queue<Vector3> waypointQueue = new Queue<Vector3>();
        private Vector3? currentWaypoint = null;
        private string finalDestNodeId = "unknown";
        private bool isNavigating = false;

        void Awake()
        {
            agent = GetComponent<NavMeshAgent>();
            identify = GetComponent<RobotIdentify>();
            telemetrySink = GetComponent<ITelemetrySink>();
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
            {
                agent.ResetPath();
            }
            else
            {
                if (currentWaypoint.HasValue)
                    NavigateToCurrentWaypoint();
            }
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

        /// <summary>
        /// A* 경로의 웨이포인트들을 순서대로 따라가도록 설정.
        /// </summary>
        public void SetDestinationWithWaypoints(Vector3[] waypoints, string destNodeId)
        {
            manualInterventionOccurred = false;
            waypointQueue.Clear();

            foreach (var wp in waypoints)
                waypointQueue.Enqueue(wp);

            finalDestNodeId = destNodeId;
            toNodeId = destNodeId;
            isNavigating = true;

            Debug.Log($"[RobotController] {identify.robotId}: received {waypoints.Length} waypoints -> {destNodeId}");
            AdvanceToNextWaypoint();
        }

        /// <summary>
        /// 단일 목적지로 직접 이동 (하위 호환).
        /// </summary>
        public void SetDestination(Vector3 dest, string targetNodeId = "unknown")
        {
            manualInterventionOccurred = false;
            waypointQueue.Clear();
            waypointQueue.Enqueue(dest);
            finalDestNodeId = targetNodeId;
            toNodeId = targetNodeId;
            isNavigating = true;
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
            NavigateToCurrentWaypoint();
        }

        private void NavigateToCurrentWaypoint()
        {
            if (!currentWaypoint.HasValue || agent == null || !agent.isOnNavMesh) return;
            agent.SetDestination(currentWaypoint.Value);
        }

        private void CheckWaypointReached()
        {
            if (!currentWaypoint.HasValue) return;

            // NavMeshAgent 내부 상태 대신 물리적 거리를 직접 측정
            float dist = Vector3.Distance(transform.position, currentWaypoint.Value);
            bool isFinalWaypoint = (waypointQueue.Count == 0);
            float threshold = isFinalWaypoint ? finalArrivalRadius : waypointArrivalRadius;

            if (dist <= threshold)
            {
                agent.ResetPath();

                if (isFinalWaypoint)
                {
                    // 최종 목적지 도착: 피드백 발생
                    currentWaypoint = null;
                    isNavigating = false;

                    Debug.Log($"[RobotController] {identify.robotId}: reached final destination {finalDestNodeId}");

                    if (!manualInterventionOccurred && telemetrySink != null)
                    {
                        string terrainTag = "Terrain_Flat";
                        if (Physics.Raycast(transform.position + Vector3.up * 0.5f, Vector3.down, out RaycastHit hit, 2f))
                        {
                            if (!string.IsNullOrEmpty(hit.collider.tag) && hit.collider.tag != "Untagged")
                                terrainTag = hit.collider.tag;
                        }

                        FeedbackMetrics metrics = FeedbackCalculator.ComputeMetrics(identify.platform, terrainTag);
                        telemetrySink.EmitFeedback(identify.platform, fromNodeId, finalDestNodeId, metrics.L, metrics.S, metrics.E);
                        fromNodeId = finalDestNodeId;
                    }
                }
                else
                {
                    // 중간 웨이포인트: 피드백 없이 다음으로
                    AdvanceToNextWaypoint();
                }
            }
        }
    }
}
