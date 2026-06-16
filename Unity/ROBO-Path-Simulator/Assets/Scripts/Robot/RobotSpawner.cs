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
        if (stations.Length >= 2)
        {
            SpawnAt(wheeledPrefab, stations[0].transform.position);
            SpawnAt(leggedPrefab, stations[1].transform.position);
        }
        else
        {
            Debug.LogWarning("Not enough Node_Station tags found to spawn robots.");
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
