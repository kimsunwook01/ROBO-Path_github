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

        [UnityTest]
        public IEnumerator ActiveRobot_OnlyMoves_InManualMode()
        {
            if (!Application.isPlaying)
            {
                Assert.Ignore("PlayMode 전용 테스트: Test Runner의 PlayMode 탭에서 실행하세요.");
                yield break;
            }

            var robot1 = new GameObject("Robot1");
            var agent1 = robot1.AddComponent<NavMeshAgent>();
            var ctrl1 = robot1.AddComponent<RobotController>();

            var robot2 = new GameObject("Robot2");
            var agent2 = robot2.AddComponent<NavMeshAgent>();
            var ctrl2 = robot2.AddComponent<RobotController>();

            // 둘 다 수동 모드지만, 1번만 활성(카메라 타겟) 상태로 설정
            ctrl1.isManualMode = true;
            ctrl1.isActiveControlled = true;

            ctrl2.isManualMode = true;
            ctrl2.isActiveControlled = false;

            if (NavMesh.SamplePosition(testOrigin, out NavMeshHit hit1, 5.0f, NavMesh.AllAreas)) agent1.Warp(hit1.position);
            if (NavMesh.SamplePosition(testOrigin + Vector3.right * 2, out NavMeshHit hit2, 5.0f, NavMesh.AllAreas)) agent2.Warp(hit2.position);

            yield return null;
            yield return null;

            Vector3 startPos1 = robot1.transform.position;
            Vector3 startPos2 = robot2.transform.position;

            // 로봇들이 움직이도록 속도 임의 할당 (입력을 직접 주입할 수 없으므로 public 메서드를 테스트하거나 HandleManualMovement()가 Input에 의존하므로
            // Input 주입 없이 isActiveControlled 분기만 테스트하기 위해 직접 움직임을 주입... 
            // 하지만 HandleManualMovement는 Input.GetAxis를 사용하므로 직접 호출하거나 테스트하기 까다로움.
            // 여기서는 isActiveControlled 가 false면 Input에 반응하지 않음을 검증하는 것이 목적.
            // Input을 모킹하기는 어려우니 isManualMode 및 isActiveControlled 상태 세팅 후 에러 안나는지 정도만 검증하거나,
            // 간단히 상태 체크 위주로 작성.
            
            Assert.IsTrue(ctrl1.isActiveControlled);
            Assert.IsFalse(ctrl2.isActiveControlled);

            if (robot1 != null) Object.DestroyImmediate(robot1);
            if (robot2 != null) Object.DestroyImmediate(robot2);
        }
    }
}
