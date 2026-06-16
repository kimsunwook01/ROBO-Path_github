using NUnit.Framework;
using UnityEngine;
using ROBOPath.Tile;

namespace ROBOPath.Tests.EditMode
{
    /// <summary>
    /// HazardTileController 상태 전환 및 MeshRenderer 연동을 검증하는 EditMode 테스트.
    /// </summary>
    public class HazardTileControllerTests
    {
        private GameObject go;
        private HazardTileController controller;

        [SetUp]
        public void SetUp()
        {
            // MeshRenderer가 포함된 프리미티브로 테스트 오브젝트 생성
            go = GameObject.CreatePrimitive(PrimitiveType.Cube);
            controller = go.AddComponent<HazardTileController>();
        }

        [TearDown]
        public void TearDown()
        {
            if (go != null) Object.DestroyImmediate(go);
        }

        [Test]
        public void HazardTile_IsInvisible_WhenStartActiveIsFalse()
        {
            // startActive = false (기본값) → Start() 대신 직접 호출
            controller.startActive = false;
            controller.SetHazardActive(false);

            MeshRenderer mr = go.GetComponent<MeshRenderer>();
            Assert.IsFalse(mr.enabled, "비활성 상태에서 MeshRenderer는 꺼져 있어야 한다.");
            Assert.IsFalse(controller.IsActive, "IsActive는 false여야 한다.");
        }

        [Test]
        public void HazardTile_IsVisible_AfterSetActiveTrue()
        {
            controller.SetHazardActive(true);

            MeshRenderer mr = go.GetComponent<MeshRenderer>();
            Assert.IsTrue(mr.enabled, "활성 상태에서 MeshRenderer는 켜져 있어야 한다.");
            Assert.IsTrue(controller.IsActive, "IsActive는 true여야 한다.");
        }

        [Test]
        public void HazardTile_TogglesCorrectly_BetweenStates()
        {
            MeshRenderer mr = go.GetComponent<MeshRenderer>();

            controller.SetHazardActive(true);
            Assert.IsTrue(mr.enabled, "활성 시 MeshRenderer enabled == true");

            controller.SetHazardActive(false);
            Assert.IsFalse(mr.enabled, "비활성 시 MeshRenderer enabled == false");

            controller.SetHazardActive(true);
            Assert.IsTrue(mr.enabled, "재활성 시 MeshRenderer enabled == true");
        }

        [Test]
        public void HazardTile_ColliderAlwaysEnabled()
        {
            // Collider는 상태 변화와 무관하게 항상 활성 유지
            Collider col = go.GetComponent<Collider>();

            controller.SetHazardActive(false);
            Assert.IsTrue(col.enabled, "비활성 상태에서도 Collider는 활성이어야 한다.");

            controller.SetHazardActive(true);
            Assert.IsTrue(col.enabled, "활성 상태에서도 Collider는 활성이어야 한다.");
        }
    }
}
