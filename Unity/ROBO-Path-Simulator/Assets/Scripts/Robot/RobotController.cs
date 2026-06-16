using UnityEngine;
using UnityEngine.AI;

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

        public float manualMoveSpeed = 3f;
        public float manualTurnSpeed = 120f;

        private Vector3? currentDestination = null;

        void Awake()
        {
            agent = GetComponent<NavMeshAgent>();
            identify = GetComponent<RobotIdentify>();
            telemetrySink = GetComponent<ITelemetrySink>();
        }

        void Update()
        {
            if (isManualMode)
            {
                HandleManualMovement();
            }
            else
            {
                CheckDestinationReached();
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
                if (currentDestination.HasValue)
                {
                    // Re-apply path, but DO NOT reset manualInterventionOccurred here
                    // because the user says: "거점에서 자율로 깨끗이 재시작할 때 리셋한다"
                    // meaning SetDestination resets it, not resuming auto.
                    SetDestinationInternal(currentDestination.Value);
                }
            }
        }

        private void HandleManualMovement()
        {
            float v = Input.GetAxis("Vertical");
            float h = Input.GetAxis("Horizontal");

            if (Mathf.Abs(v) > 0.01f || Mathf.Abs(h) > 0.01f)
            {
                manualInterventionOccurred = true;

                transform.Rotate(Vector3.up, h * manualTurnSpeed * Time.deltaTime);

                Vector3 moveDir = transform.forward * v * manualMoveSpeed * Time.deltaTime;
                agent.Move(moveDir);

                if (!agent.isOnNavMesh)
                {
                    if (NavMesh.SamplePosition(transform.position, out NavMeshHit hit, 2.0f, NavMesh.AllAreas))
                    {
                        transform.position = hit.position;
                    }
                }
            }
        }

        public void SetDestination(Vector3 dest)
        {
            manualInterventionOccurred = false; // Reset on clean restart
            currentDestination = dest;
            if (!isManualMode)
            {
                SetDestinationInternal(dest);
            }
        }

        private void SetDestinationInternal(Vector3 dest)
        {
            if (agent == null || !agent.isOnNavMesh) return;

            NavMeshPath path = new NavMeshPath();
            if (agent.CalculatePath(dest, path))
            {
                // 부분 경로(도달 불가) 거부 — 배달 로봇이 도달할 수 없는 목적지로 부분 주행하는 것을 방지
                if (path.status != UnityEngine.AI.NavMeshPathStatus.PathComplete)
                {
                    Debug.LogWarning($"[RobotController] Path rejected for {identify.platform} — destination unreachable (status: {path.status})");
                    agent.ResetPath();
                    return;
                }

                if (ValidatePath(path))
                {
                    agent.SetPath(path);
                }
                else
                {
                    Debug.LogWarning($"[RobotController] Path rejected for {identify.platform} — terrain validation failed");
                    agent.ResetPath();
                }
            }
        }

        public bool ValidatePath(NavMeshPath path)
        {
            if (identify.platform != RobotPlatform.Wheeled) return true;

            for (int i = 0; i < path.corners.Length - 1; i++)
            {
                Vector3 start = path.corners[i];
                Vector3 end = path.corners[i + 1];
                float dist = Vector3.Distance(start, end);

                for (float d = 0; d <= dist; d += 1.0f)
                {
                    Vector3 samplePoint = Vector3.Lerp(start, end, d / dist);
                    samplePoint.y += 0.5f;

                    if (Physics.Raycast(samplePoint, Vector3.down, out RaycastHit hit, 2f))
                    {
                        if (hit.collider.CompareTag("Path_Stair")) return false;

                        float angle = Vector3.Angle(Vector3.up, hit.normal);
                        if (angle > 15.0f) return false;
                    }
                }
            }
            return true;
        }

        private void CheckDestinationReached()
        {
            if (!agent.pathPending && agent.hasPath && agent.remainingDistance <= agent.stoppingDistance)
            {
                if (!agent.hasPath || agent.velocity.sqrMagnitude == 0f)
                {
                    agent.ResetPath();
                    
                    if (!manualInterventionOccurred && telemetrySink != null)
                    {
                        string terrainTag = "Terrain_Flat";
                        if (Physics.Raycast(transform.position + Vector3.up * 0.5f, Vector3.down, out RaycastHit hit, 2f))
                        {
                            if (!string.IsNullOrEmpty(hit.collider.tag) && hit.collider.tag != "Untagged")
                            {
                                terrainTag = hit.collider.tag;
                            }
                        }

                        FeedbackMetrics metrics = FeedbackCalculator.ComputeMetrics(identify.platform, terrainTag);
                        telemetrySink.EmitFeedback(identify.platform, terrainTag, metrics.L, metrics.S, metrics.E);
                    }
                }
            }
        }
    }
}
