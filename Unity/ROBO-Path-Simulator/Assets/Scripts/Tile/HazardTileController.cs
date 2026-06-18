using UnityEngine;
using UnityEngine.AI;

namespace ROBOPath.Tile
{
    /// <summary>
    /// Tile_Hazard 프리팹의 활성/비활성 상태를 제어한다.
    ///
    /// 비활성(기본):
    ///   - MeshRenderer 꺼짐 → 맵에서 보이지 않음
    ///   - NavMeshObstacle 꺼짐 → 통행 가능
    /// 활성:
    ///   - MeshRenderer 켜짐 → 형광색 타일 시각화
    ///   - NavMeshObstacle 켜짐(carving) → 그 자리 NavMesh 를 도려내 모든 로봇 통행 차단
    ///
    /// 설계 의도:
    ///   - 향후 에디터 작업(재베이크) 없이 코드(SetHazardActive)만으로 통행을 막거나 연다.
    ///   - NavMeshObstacle 의 carving 은 런타임에 NavMesh 를 동적으로 깎으므로 재베이크 불필요.
    ///   - BoxCollider 는 건드리지 않는다 → RaycastScanner 의 장애물 감지 유지(명세 제약).
    ///   - NavMeshObstacle 컴포넌트가 없으면(미부착) MeshRenderer 토글만 수행하고
    ///     통행 차단은 건너뛴다(하위 호환). 차단 기능을 쓰려면 프리팹에 NavMeshObstacle
    ///     (Carve 체크)을 부착해야 한다.
    /// </summary>
    public class HazardTileController : MonoBehaviour
    {
        [Header("Initial State")]
        [Tooltip("Play 시작 시 활성화 여부. 기본값 false(비표시·통행가능).")]
        public bool startActive = false;

        private MeshRenderer meshRenderer;
        private NavMeshObstacle navObstacle;
        private bool isActive;

        // Awake가 호출되지 않는 EditMode 테스트 환경에서도 동작하도록 Lazy 초기화
        private MeshRenderer MeshRend
        {
            get
            {
                if (meshRenderer == null)
                    meshRenderer = GetComponent<MeshRenderer>();
                return meshRenderer;
            }
        }

        private NavMeshObstacle NavObstacle
        {
            get
            {
                if (navObstacle == null)
                    navObstacle = GetComponent<NavMeshObstacle>();
                return navObstacle;
            }
        }

        void Awake()
        {
            meshRenderer = GetComponent<MeshRenderer>();
            navObstacle = GetComponent<NavMeshObstacle>();
        }

        void Start()
        {
            SetHazardActive(startActive);
        }

        /// <summary>
        /// 장애물 타일의 활성/비활성 상태를 전환한다.
        /// Phase 4 WebSocket 수신 시 이 메서드를 호출한다.
        /// </summary>
        /// <param name="active">true = 활성(형광색 표시 + 통행 차단), false = 비활성(비표시 + 통행 허용)</param>
        public void SetHazardActive(bool active)
        {
            isActive = active;

            // 1) 시각적 표시
            var mr = MeshRend;
            if (mr != null)
                mr.enabled = active;

            // 2) NavMesh 통행 차단 (carving)
            //    NavMeshObstacle 이 부착돼 있을 때만 동작. 없으면 통행 제어는 생략(하위 호환).
            var obs = NavObstacle;
            if (obs != null)
            {
                obs.enabled = active;
                // carving 이 켜져 있어야 NavMesh 를 실제로 도려낸다(Inspector 에서 Carve 체크 권장).
                obs.carving = active;
            }
        }

        /// <summary>현재 활성 상태를 반환한다.</summary>
        public bool IsActive => isActive;
    }
}
