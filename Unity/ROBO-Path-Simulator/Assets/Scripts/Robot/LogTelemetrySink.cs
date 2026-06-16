using UnityEngine;

namespace ROBOPath.Robot
{
    public class LogTelemetrySink : MonoBehaviour, ITelemetrySink
    {
        public void EmitFeedback(RobotPlatform platform, string terrainTag, float? load, float? stability, float? efficiency)
        {
            if (load.HasValue && stability.HasValue && efficiency.HasValue)
            {
                Debug.Log($"[Telemetry] Platform: {platform}, Terrain: {terrainTag}, L: {load.Value:F3}, S: {stability.Value:F3}, E: {efficiency.Value:F3}");
            }
            else
            {
                Debug.Log($"[Telemetry] Platform: {platform}, Terrain: {terrainTag}, Traversable: False (L/S/E: null)");
            }
        }

        public void EmitDiscovery(Vector3 nodePos)
        {
            Debug.Log($"[Telemetry] Node discovered at: {nodePos}");
        }
    }
}
