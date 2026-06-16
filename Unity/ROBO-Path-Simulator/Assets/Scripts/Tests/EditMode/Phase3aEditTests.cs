using System.Collections;
using System.Collections.Generic;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.AI;
using UnityEditor;

namespace ROBOPath.Tests.EditMode
{
    public class Phase3aEditTests
    {
        private GameObject wheeledPrefab;
        private GameObject leggedPrefab;

        [SetUp]
        public void Setup()
        {
            wheeledPrefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Prefabs/Robot/Robot_Wheeled.prefab");
            leggedPrefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Prefabs/Robot/Robot_Legged.prefab");
        }

        [Test]
        public void WheeledPrefab_HasCorrectComponentsAndLayer()
        {
            Assert.IsNotNull(wheeledPrefab, "Wheeled prefab not found");
            
            // Layer
            Assert.AreEqual(LayerMask.NameToLayer("Robot"), wheeledPrefab.layer, "Wheeled prefab layer is not Robot");

            // Identify
            var identify = wheeledPrefab.GetComponent<RobotIdentify>();
            Assert.IsNotNull(identify, "RobotIdentify missing");
            Assert.AreEqual(RobotPlatform.Wheeled, identify.platform);

            // Rigidbody
            var rb = wheeledPrefab.GetComponent<Rigidbody>();
            Assert.IsNotNull(rb, "Rigidbody missing");
            Assert.IsTrue(rb.isKinematic, "Rigidbody must be kinematic");

            // Collider
            var col = wheeledPrefab.GetComponent<BoxCollider>();
            Assert.IsNotNull(col, "Root BoxCollider missing");

            // NavMeshAgent
            var agent = wheeledPrefab.GetComponent<NavMeshAgent>();
            Assert.IsNotNull(agent, "NavMeshAgent missing");
            Assert.AreEqual(2.5f, agent.radius, 0.01f, "Agent radius must be 2.5");
            
            // Area Mask (Walkable + Road)
            int walkable = NavMesh.GetAreaFromName("Walkable");
            int road = NavMesh.GetAreaFromName("Road");
            int expectedMask = (1 << walkable) | (1 << road);
            Assert.AreEqual(expectedMask, agent.areaMask, "Wheeled Area Mask must be Walkable + Road");

            // SensorOrigin
            Transform sensorOrigin = wheeledPrefab.transform.Find("Body/Sensor/SensorOrigin") ?? wheeledPrefab.transform.Find("Sensor/SensorOrigin");
            // Depending on hierarchy. Let's just search recursively
            bool foundSensor = false;
            foreach (Transform t in wheeledPrefab.GetComponentsInChildren<Transform>(true))
            {
                if (t.name == "SensorOrigin") foundSensor = true;
            }
            Assert.IsTrue(foundSensor, "SensorOrigin not found in hierarchy");
        }

        [Test]
        public void LeggedPrefab_HasCorrectComponentsAndLayer()
        {
            Assert.IsNotNull(leggedPrefab, "Legged prefab not found");
            
            Assert.AreEqual(LayerMask.NameToLayer("Robot"), leggedPrefab.layer, "Legged prefab layer is not Robot");

            var identify = leggedPrefab.GetComponent<RobotIdentify>();
            Assert.IsNotNull(identify);
            Assert.AreEqual(RobotPlatform.Legged, identify.platform);

            var rb = leggedPrefab.GetComponent<Rigidbody>();
            Assert.IsTrue(rb.isKinematic);

            var agent = leggedPrefab.GetComponent<NavMeshAgent>();
            Assert.AreEqual(2.5f, agent.radius, 0.01f);
            Assert.AreEqual(NavMesh.AllAreas, agent.areaMask);
        }
    }
}
