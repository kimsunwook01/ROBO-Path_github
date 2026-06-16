#if UNITY_EDITOR
using UnityEngine;
using UnityEditor;
using UnityEngine.AI;
using UnityEditor.SceneManagement;

public class Phase3aSetup
{
    [MenuItem("ROBO-Path/Run Phase 3a Setup")]
    public static void RunSetup()
    {
        AddLayer("Robot");
        AddNavMeshArea("Road", 1);
        AddNavMeshArea("Stair", 1);
        
        SetupPrefab("Assets/Prefabs/Robot/Robot_Wheeled.prefab", RobotPlatform.Wheeled);
        SetupPrefab("Assets/Prefabs/Robot/Robot_Legged.prefab", RobotPlatform.Legged);
        
        RebakeMainScene();
        
        Debug.Log("Phase 3a Setup Completed!");
    }

    private static void AddLayer(string layerName)
    {
        SerializedObject tagManager = new SerializedObject(AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/TagManager.asset")[0]);
        SerializedProperty layers = tagManager.FindProperty("layers");
        
        bool found = false;
        for (int i = 8; i < layers.arraySize; i++)
        {
            SerializedProperty sp = layers.GetArrayElementAtIndex(i);
            if (sp.stringValue == layerName)
            {
                found = true;
                break;
            }
        }

        if (!found)
        {
            for (int i = 8; i < layers.arraySize; i++)
            {
                SerializedProperty sp = layers.GetArrayElementAtIndex(i);
                if (string.IsNullOrEmpty(sp.stringValue))
                {
                    sp.stringValue = layerName;
                    tagManager.ApplyModifiedProperties();
                    Debug.Log($"Layer '{layerName}' added at index {i}");
                    break;
                }
            }
        }
    }

    private static void AddNavMeshArea(string areaName, int cost)
    {
        // For Unity, NavMesh areas are stored in NavMeshAreas.asset or NavMeshProjectSettings
        SerializedObject navMeshSettings = new SerializedObject(AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/NavMeshAreas.asset")[0]);
        SerializedProperty areas = navMeshSettings.FindProperty("areas");

        bool found = false;
        int emptyIndex = -1;

        for (int i = 3; i < areas.arraySize; i++) // 0,1,2 are built-in
        {
            SerializedProperty area = areas.GetArrayElementAtIndex(i);
            SerializedProperty nameProp = area.FindPropertyRelative("name");
            if (nameProp.stringValue == areaName)
            {
                found = true;
                break;
            }
            if (emptyIndex == -1 && string.IsNullOrEmpty(nameProp.stringValue))
            {
                emptyIndex = i;
            }
        }

        if (!found && emptyIndex != -1)
        {
            SerializedProperty area = areas.GetArrayElementAtIndex(emptyIndex);
            area.FindPropertyRelative("name").stringValue = areaName;
            area.FindPropertyRelative("cost").floatValue = cost;
            navMeshSettings.ApplyModifiedProperties();
            Debug.Log($"NavMesh Area '{areaName}' added.");
        }
    }

    private static void SetupPrefab(string path, RobotPlatform platform)
    {
        GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
        if (prefab == null) return;

        GameObject instance = (GameObject)PrefabUtility.InstantiatePrefab(prefab);

        // 1. RobotIdentify
        RobotIdentify identify = instance.GetComponent<RobotIdentify>();
        if (identify == null) identify = instance.AddComponent<RobotIdentify>();
        identify.platform = platform;

        // 2. Rigidbody
        Rigidbody rb = instance.GetComponent<Rigidbody>();
        if (rb == null) rb = instance.AddComponent<Rigidbody>();
        rb.isKinematic = true;
        rb.useGravity = false;

        // 3. Collider
        // Remove child colliders
        Collider[] colliders = instance.GetComponentsInChildren<Collider>(true);
        foreach (var c in colliders)
        {
            Object.DestroyImmediate(c);
        }

        BoxCollider box = instance.GetComponent<BoxCollider>();
        if (box == null) box = instance.AddComponent<BoxCollider>();
        box.center = new Vector3(0, 3, 0);
        box.size = new Vector3(5, 5, 8);

        // 4. NavMeshAgent
        NavMeshAgent agent = instance.GetComponent<NavMeshAgent>();
        if (agent == null) agent = instance.AddComponent<NavMeshAgent>();
        agent.radius = 2.5f;
        agent.height = 5.5f;
        agent.baseOffset = 0f;

        if (platform == RobotPlatform.Wheeled)
        {
            agent.speed = 3.5f;
            agent.acceleration = 8f;
            agent.angularSpeed = 120f;
            agent.areaMask = (1 << NavMesh.GetAreaFromName("Walkable")) | (1 << NavMesh.GetAreaFromName("Road"));
        }
        else
        {
            agent.speed = 2.5f;
            agent.acceleration = 5f;
            agent.angularSpeed = 120f;
            agent.areaMask = NavMesh.AllAreas;
        }

        // 5. Layer
        int robotLayer = LayerMask.NameToLayer("Robot");
        if (robotLayer != -1)
        {
            SetLayerRecursively(instance, robotLayer);
        }

        PrefabUtility.SaveAsPrefabAsset(instance, path);
        Object.DestroyImmediate(instance);
        Debug.Log($"Setup completed for {path}");
    }

    private static void SetLayerRecursively(GameObject obj, int layer)
    {
        obj.layer = layer;
        foreach (Transform child in obj.transform)
        {
            SetLayerRecursively(child.gameObject, layer);
        }
    }

    private static void RebakeMainScene()
    {
        string scenePath = "Assets/Scenes/CampusMainMap/CampusMainMap.unity";
        var scene = EditorSceneManager.OpenScene(scenePath, OpenSceneMode.Single);
        
        // Modify default NavMesh build settings if possible, 
        // or just rely on NavMeshSurface if the project uses it.
        // Assuming Unity's built-in NavMeshBuilder or NavMeshSurface.
        
        // If there's a Unity.AI.Navigation.NavMeshSurface in the scene:
        // Wait, standard AI package or NavMeshSurface?
        // We will just invoke UnityEditor.AI.NavMeshBuilder.BuildNavMesh() 
        // but we need to set the agent radius first.
        SerializedObject navMeshSettings = new SerializedObject(AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/NavMeshAreas.asset")[0]); // NavMeshProjectSettings in newer unity
        SerializedProperty settings = navMeshSettings.FindProperty("m_Settings");
        if (settings != null && settings.arraySize > 0)
        {
            SerializedProperty s = settings.GetArrayElementAtIndex(0);
            s.FindPropertyRelative("agentRadius").floatValue = 2.5f;
            navMeshSettings.ApplyModifiedProperties();
        }

        UnityEditor.AI.NavMeshBuilder.BuildNavMesh();
        EditorSceneManager.SaveScene(scene);
        Debug.Log("NavMesh rebaked with 2.5m radius.");
    }
}
#endif
