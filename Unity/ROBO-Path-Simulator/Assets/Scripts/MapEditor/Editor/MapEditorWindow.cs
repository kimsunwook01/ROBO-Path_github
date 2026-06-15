using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace ROBOPath.MapEditor
{
    public class MapEditorWindow : EditorWindow
    {
        private List<GameObject> loadedPrefabs = new List<GameObject>();
        private GameObject selectedPrefab;
        private int currentRotationIndex = 0;
        private bool isSelectMode = false;
        
        private HashSet<string> allTags = new HashSet<string>();
        private HashSet<string> activeTagFilters = new HashSet<string>();
        private Vector2 scrollPos;

        [MenuItem("ROBO-Path/Map Editor")]
        public static void ShowWindow()
        {
            var window = GetWindow<MapEditorWindow>("Map Editor");
            window.Show();
        }

        private void OnEnable()
        {
            RefreshPrefabs();
            SceneView.duringSceneGui += OnSceneGUI;
        }

        private void OnDisable()
        {
            SceneView.duringSceneGui -= OnSceneGUI;
        }

        private void RefreshPrefabs()
        {
            loadedPrefabs.Clear();
            allTags.Clear();

            string[] guids = AssetDatabase.FindAssets("t:Prefab", new[] { "Assets/Prefabs" });
            foreach (string guid in guids)
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if (prefab != null)
                {
                    loadedPrefabs.Add(prefab);
                    allTags.Add(prefab.tag);
                }
            }

            foreach (string t in allTags)
            {
                if (!activeTagFilters.Contains(t))
                {
                    activeTagFilters.Add(t);
                }
            }

            activeTagFilters.RemoveWhere(t => !allTags.Contains(t));
            loadedPrefabs.Sort((a, b) => a.name.CompareTo(b.name));
            Repaint();
        }

        private void OnGUI()
        {
            GUILayout.Label("Mode", EditorStyles.boldLabel);
            isSelectMode = GUILayout.Toolbar(isSelectMode ? 1 : 0, new[] { "Placement Mode", "Selection Mode" }) == 1;

            EditorGUILayout.Space();

            if (GUILayout.Button("Refresh Prefabs", GUILayout.Height(30)))
            {
                RefreshPrefabs();
            }

            EditorGUILayout.Space();
            GUILayout.Label("Tag Filters", EditorStyles.boldLabel);
            
            GUILayout.BeginHorizontal();
            List<string> sortedTags = allTags.ToList();
            sortedTags.Sort();
            foreach (string t in sortedTags)
            {
                bool current = activeTagFilters.Contains(t);
                bool changed = GUILayout.Toggle(current, t);
                if (changed && !current) activeTagFilters.Add(t);
                else if (!changed && current) activeTagFilters.Remove(t);
            }
            GUILayout.EndHorizontal();

            EditorGUILayout.Space();
            GUILayout.Label("Prefabs Palette", EditorStyles.boldLabel);

            scrollPos = GUILayout.BeginScrollView(scrollPos);
            
            int columns = Mathf.Max(1, (int)(position.width / 110f));
            int colIndex = 0;
            
            GUILayout.BeginHorizontal();
            foreach (var prefab in loadedPrefabs)
            {
                if (!activeTagFilters.Contains(prefab.tag)) continue;

                if (colIndex >= columns)
                {
                    GUILayout.EndHorizontal();
                    GUILayout.BeginHorizontal();
                    colIndex = 0;
                }

                GUIStyle style = new GUIStyle(GUI.skin.button);
                if (selectedPrefab == prefab)
                {
                    style.normal.textColor = Color.green;
                    style.fontStyle = FontStyle.Bold;
                }

                GUILayout.BeginVertical(GUILayout.Width(100), GUILayout.Height(120));
                
                Texture2D preview = AssetPreview.GetAssetPreview(prefab);
                if (preview != null)
                {
                    if (GUILayout.Button(preview, GUILayout.Width(100), GUILayout.Height(100)))
                    {
                        selectedPrefab = prefab;
                    }
                }
                else
                {
                    if (GUILayout.Button(prefab.name, GUILayout.Width(100), GUILayout.Height(100)))
                    {
                        selectedPrefab = prefab;
                    }
                }
                
                GUILayout.Label(prefab.name, style, GUILayout.MaxWidth(100));
                GUILayout.EndVertical();
                
                colIndex++;
            }
            GUILayout.EndHorizontal();
            
            GUILayout.EndScrollView();
        }

        private void OnSceneGUI(SceneView sceneView)
        {
            Event e = Event.current;

            if (e.type == EventType.KeyDown && e.keyCode == KeyCode.Escape)
            {
                selectedPrefab = null;
                e.Use();
                sceneView.Repaint();
            }

            if (isSelectMode)
            {
                if (e.type == EventType.KeyDown)
                {
                    if (e.keyCode == KeyCode.Delete || e.keyCode == KeyCode.Backspace)
                    {
                        if (Selection.activeGameObject != null && Selection.activeGameObject.transform.IsChildOf(GetOrCreateMapRoot()))
                        {
                            Undo.DestroyObjectImmediate(Selection.activeGameObject);
                            e.Use();
                        }
                    }
                    else if (e.keyCode == KeyCode.R)
                    {
                        if (Selection.activeGameObject != null && Selection.activeGameObject.transform.IsChildOf(GetOrCreateMapRoot()))
                        {
                            Undo.RecordObject(Selection.activeGameObject.transform, "Rotate Block");
                            Selection.activeGameObject.transform.Rotate(0, 90f, 0, Space.World);
                            e.Use();
                        }
                    }
                }
                return; // Let Unity handle selection and camera logic
            }

            // Placement Mode
            if (selectedPrefab == null) return;

            // Prevent unity's default click-selection in Scene view while in Placement Mode
            int controlID = GUIUtility.GetControlID(FocusType.Passive);
            HandleUtility.AddDefaultControl(controlID);

            Ray ray = HandleUtility.GUIPointToWorldRay(e.mousePosition);
            bool foundCell = false;
            float cellX = 0, cellZ = 0;
            float baseY = 0f;
            float blockHeight = GetPreviewSize(selectedPrefab).y;

            if (Physics.Raycast(ray, out RaycastHit hit) && hit.collider.transform.IsChildOf(GetOrCreateMapRoot()))
            {
                GameObject hitObj = hit.collider.gameObject;
                Renderer hitRenderer = hitObj.GetComponentInChildren<Renderer>();
                
                float hitMaxY = hitRenderer != null ? hitRenderer.bounds.max.y : hitObj.transform.position.y + GetPrefabHeight(hitObj) / 2f;
                float hitMinY = hitRenderer != null ? hitRenderer.bounds.min.y : hitObj.transform.position.y - GetPrefabHeight(hitObj) / 2f;
                
                Vector3 hitPointCell = hitObj.transform.position;

                if (hit.normal.y > 0.5f)
                {
                    // Top face
                    cellX = Mathf.Floor(hitPointCell.x / 10f);
                    cellZ = Mathf.Floor(hitPointCell.z / 10f);
                    baseY = hitMaxY;
                }
                else if (hit.normal.y < -0.5f)
                {
                    // Bottom face
                    cellX = Mathf.Floor(hitPointCell.x / 10f);
                    cellZ = Mathf.Floor(hitPointCell.z / 10f);
                    baseY = hitMinY - blockHeight;
                }
                else
                {
                    // Side face
                    cellX = Mathf.Floor(hitPointCell.x / 10f) + Mathf.Round(hit.normal.x);
                    cellZ = Mathf.Floor(hitPointCell.z / 10f) + Mathf.Round(hit.normal.z);
                    baseY = hitMinY;
                }
                foundCell = true;
            }
            else
            {
                Plane plane = new Plane(Vector3.up, Vector3.zero);
                if (plane.Raycast(ray, out float enter))
                {
                    Vector3 hitPoint = ray.GetPoint(enter);
                    cellX = Mathf.Floor(hitPoint.x / 10f);
                    cellZ = Mathf.Floor(hitPoint.z / 10f);
                    baseY = 0f;
                    foundCell = true;
                }
            }

            if (!foundCell) return;

            float centerX = cellX * 10f + 5f;
            float centerZ = cellZ * 10f + 5f;
            Vector3 placePos = new Vector3(centerX, baseY + blockHeight / 2f, centerZ);

            DrawPreviewHandle(placePos);

            if (e.type == EventType.KeyDown && e.keyCode == KeyCode.R)
            {
                currentRotationIndex = (currentRotationIndex + 1) % 4;
                e.Use();
            }

            if (e.type == EventType.MouseDown && e.button == 0 && e.modifiers == EventModifiers.None)
            {
                HandlePlacement(placePos);
                e.Use();
            }

            sceneView.Repaint();
        }

        private void DrawPreviewHandle(Vector3 placePos)
        {
            Vector3 size = GetPreviewSize(selectedPrefab);
            Handles.color = new Color(0f, 1f, 0f, 0.4f);
            
            Matrix4x4 oldMatrix = Handles.matrix;
            Handles.matrix = Matrix4x4.TRS(placePos, Quaternion.Euler(0, currentRotationIndex * 90f, 0), Vector3.one);
            Handles.DrawWireCube(Vector3.zero, size);
            Handles.matrix = oldMatrix;
        }

        private void HandlePlacement(Vector3 placePos)
        {
            if (selectedPrefab == null) return;

            Transform root = GetOrCreateMapRoot();
            GameObject newBlock = PrefabUtility.InstantiatePrefab(selectedPrefab) as GameObject;
            if (newBlock == null) return;

            newBlock.transform.SetParent(root);
            newBlock.transform.position = placePos;
            newBlock.transform.rotation = Quaternion.Euler(0, currentRotationIndex * 90f, 0);

            Undo.RegisterCreatedObjectUndo(newBlock, "Place Block");
        }

        private Transform GetOrCreateMapRoot()
        {
            GameObject root = GameObject.Find("MapRoot");
            if (root == null)
            {
                root = new GameObject("MapRoot");
            }
            return root.transform;
        }

        private Vector3 GetPreviewSize(GameObject prefab)
        {
            var renderer = prefab.GetComponentInChildren<Renderer>();
            if (renderer != null && renderer.bounds.size.sqrMagnitude > 0.01f)
            {
                return renderer.bounds.size;
            }
            return new Vector3(10f, GetPrefabHeight(prefab), 10f);
        }

        private float GetPrefabHeight(GameObject prefab)
        {
            string[] parts = prefab.name.Split('_');
            if (parts.Length > 0 && float.TryParse(parts[parts.Length - 1], out float h))
            {
                return h;
            }
            return 2f; // Fallback
        }
    }
}
