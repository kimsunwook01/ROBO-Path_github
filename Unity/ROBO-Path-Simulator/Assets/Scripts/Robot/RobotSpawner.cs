using UnityEngine;
using UnityEngine.AI;

public class RobotSpawner : MonoBehaviour
{
    public GameObject wheeledPrefab;
    public GameObject leggedPrefab;

    void Start()
    {
        SpawnRobots();
    }

    public void SpawnRobots()
    {
        GameObject[] stations = GameObject.FindGameObjectsWithTag("Node_Station");
        if (stations.Length == 0)
        {
            Debug.LogWarning("No Node_Station tags found to spawn robots.");
            return;
        }

        for (int i = 0; i < stations.Length; i++)
        {
            // 교대로 배정 (짝수: Wheeled, 홀수: Legged)
            GameObject prefabToSpawn = (i % 2 == 0) ? wheeledPrefab : leggedPrefab;
            SpawnAt(prefabToSpawn, stations[i].transform.position);
        }
    }

    private void SpawnAt(GameObject prefab, Vector3 position)
    {
        if (prefab == null) return;
        
        // Spawn slightly above to avoid clipping initially
        Vector3 spawnPos = position + Vector3.up * 1f;
        GameObject robot = Instantiate(prefab, spawnPos, Quaternion.identity);
        
        // Ensure it aligns with NavMesh
        NavMeshAgent agent = robot.GetComponent<NavMeshAgent>();
        if (agent != null)
        {
            if (NavMesh.SamplePosition(spawnPos, out NavMeshHit hit, 5.0f, NavMesh.AllAreas))
            {
                agent.Warp(hit.position);
            }
        }
    }
}
