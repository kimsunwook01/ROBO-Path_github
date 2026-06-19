using UnityEngine;

namespace ROBOPath.Robot
{
    public interface ITelemetrySink
    {
        void EmitFeedback(RobotPlatform platform, string fromNodeId, string toNodeId, float? load, float? stability, float? efficiency, float batteryPct);
        void EmitDiscovery(Vector3 nodePos);
        // 최종 목적지 도달 실패(경로 막힘/끊김) 시 호출. Python 쪽이 임무를 Failed 처리하고
        // 다음 임무를 재배정하도록 신호를 보낸다. (robotId = 로봇 이름, toNodeId = 목적지 scene-dump ID)
        void EmitMissionFailed(string robotId, string toNodeId, string reason);
    }
}
