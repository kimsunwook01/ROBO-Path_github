using UnityEngine;

namespace ROBOPath.Robot
{
    public interface ITelemetrySink
    {
        void EmitFeedback(RobotPlatform platform, string terrainTag, float? load, float? stability, float? efficiency);
        void EmitDiscovery(Vector3 nodePos);
    }
}
