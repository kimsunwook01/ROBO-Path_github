using UnityEngine;
using UnityEditor;
using ROBOPath.Robot;

public static class Phase3PrefabPatcher
{
    [MenuItem("ROBO-Path/Patch Phase 3 Prefabs")]
    public static void PatchPrefabs()
    {
        string[] paths = new string[] 
        {
            "Assets/Prefabs/Robot/Robot_Wheeled.prefab",
            "Assets/Prefabs/Robot/Robot_Legged.prefab"
        };

        foreach (string path in paths)
        {
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (prefab == null) continue;

            // Remove old ClickToMove if it exists
            // Since we deleted the script, it will be a "Missing Script".
            // Unity provides GameObjectUtility.RemoveMonoBehavioursWithMissingScript
            GameObjectUtility.RemoveMonoBehavioursWithMissingScript(prefab);

            // Add new components
            if (prefab.GetComponent<LogTelemetrySink>() == null)
            {
                prefab.AddComponent<LogTelemetrySink>();
            }
            if (prefab.GetComponent<RobotController>() == null)
            {
                prefab.AddComponent<RobotController>();
            }
            if (prefab.GetComponent<RaycastScanner>() == null)
            {
                prefab.AddComponent<RaycastScanner>();
            }

            PrefabUtility.SavePrefabAsset(prefab);
            Debug.Log($"[Phase3PrefabPatcher] Successfully patched {path}");
        }
    }
}
