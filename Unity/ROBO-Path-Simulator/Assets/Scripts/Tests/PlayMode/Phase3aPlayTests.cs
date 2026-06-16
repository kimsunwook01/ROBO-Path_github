using System.Collections;
using System.Collections.Generic;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;
using UnityEngine.AI;
using UnityEditor.SceneManagement;

namespace ROBOPath.Tests.PlayMode
{
    public class Phase3aPlayTests
    {
        [UnitySetUp]
        public IEnumerator Setup()
        {
            // Load CampusMainMap
            EditorSceneManager.LoadSceneInPlayMode("Assets/Scenes/CampusMainMap/CampusMainMap.unity", new UnityEngine.SceneManagement.LoadSceneParameters(UnityEngine.SceneManagement.LoadSceneMode.Single));
            yield return null; // wait one frame
        }

        [UnityTest]
        public IEnumerator Spawner_InstantiatesRobots_OnNavMesh()
        {
            // Find Spawner or create one
            GameObject spawnerObj = new GameObject("TestSpawner");
            var spawner = spawnerObj.AddComponent<RobotSpawner>();
            
            // Assign prefabs from resources or assetdatabase? In PlayMode test, we can't easily use AssetDatabase unless it's in Editor.
            // But we can do it if the test is running in Editor play mode. Let's use AssetDatabase to load prefab for test.
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
        }
    }
}
