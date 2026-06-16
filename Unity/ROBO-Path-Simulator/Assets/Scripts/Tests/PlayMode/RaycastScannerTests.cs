using System.Collections;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;
using ROBOPath.Robot;

namespace ROBOPath.Tests.PlayMode
{
    public class MockTelemetrySink : MonoBehaviour, ITelemetrySink
    {
        public int DiscoveryCount = 0;
        public void EmitFeedback(RobotPlatform platform, string terrainTag, float? load, float? stability, float? efficiency) {}
        public void EmitDiscovery(Vector3 nodePos) { DiscoveryCount++; }
    }

    public class RaycastScannerTests
    {
        [UnityTest]
        public IEnumerator RaycastScanner_DiscoversNode_ButIgnoresRobotLayer()
        {
            var robotObj = new GameObject("Robot");
            robotObj.layer = LayerMask.NameToLayer("Robot");
            var col = robotObj.AddComponent<BoxCollider>();
            col.size = new Vector3(1, 2, 1);
            
            var sink = robotObj.AddComponent<MockTelemetrySink>();
            var scanner = robotObj.AddComponent<RaycastScanner>();
            scanner.scanInterval = 0.05f;

            // Node를 로봇 정면(+Z)에 배치
            var nodeObj = GameObject.CreatePrimitive(PrimitiveType.Cube);
            nodeObj.name = "Node_Station";
            nodeObj.transform.position = new Vector3(0, 0, 5);

            // 물리 엔진이 새로운 Collider를 등록할 시간 확보
            yield return new WaitForFixedUpdate();
            yield return new WaitForFixedUpdate();

            // 스캔이 충분히 실행될 때까지 대기 (최소 5회 스캔 기회)
            yield return new WaitForSeconds(0.5f);

            Assert.GreaterOrEqual(sink.DiscoveryCount, 1,
                $"Scanner should discover Node_Station but DiscoveryCount was {sink.DiscoveryCount}");

            if (robotObj != null) Object.DestroyImmediate(robotObj);
            if (nodeObj != null) Object.DestroyImmediate(nodeObj);
        }
    }
}
