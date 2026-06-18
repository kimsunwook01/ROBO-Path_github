using UnityEngine;
using UnityEditor;
using Unity.AI.Navigation;
using UnityEngine.AI;
using System.IO;

namespace ROBOPath.EditorTools
{
    /// <summary>
    /// 지형 프리팹에 NavMeshModifier 를 자동 부착하여, NavMesh 베이크 시
    /// 특정 지형을 별도 Area 로 표시하게 한다.
    ///
    /// 배경 — NavMesh 와 A* 는 별개의 두 경로 시스템이다:
    /// - A* 는 cost_profiles 로 계단 차단/도로 회피를 계산한다.
    /// - 하지만 NavMeshAgent 는 자기 NavMesh 위에서 독자적으로 경로를 짠다.
    ///   웨이포인트 사이를 NavMesh 가 자체 계산하므로, A* 의도가 무시될 수 있다.
    /// - NavMesh 가 A* 와 합의하게 하려면, NavMesh Area 의 비용 구조를
    ///   A* 의 cost_multiplier 와 일치시켜야 한다.
    ///
    /// Area 처리 (모두 프리팹에 NavMeshModifier 부착 → 재베이크):
    /// 1) Stair Area — 휠 로봇은 areaMask 에서 완전 제외(통행 불가). 보행은 사용.
    /// 2) Road Area — 휠 로봇은 areaMask 에서 제외(연석: 도로 면 진입 불가).
    ///    횡단보도 타일은 도로 위 0.5m 에 얹힌 블록이라 NavMesh 가 그 윗면을
    ///    별도 주행면(Road Area 아님)으로 굽는다 → 휠 로봇도 횡단보도로는 건넌다.
    ///    보행 로봇은 Road 비용만 높여(3) 감수 가능하게 둔다.
    /// 3) Ramp Area — 경사를 평지와 구분해 NavMesh 가 인식하게만 한다(비용 1, 통행 영향 없음).
    ///    향후 경사 관련 제어가 필요할 때 에디터 작업 없이 코드로 대응하기 위한 사전 분리.
    /// 4) Hazard Area — 장애물 타일. 활성/비활성에 따라 HazardTileController 가
    ///    코드로 NavMesh 비용을 조절해 통행을 막거나 연다(에디터 재작업 불필요).
    ///
    /// 사용 순서:
    /// 1. [선행] Window > AI > Navigation 의 Areas 탭에서 'Stair','Road','Ramp','Hazard' Area 추가.
    /// 2. ROBO-Path > Setup All NavMesh Areas  (네 종류 프리팹 일괄 처리)
    /// 3. NavMeshSurface 에서 Bake 재실행.
    /// 4. 플레이 테스트.
    ///
    /// 주의: ROBOPath.Debug 네임스페이스 충돌(CS0234) 때문에 UnityEngine.Debug 를 명시.
    /// </summary>
    public static class StairNavMeshSetup
    {
        private const string STAIR_AREA_NAME = "Stair";
        private const string ROAD_AREA_NAME = "Road";
        private const string RAMP_AREA_NAME = "Ramp";
        private const string HAZARD_AREA_NAME = "Hazard";
        private const string PrefabFolder = "Assets/Prefabs";

        private static readonly string[] StairPrefabNames =
            { "Stair_2", "Stair_4", "Stair_6", "Stair_8", "Stair_10" };

        // 도로 계열 — A* 에서 cost_multiplier 20(휠) 으로 회피하는 지형.
        // Road_Vehicle_Ramp 도 차도이면서 경사라 동일하게 Road Area 로 묶는다.
        private static readonly string[] RoadPrefabNames =
        {
            "Road_Vehicle_2", "Road_Vehicle_4", "Road_Vehicle_6", "Road_Vehicle_8", "Road_Vehicle_10",
            "Road_Vehicle_Ramp_2", "Road_Vehicle_Ramp_4", "Road_Vehicle_Ramp_6", "Road_Vehicle_Ramp_8", "Road_Vehicle_Ramp_10"
        };

        // 경사로 — 평지와 구분 인식용 (Road_Vehicle_Ramp 는 Road 로 분류되므로 여기선 일반 Ramp 만)
        private static readonly string[] RampPrefabNames =
            { "Ramp_2", "Ramp_4", "Ramp_6", "Ramp_8", "Ramp_10" };

        // 장애물 타일 — 단일 프리팹
        private static readonly string[] HazardPrefabNames =
            { "Tile_Hazard" };

        [MenuItem("ROBO-Path/Setup All NavMesh Areas")]
        public static void SetupAllAreas()
        {
            ApplyAreaToPrefabs(STAIR_AREA_NAME, StairPrefabNames, "계단", silent: true);
            ApplyAreaToPrefabs(ROAD_AREA_NAME, RoadPrefabNames, "도로", silent: true);
            ApplyAreaToPrefabs(RAMP_AREA_NAME, RampPrefabNames, "경사", silent: true);
            ApplyAreaToPrefabs(HAZARD_AREA_NAME, HazardPrefabNames, "장애물", silent: true);
            EditorUtility.DisplayDialog(
                "완료",
                "계단/도로/경사/장애물 프리팹에 NavMeshModifier 부착 완료.\n" +
                "각 Area 가 등록돼 있어야 적용됩니다(로그에서 'Area 없음' 경고 확인).\n\n" +
                "이제 NavMeshSurface 에서 Bake 를 다시 눌러 재베이크하세요.",
                "확인");
        }

        [MenuItem("ROBO-Path/Setup Stair NavMesh Area")]
        public static void SetupStairArea()
        {
            ApplyAreaToPrefabs(STAIR_AREA_NAME, StairPrefabNames, "계단");
        }

        [MenuItem("ROBO-Path/Setup Road NavMesh Area")]
        public static void SetupRoadArea()
        {
            ApplyAreaToPrefabs(ROAD_AREA_NAME, RoadPrefabNames, "도로");
        }

        [MenuItem("ROBO-Path/Setup Ramp NavMesh Area")]
        public static void SetupRampArea()
        {
            ApplyAreaToPrefabs(RAMP_AREA_NAME, RampPrefabNames, "경사");
        }

        [MenuItem("ROBO-Path/Setup Hazard NavMesh Area")]
        public static void SetupHazardArea()
        {
            ApplyAreaToPrefabs(HAZARD_AREA_NAME, HazardPrefabNames, "장애물");
        }

        /// <summary>
        /// 지정한 프리팹들에 NavMeshModifier(overrideArea, area=areaName)를 부착한다.
        /// silent=true 면 개별 완료 다이얼로그를 띄우지 않는다(일괄 처리용).
        /// </summary>
        private static void ApplyAreaToPrefabs(string areaName, string[] prefabNames, string label, bool silent = false)
        {
            int areaIndex = GetAreaIndexByName(areaName);
            if (areaIndex < 0)
            {
                if (!silent)
                {
                    EditorUtility.DisplayDialog(
                        $"{areaName} Area 없음",
                        $"NavMesh Area '{areaName}' 를 찾을 수 없습니다.\n\n" +
                        $"먼저 Window > AI > Navigation 의 Areas 탭에서 '{areaName}' Area 를 추가한 뒤 다시 실행하세요.",
                        "확인");
                }
                else
                {
                    UnityEngine.Debug.LogWarning($"[NavMeshSetup] '{areaName}' Area 없음 — {label} 건너뜀. Areas 탭에서 추가 필요.");
                }
                return;
            }

            UnityEngine.Debug.Log($"[NavMeshSetup] '{areaName}' Area 인덱스 = {areaIndex}");

            int processed = 0;
            int skipped = 0;

            foreach (var prefabName in prefabNames)
            {
                string path = $"{PrefabFolder}/{prefabName}.prefab";
                if (!File.Exists(path))
                {
                    UnityEngine.Debug.LogWarning($"[NavMeshSetup] 프리팹 없음: {path} — 건너뜀");
                    skipped++;
                    continue;
                }

                GameObject prefabRoot = PrefabUtility.LoadPrefabContents(path);
                if (prefabRoot == null)
                {
                    UnityEngine.Debug.LogWarning($"[NavMeshSetup] 프리팹 로드 실패: {path}");
                    skipped++;
                    continue;
                }

                NavMeshModifier modifier = prefabRoot.GetComponent<NavMeshModifier>();
                if (modifier == null)
                {
                    modifier = prefabRoot.AddComponent<NavMeshModifier>();
                    UnityEngine.Debug.Log($"[NavMeshSetup] {prefabName}: NavMeshModifier 추가 (area={areaName})");
                }
                else
                {
                    UnityEngine.Debug.Log($"[NavMeshSetup] {prefabName}: 기존 NavMeshModifier 갱신 (area={areaName})");
                }

                modifier.overrideArea = true;
                modifier.area = areaIndex;
                modifier.applyToChildren = true;

                PrefabUtility.SaveAsPrefabAsset(prefabRoot, path);
                PrefabUtility.UnloadPrefabContents(prefabRoot);
                processed++;
            }

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();

            if (!silent)
            {
                EditorUtility.DisplayDialog(
                    "완료",
                    $"{label} 프리팹 {processed}개에 NavMeshModifier(area={areaName}) 부착 완료.\n" +
                    (skipped > 0 ? $"({skipped}개 건너뜀)\n\n" : "\n") +
                    "이제 씬의 NavMeshSurface 에서 Bake 를 다시 눌러 재베이크하세요.",
                    "확인");
            }

            UnityEngine.Debug.Log($"[NavMeshSetup] {label} 완료: {processed}개 처리, {skipped}개 건너뜀. 재베이크 필요.");
        }

        private static int GetAreaIndexByName(string areaName)
        {
            string[] areaNames = NavMesh.GetAreaNames();
            for (int i = 0; i < areaNames.Length; i++)
            {
                if (areaNames[i] == areaName)
                    return NavMesh.GetAreaFromName(areaName);
            }
            return -1;
        }

        [MenuItem("ROBO-Path/Print NavMesh Areas")]
        public static void PrintNavMeshAreas()
        {
            string[] areaNames = NavMesh.GetAreaNames();
            UnityEngine.Debug.Log("=== 현재 등록된 NavMesh Areas ===");
            foreach (var name in areaNames)
            {
                int idx = NavMesh.GetAreaFromName(name);
                UnityEngine.Debug.Log($"  Area '{name}' -> 인덱스 {idx}");
            }
        }
    }
}
