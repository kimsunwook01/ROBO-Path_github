using UnityEngine;

namespace ROBOPath.Tile
{
    /// <summary>
    /// Tile_Hazard 프리팹의 활성/비활성 상태를 제어한다.
    /// 비활성 시 MeshRenderer를 꺼서 맵에서 보이지 않게 하고,
    /// Collider는 유지하여 NavMesh 통행 및 RaycastScanner 감지를 보존한다.
    /// 외부(WebSocket, 타이머)에서 SetHazardActive(bool)을 호출하여 제어한다.
    /// </summary>
    public class HazardTileController : MonoBehaviour
    {
        [Header("Initial State")]
        [Tooltip("Play 시작 시 활성화 여부. 기본값 false(비표시).")]
        public bool startActive = false;

        private MeshRenderer meshRenderer;
        private bool isActive;

        void Awake()
        {
            meshRenderer = GetComponent<MeshRenderer>();
        }

        void Start()
        {
            SetHazardActive(startActive);
        }

        /// <summary>
        /// 장애물 타일의 활성/비활성 상태를 전환한다.
        /// Phase 4 WebSocket 수신 시 이 메서드를 호출한다.
        /// </summary>
        /// <param name="active">true = 활성(형광색 표시), false = 비활성(보이지 않음)</param>
        public void SetHazardActive(bool active)
        {
            isActive = active;
            if (meshRenderer != null)
                meshRenderer.enabled = active;
        }

        /// <summary>현재 활성 상태를 반환한다.</summary>
        public bool IsActive => isActive;
    }
}
