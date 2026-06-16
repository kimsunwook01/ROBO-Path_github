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

            var nodeObj = GameObject.CreatePrimitive(PrimitiveType.Cube);
            nodeObj.name = "Node_Station";
            nodeObj.transform.position = new Vector3(0, 0, 5);

            yield return new WaitForSeconds(0.15f);

            Assert.GreaterOrEqual(sink.DiscoveryCount, 1);

            Object.Destroy(robotObj);
            Object.Destroy(nodeObj);
        }
    }
}
