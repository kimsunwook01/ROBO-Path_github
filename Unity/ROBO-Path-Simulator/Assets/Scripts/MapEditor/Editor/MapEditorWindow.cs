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

            // Ensure new tags are active by default
            foreach (string t in allTags)
            {
                if (!activeTagFilters.Contains(t))
                {
                    activeTagFilters.Add(t);
                }
            }

            // Clean up old tags
            activeTagFilters.RemoveWhere(t => !allTags.Contains(t));
            
            // Sort by name
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
            
            // Tag toggles
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
            
            // Draw grid of buttons
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
                
                // Name label
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

            if (!isSelectMode)
            {
                // Prevent unity's default click-selection in Scene view while in Placement Mode
                int controlID = GUIUtility.GetControlID(FocusType.Passive);
                HandleUtility.AddDefaultControl(controlID);
            }

            Plane plane = new Plane(Vector3.up, Vector3.zero);
            Ray ray = HandleUtility.GUIPointToWorldRay(e.mousePosition);
            
            if (!plane.Raycast(ray, out float enter)) return;

            Vector3 hitPoint = ray.GetPoint(enter);
            float gx = Mathf.Round(hitPoint.x / 10f) * 10f;
            float gz = Mathf.Round(hitPoint.z / 10f) * 10f;

            Transform root = GetOrCreateMapRoot();
            float topY = GetTopYAtGrid(root, gx, gz);

            Vector3 placePos = new Vector3(gx, topY, gz);

            if (!isSelectMode && selectedPrefab != null)
            {
                DrawPreviewHandle(placePos);

                if (e.type == EventType.KeyDown && e.keyCode == KeyCode.R)
                {
                    currentRotationIndex = (currentRotationIndex + 1) % 4;
                    e.Use();
                }

                if (e.type == EventType.MouseDown && e.button == 0 && e.modifiers == EventModifiers.None)
                {
                    HandlePlacement(gx, gz, topY);
                    e.Use();
                }
                else if (e.type == EventType.MouseDown && e.button == 1 && e.modifiers == EventModifiers.None)
                {
                    HandleDeletion(gx, gz);
                    e.Use();
                }
            }
            
            // Force repaint scene to keep preview responsive to mouse move
            sceneView.Repaint();
        }

        private void DrawPreviewHandle(Vector3 placePos)
        {
            Vector3 size = new Vector3(10, 2, 10); // fallback size
            var renderer = selectedPrefab.GetComponentInChildren<Renderer>();
            if (renderer != null) size = renderer.bounds.size;

            Handles.color = new Color(0f, 1f, 0f, 0.4f);
            
            Matrix4x4 oldMatrix = Handles.matrix;
            Handles.matrix = Matrix4x4.TRS(placePos, Quaternion.Euler(0, currentRotationIndex * 90f, 0), Vector3.one);
            Handles.DrawWireCube(new Vector3(0, size.y / 2f, 0), size);
            Handles.matrix = oldMatrix;
        }

        private void HandlePlacement(float gx, float gz, float topY)
        {
            if (selectedPrefab == null) return;

            Transform root = GetOrCreateMapRoot();
            GameObject newBlock = PrefabUtility.InstantiatePrefab(selectedPrefab) as GameObject;
            
            if (newBlock == null) return;

            newBlock.transform.SetParent(root);
            newBlock.transform.position = new Vector3(gx, topY, gz);
            newBlock.transform.rotation = Quaternion.Euler(0, currentRotationIndex * 90f, 0);

            Undo.RegisterCreatedObjectUndo(newBlock, "Place Block");
        }

        private void HandleDeletion(float gx, float gz)
        {
            Transform root = GetOrCreateMapRoot();
            GameObject highestBlock = GetHighestBlockAtGrid(root, gx, gz);

            if (highestBlock != null)
            {
                Undo.DestroyObjectImmediate(highestBlock);
            }
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

        private float GetTopYAtGrid(Transform root, float gx, float gz)
        {
            float topY = 0f;
            foreach (Transform child in root)
            {
                if (Mathf.Approximately(child.position.x, gx) && Mathf.Approximately(child.position.z, gz))
                {
                    float y = GetBlockTopY(child.gameObject);
                    if (y > topY) topY = y;
                }
            }
            return topY;
        }

        private GameObject GetHighestBlockAtGrid(Transform root, float gx, float gz)
        {
            GameObject highest = null;
            float topY = -1f;
            foreach (Transform child in root)
            {
                if (Mathf.Approximately(child.position.x, gx) && Mathf.Approximately(child.position.z, gz))
                {
                    float y = GetBlockTopY(child.gameObject);
                    if (y > topY)
                    {
                        topY = y;
                        highest = child.gameObject;
                    }
                }
            }
            return highest;
        }

        private float GetBlockTopY(GameObject go)
        {
            var renderer = go.GetComponentInChildren<Renderer>();
            if (renderer != null)
            {
                return renderer.bounds.max.y;
            }
            return go.transform.position.y;
        }
    }
}
