using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace ROBOPath.Debug.Editor
{
    public class SceneDumpExporter : EditorWindow
    {
        private const float Tolerance = 0.1f;

        [MenuItem("ROBO-Path/Export Scene Dump")]
        public static void ExportSceneDump()
        {
            Scene scene = SceneManager.GetActiveScene();
            
            // All tags to collect
            string[] nodeTags = { "Node_Station", "Node_Pickup", "Node_Destination", "Waypoint" };
            string[] tileTags = { "Terrain_Flat", "Terrain_Slope", "Path_Stair", "Path_Ramp", "Path_Tunnel", "Road_Sidewalk", "Road_Vehicle", "Road_Crosswalk" };
            string[] obstacleTags = { "Building", "Obstacle", "Prop_Pole", "Prop_Tree" };

            var dump = new SceneDumpData();

            // Collect all GameObjects
            GameObject[] rootObjects = scene.GetRootGameObjects();
            List<GameObject> allObjects = new List<GameObject>();
            foreach (var root in rootObjects)
            {
                allObjects.AddRange(root.GetComponentsInChildren<Transform>(true).Select(t => t.gameObject));
            }

            List<TileData> tiles = new List<TileData>();

            float minElevation = float.MaxValue;
            float maxElevation = float.MinValue;

            List<string> suspectedMissingTags = new List<string>();
            var allValidTags = nodeTags.Concat(tileTags).Concat(obstacleTags).ToList();

            foreach (var go in allObjects)
            {
                if (!go.activeInHierarchy) continue;

                if (go.GetComponent<MeshRenderer>() != null)
                {
                    if (go.tag == "Untagged" || !allValidTags.Contains(go.tag))
                    {
                        suspectedMissingTags.Add(go.name);
                    }
                }

                if (nodeTags.Contains(go.tag))
                {
                    dump.nodes.Add(ProcessNode(go));
                }
                else if (tileTags.Contains(go.tag))
                {
                    var tile = ProcessTile(go);
                    dump.tiles.Add(tile);
                    tiles.Add(tile);

                    if (tile.elevation < minElevation) minElevation = tile.elevation;
                    if (tile.elevation > maxElevation) maxElevation = tile.elevation;
                }
                else if (obstacleTags.Contains(go.tag))
                {
                    dump.obstacles.Add(ProcessObstacle(go));
                }
            }

            // Adjacency for tiles
            for (int i = 0; i < tiles.Count; i++)
            {
                var adj = new AdjacencyData { tile = tiles[i].name };
                for (int j = 0; j < tiles.Count; j++)
                {
                    if (i == j) continue;
                    if (AreAdjacent(tiles[i].go, tiles[j].go, Tolerance))
                    {
                        adj.adjacent_to.Add(tiles[j].name);
                    }
                }
                if (adj.adjacent_to.Count > 0)
                {
                    dump.adjacency.Add(adj);
                }
            }

            // Summary
            Bounds mapBounds = CalculateMapBounds(tiles.Select(t => t.go).ToList());
            
            if (minElevation == float.MaxValue) minElevation = 0;
            if (maxElevation == float.MinValue) maxElevation = 0;

            dump.summary = new SummaryData
            {
                total_nodes = dump.nodes.Count,
                total_tiles = dump.tiles.Count,
                total_obstacles = dump.obstacles.Count,
                min_elevation = minElevation,
                max_elevation = maxElevation,
                map_size = new Vector3Data(mapBounds.size)
            };

            // Serialization
            string json = JsonUtility.ToJson(dump, true);

            // Path: We want ProjectRoot/scene_snapshots/scene_dump.json -> Unity/ROBO-Path-Simulator/scene_snapshots/scene_dump.json
            // Application.dataPath is Unity/ROBO-Path-Simulator/Assets, so we use ../scene_snapshots
            string targetDir = Path.GetFullPath(Path.Combine(Application.dataPath, "../scene_snapshots"));
            if (!Directory.Exists(targetDir))
            {
                Directory.CreateDirectory(targetDir);
            }

            string filePath = Path.Combine(targetDir, "scene_dump.json");
            File.WriteAllText(filePath, json);

            if (suspectedMissingTags.Count > 0)
            {
                UnityEngine.Debug.LogWarning($"[SceneDump] 태그 누락 의심 오브젝트 {suspectedMissingTags.Count}개: {string.Join(", ", suspectedMissingTags)}");
            }
            else
            {
                UnityEngine.Debug.Log("[SceneDump] 태그 누락 의심 오브젝트 없음");
            }

            UnityEngine.Debug.Log($"[ROBO-Path] Scene Dump Exported to: {filePath}\nNodes: {dump.nodes.Count}, Tiles: {dump.tiles.Count}, Obstacles: {dump.obstacles.Count}");
        }

        private static Bounds GetBounds(GameObject go)
        {
            var renderer = go.GetComponent<Renderer>();
            if (renderer != null) return renderer.bounds;

            var collider = go.GetComponent<Collider>();
            if (collider != null) return collider.bounds;

            // Fallback
            return new Bounds(go.transform.position, Vector3.zero);
        }

        private static NodeData ProcessNode(GameObject go)
        {
            var data = new NodeData
            {
                name = go.name,
                tag = go.tag,
                position = new Vector3Data(go.transform.position),
                rotation_y = go.transform.rotation.eulerAngles.y,
                size = new Vector3Data(GetBounds(go).size)
            };

            if (go.tag == "Node_Station") data.usage = "station";
            else if (go.tag == "Node_Pickup") data.usage = "pickup";
            else if (go.tag == "Node_Destination") data.usage = "destination";
            else data.usage = null; // Waypoint -> null

            return data;
        }

        private static TileData ProcessTile(GameObject go)
        {
            var bounds = GetBounds(go);
            return new TileData
            {
                go = go,
                name = go.name,
                tag = go.tag,
                position = new Vector3Data(go.transform.position),
                rotation_y = go.transform.rotation.eulerAngles.y,
                size = new Vector3Data(bounds.size),
                terrain_type = go.tag,
                elevation = bounds.max.y
            };
        }

        private static ObstacleData ProcessObstacle(GameObject go)
        {
            return new ObstacleData
            {
                name = go.name,
                tag = go.tag,
                position = new Vector3Data(go.transform.position),
                rotation_y = go.transform.rotation.eulerAngles.y,
                size = new Vector3Data(GetBounds(go).size)
            };
        }

        private static bool AreAdjacent(GameObject a, GameObject b, float tolerance)
        {
            Bounds boundsA = GetBounds(a);
            Bounds boundsB = GetBounds(b);

            // X axis
            float aMinX = boundsA.min.x;
            float aMaxX = boundsA.max.x;
            float bMinX = boundsB.min.x;
            float bMaxX = boundsB.max.x;

            // Z axis
            float aMinZ = boundsA.min.z;
            float aMaxZ = boundsA.max.z;
            float bMinZ = boundsB.min.z;
            float bMaxZ = boundsB.max.z;

            // Calculate distance between bounds on each axis
            float distX = Math.Max(0, Math.Max(aMinX - bMaxX, bMinX - aMaxX));
            float distZ = Math.Max(0, Math.Max(aMinZ - bMaxZ, bMinZ - aMaxZ));

            // Calculate overlap length on each axis
            float overlapX = Math.Min(aMaxX, bMaxX) - Math.Max(aMinX, bMinX);
            float overlapZ = Math.Min(aMaxZ, bMaxZ) - Math.Max(aMinZ, bMinZ);

            bool isTouchingX = distX <= tolerance;
            bool isTouchingZ = distZ <= tolerance;

            // Must overlap by more than tolerance to exclude mere vertex (corner) touching
            bool overlapsX = overlapX > tolerance;
            bool overlapsZ = overlapZ > tolerance;

            // 4-way adjacency: must touch on one axis and overlap on the other
            if (isTouchingX && overlapsZ) return true;
            if (isTouchingZ && overlapsX) return true;

            return false;
        }

        private static Bounds CalculateMapBounds(List<GameObject> tiles)
        {
            if (tiles.Count == 0) return new Bounds(Vector3.zero, Vector3.zero);

            Bounds b = GetBounds(tiles[0]);
            for (int i = 1; i < tiles.Count; i++)
            {
                b.Encapsulate(GetBounds(tiles[i]));
            }
            return b;
        }

        // --- Serializable Data Structures ---

        [Serializable]
        public class SceneDumpData
        {
            public SummaryData summary = new SummaryData();
            public List<NodeData> nodes = new List<NodeData>();
            public List<TileData> tiles = new List<TileData>();
            public List<ObstacleData> obstacles = new List<ObstacleData>();
            public List<AdjacencyData> adjacency = new List<AdjacencyData>();
        }

        [Serializable]
        public class SummaryData
        {
            public int total_nodes;
            public int total_tiles;
            public int total_obstacles;
            public float min_elevation;
            public float max_elevation;
            public Vector3Data map_size;
        }

        [Serializable]
        public class ObjectData
        {
            public string name;
            public string tag;
            public Vector3Data position;
            public float rotation_y;
            public Vector3Data size;
        }

        [Serializable]
        public class NodeData : ObjectData
        {
            public string usage;
        }

        [Serializable]
        public class TileData : ObjectData
        {
            [NonSerialized] public GameObject go;
            public string terrain_type;
            public float elevation;
        }

        [Serializable]
        public class ObstacleData : ObjectData { }

        [Serializable]
        public class AdjacencyData
        {
            public string tile;
            public List<string> adjacent_to = new List<string>();
        }

        [Serializable]
        public struct Vector3Data
        {
            public float x, y, z;
            public Vector3Data(Vector3 v) { x = v.x; y = v.y; z = v.z; }
        }
    }
}
