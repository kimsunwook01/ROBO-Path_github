using UnityEngine;

namespace ROBOPath.Robot
{
    public interface ITelemetrySink
    {
        void EmitFeedback(RobotPlatform platform, string fromNodeId, string toNodeId, float? load, float? stability, float? efficiency);
        void EmitDiscovery(Vector3 nodePos);
    }
}
