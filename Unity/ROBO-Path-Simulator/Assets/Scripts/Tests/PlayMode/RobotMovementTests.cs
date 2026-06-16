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

        [SetUp]
        public void SetUp()
        {
            environment = new GameObject("Environment");
            
            var floor = GameObject.CreatePrimitive(PrimitiveType.Plane);
            floor.transform.parent = environment.transform;
            floor.transform.position = Vector3.zero;
            floor.transform.localScale = new Vector3(10, 1, 10);
            
            var stair = GameObject.CreatePrimitive(PrimitiveType.Cube);
            stair.transform.parent = environment.transform;
            stair.transform.position = new Vector3(0, 0.5f, 5);
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

        /// <summary>NavMesh 위의 유효한 위치로 에이전트를 Warp하는 헬퍼</summary>
        private bool WarpAgentToNavMesh(NavMeshAgent agent, Vector3 desiredPosition)
        {
            if (NavMesh.SamplePosition(desiredPosition, out NavMeshHit hit, 5.0f, NavMesh.AllAreas))
            {
                agent.Warp(hit.position);
                return true;
            }
            return false;
        }

        [UnityTest]
        public IEnumerator WheeledRobot_RejectsPathToStairs()
        {
            var robotObj = new GameObject("Robot");
            var identify = robotObj.AddComponent<RobotIdentify>();
            identify.platform = RobotPlatform.Wheeled;
            var agent = robotObj.AddComponent<NavMeshAgent>();
            var controller = robotObj.AddComponent<RobotController>();

            // NavMesh 위의 유효한 위치로 에이전트를 Warp
            Assert.IsTrue(WarpAgentToNavMesh(agent, Vector3.zero), "Failed to warp agent to NavMesh");
            
            yield return null; // Wait one frame for agent to settle

            Assert.IsTrue(agent.isOnNavMesh, "Agent must be on NavMesh before test");

            controller.SetDestination(new Vector3(0, 1, 6)); // 계단 영역

            yield return null; // Wait one frame for path calculation

            Assert.IsFalse(agent.hasPath);
            Assert.AreEqual(0, agent.velocity.sqrMagnitude);

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

            // NavMesh 위의 유효한 위치로 에이전트를 Warp
            Assert.IsTrue(WarpAgentToNavMesh(agent, Vector3.zero), "Failed to warp agent to NavMesh");

            yield return null;

            controller.manualInterventionOccurred = true;
            controller.SetDestination(new Vector3(0, 0, 2));

            Assert.IsFalse(controller.manualInterventionOccurred);

            if (robotObj != null) Object.DestroyImmediate(robotObj);
        }
    }
}
