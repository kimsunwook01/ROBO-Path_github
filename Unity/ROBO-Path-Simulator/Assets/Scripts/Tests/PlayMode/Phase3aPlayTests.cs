using System.Collections;
using System.Collections.Generic;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;
using UnityEngine.AI;
using UnityEngine.SceneManagement;
using UnityEditor.SceneManagement;

namespace ROBOPath.Tests.PlayMode
{
    public class Phase3aPlayTests
    {
        [UnitySetUp]
        public IEnumerator Setup()
        {
            if (!Application.isPlaying)
                yield break;

            // PlayMode 전용: 씬을 Build Settings 없이 로드
            EditorSceneManager.LoadSceneInPlayMode(
                "Assets/Scenes/CampusMainMap.unity",
                new LoadSceneParameters(LoadSceneMode.Single));
            yield return null; // wait one frame for scene initialization
        }

        [UnityTest]
        public IEnumerator Spawner_InstantiatesRobots_OnNavMesh()
        {
            if (!Application.isPlaying)
            {
                Assert.Ignore("PlayMode 전용 테스트: Test Runner의 PlayMode 탭에서 실행하세요.");
                yield break;
            }

            // Find Spawner or create one
            GameObject spawnerObj = new GameObject("TestSpawner");
            var spawner = spawnerObj.AddComponent<RobotSpawner>();
            
            #if UNITY_EDITOR
            spawner.wheeledPrefab = UnityEditor.AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Prefabs/Robot/Robot_Wheeled.prefab");
            spawner.leggedPrefab = UnityEditor.AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Prefabs/Robot/Robot_Legged.prefab");
            #endif

            spawner.SpawnRobots();
            
            yield return new WaitForSeconds(0.5f); // Wait for NavMesh agent to snap to surface

            var wheeled = GameObject.Find("Robot_Wheeled(Clone)");
            var legged = GameObject.Find("Robot_Legged(Clone)");

            Assert.IsNotNull(wheeled, "Wheeled robot was not spawned");
            Assert.IsNotNull(legged, "Legged robot was not spawned");

            var agentW = wheeled.GetComponent<NavMeshAgent>();
            var agentL = legged.GetComponent<NavMeshAgent>();

            Assert.IsTrue(agentW.isOnNavMesh, "Wheeled robot failed to snap to NavMesh");
            Assert.IsTrue(agentL.isOnNavMesh, "Legged robot failed to snap to NavMesh");

            // Cleanup
            Object.DestroyImmediate(spawnerObj);
            Object.DestroyImmediate(wheeled);
            Object.DestroyImmediate(legged);
        }
    }
}
