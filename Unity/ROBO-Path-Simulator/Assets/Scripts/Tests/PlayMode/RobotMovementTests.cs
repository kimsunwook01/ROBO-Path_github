using System.Collections;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;
using UnityEngine.AI;
using Unity.AI.Navigation;
using ROBOPath.Robot;

namespace ROBOPath.Tests.PlayMode
{
    public class RobotMovementTests
    {
        private GameObject environment;
        // 다른 테스트(Phase3aPlayTests 등)가 로드한 씬과의 NavMesh 충돌을 방지하기 위해
        // 충분히 먼 좌표에 테스트 환경을 배치
        private readonly Vector3 testOrigin = new Vector3(5000, 0, 5000);

        [SetUp]
        public void SetUp()
        {
            environment = new GameObject("Environment");
            
            var floor = GameObject.CreatePrimitive(PrimitiveType.Plane);
            floor.transform.parent = environment.transform;
            floor.transform.position = testOrigin;
            floor.transform.localScale = new Vector3(10, 1, 10);
            
            var stair = GameObject.CreatePrimitive(PrimitiveType.Cube);
            stair.transform.parent = environment.transform;
            stair.transform.position = testOrigin + new Vector3(0, 0.5f, 5);
            stair.transform.localScale = new Vector3(10, 1, 5);
            stair.tag = "Path_Stair";

            var surface = environment.AddComponent<NavMeshSurface>();
            surface.BuildNavMesh();
        }

        [TearDown]
        public void TearDown()
        {
            if (environment != null) Object.DestroyImmediate(environment);
        }

        [UnityTest]
        public IEnumerator WheeledRobot_RejectsPathToStairs()
        {
            if (!Application.isPlaying)
            {
                Assert.Ignore("PlayMode 전용 테스트: Test Runner의 PlayMode 탭에서 실행하세요.");
                yield break;
            }

            var robotObj = new GameObject("Robot");
            var identify = robotObj.AddComponent<RobotIdentify>();
            identify.platform = RobotPlatform.Wheeled;
            var agent = robotObj.AddComponent<NavMeshAgent>();
            var controller = robotObj.AddComponent<RobotController>();

            // 테스트 원점의 NavMesh 위로 에이전트를 Warp
            if (NavMesh.SamplePosition(testOrigin, out NavMeshHit hit, 5.0f, NavMesh.AllAreas))
            {
                agent.Warp(hit.position);
            }
            
            yield return null;
            yield return null;

            Assert.IsTrue(agent.isOnNavMesh, "Agent must be on NavMesh before test");

            // 계단 영역으로 목적지 설정
            controller.SetDestination(testOrigin + new Vector3(0, 1, 6));

            yield return null;

            // 바퀴형 로봇은 Path_Stair를 포함한 경로를 거부해야 함
            Assert.IsFalse(agent.hasPath, "Wheeled robot should reject path through stairs");

            if (robotObj != null) Object.DestroyImmediate(robotObj);
        }

        [UnityTest]
        public IEnumerator SetDestination_ResetsManualInterventionFlag()
        {
            var robotObj = new GameObject("Robot");
            var identify = robotObj.AddComponent<RobotIdentify>();
            identify.platform = RobotPlatform.Legged;
            var agent = robotObj.AddComponent<NavMeshAgent>();
            var controller = robotObj.AddComponent<RobotController>();

            robotObj.transform.position = testOrigin;
            yield return null;

            controller.manualInterventionOccurred = true;
            controller.SetDestination(testOrigin + new Vector3(0, 0, 2));

            Assert.IsFalse(controller.manualInterventionOccurred);

            if (robotObj != null) Object.DestroyImmediate(robotObj);
        }
    }
}
