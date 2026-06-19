using UnityEngine;

namespace ROBOPath.Robot
{
    public class LogTelemetrySink : MonoBehaviour, ITelemetrySink
    {
        public void EmitFeedback(RobotPlatform platform, string fromNodeId, string toNodeId, float? load, float? stability, float? efficiency, float batteryPct)
        {
            if (load.HasValue && stability.HasValue && efficiency.HasValue)
            {
                Debug.Log($"[Telemetry] Platform: {platform}, Segment: {fromNodeId} -> {toNodeId}, L: {load.Value:F3}, S: {stability.Value:F3}, E: {efficiency.Value:F3}, Battery: {batteryPct:F1}%");
            }
            else
            {
                Debug.Log($"[Telemetry] Platform: {platform}, Segment: {fromNodeId} -> {toNodeId}, Traversable: False (L/S/E: null), Battery: {batteryPct:F1}%");
            }
        }

        public void EmitDiscovery(Vector3 nodePos)
        {
            Debug.Log($"[Telemetry] Node discovered at: {nodePos}");
        }

        public void EmitMissionFailed(string robotId, string toNodeId, string reason)
        {
            Debug.LogWarning($"[Telemetry] MISSION FAILED: {robotId} -> {toNodeId} (reason: {reason})");
        }
    }
}
