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
            
            // 일반 바닥 타일 (Cube, 상면 y=0)
            var floor = GameObject.CreatePrimitive(PrimitiveType.Cube);
            floor.transform.parent = environment.transform;
            floor.transform.position = testOrigin + new Vector3(0, -0.5f, 0);
            floor.transform.localScale = new Vector3(20, 1, 10);

            // 계단 타일 (Cube, 상면 y=0 — 바닥과 동일 높이로 NavMesh 자연 연결)
            // Step Height 매직넘버에 의존하지 않음
            var stairTile = GameObject.CreatePrimitive(PrimitiveType.Cube);
            stairTile.transform.parent = environment.transform;
            stairTile.transform.position = testOrigin + new Vector3(0, -0.5f, 10);
            stairTile.transform.localScale = new Vector3(20, 1, 10);
            stairTile.tag = "Path_Stair";

            var surface = environment.AddComponent<NavMeshSurface>();
            surface.BuildNavMesh();
        }

        [TearDown]
        public void TearDown()
        {
            if (environment != null) Object.DestroyImmediate(environment);
        }

        /// <summary>
        /// 바퀴형 로봇이 Path_Stair 태그 지형을 가로지르는 경로를 거부하는지 검증.
        /// 바닥과 계단 타일이 같은 높이(y=0)에 있어 NavMesh가 자연스럽게 연결되므로,
        /// CalculatePath 는 PathComplete 경로를 반환하지만 ValidatePath 가 태그를 감지하여 거부한다.
        /// </summary>
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

            // NavMesh 위의 유효한 위치로 에이전트를 Warp (바닥 타일 위)
            if (NavMesh.SamplePosition(testOrigin, out NavMeshHit hit, 5.0f, NavMesh.AllAreas))
            {
                agent.Warp(hit.position);
            }
            
            yield return null;
            yield return null;

            Assert.IsTrue(agent.isOnNavMesh, "Agent must be on NavMesh before test");

            // 계단 타일 위의 목적지 설정 (z = testOrigin.z + 12, 계단 타일 z범위 +5~+15)
            controller.SetDestination(testOrigin + new Vector3(0, 0, 12));

            yield return null;

            // 바퀴형 로봇은 Path_Stair 태그 지형을 포함한 경로를 거부해야 함
            Assert.IsFalse(agent.hasPath, "Wheeled robot should reject path through Path_Stair terrain");

            if (robotObj != null) Object.DestroyImmediate(robotObj);
        }

        /// <summary>
        /// 도달 불가능한 목적지에 대한 부분 경로(PathPartial)를 거부하는지 검증.
        /// 배달 로봇이 목적지에 도달할 수 없을 때 부분 주행하지 않도록 한다.
        /// </summary>
        [UnityTest]
        public IEnumerator PartialPath_IsRejected_WhenDestinationUnreachable()
        {
            if (!Application.isPlaying)
            {
                Assert.Ignore("PlayMode 전용 테스트: Test Runner의 PlayMode 탭에서 실행하세요.");
                yield break;
            }

            var robotObj = new GameObject("Robot");
            var identify = robotObj.AddComponent<RobotIdentify>();
            identify.platform = RobotPlatform.Legged;
            var agent = robotObj.AddComponent<NavMeshAgent>();
            var controller = robotObj.AddComponent<RobotController>();

            // NavMesh 위의 유효한 위치로 에이전트를 Warp
            if (NavMesh.SamplePosition(testOrigin, out NavMeshHit hit, 5.0f, NavMesh.AllAreas))
            {
                agent.Warp(hit.position);
            }

            yield return null;
            yield return null;

            Assert.IsTrue(agent.isOnNavMesh, "Agent must be on NavMesh before test");

            // NavMesh 영역 밖의 도달 불가능한 목적지 설정
            controller.SetDestination(testOrigin + new Vector3(0, 0, 500));

            yield return null;

            // 부분 경로가 거부되어 hasPath == false
            Assert.IsFalse(agent.hasPath, "Partial path to unreachable destination should be rejected");

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
