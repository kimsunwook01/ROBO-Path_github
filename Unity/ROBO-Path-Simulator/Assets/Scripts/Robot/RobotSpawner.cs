using UnityEngine;
using UnityEngine.AI;

public class RobotSpawner : MonoBehaviour
{
    public GameObject wheeledPrefab;
    public GameObject leggedPrefab;

    private int wheeledCount = 0;
    private int leggedCount = 0;

    void Start()
    {
        SpawnRobots();
    }

    public void SpawnRobots()
    {
        wheeledCount = 0;
        leggedCount = 0;
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
            SpawnAt(prefabToSpawn, stations[i]);
        }
    }

    private void SpawnAt(GameObject prefab, GameObject stationNode)
    {
        if (prefab == null) return;
        
        // Spawn slightly above to avoid clipping initially
        Vector3 spawnPos = stationNode.transform.position + Vector3.up * 1f;
        GameObject robot = Instantiate(prefab, spawnPos, Quaternion.identity);
        
        RobotIdentify identify = robot.GetComponent<RobotIdentify>();
        if (identify != null)
        {
            int index = 0;
            if (identify.platform == RobotPlatform.Wheeled)
            {
                wheeledCount++;
                index = wheeledCount;
            }
            else
            {
                leggedCount++;
                index = leggedCount;
            }
            identify.robotId = $"{identify.platform}-{index:D2}";
            identify.homeStationId = GenerateNodeId(stationNode);
        }

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

    private string GenerateNodeId(GameObject go)
    {
        float rotY = go.transform.rotation.eulerAngles.y;
        int gx = Mathf.RoundToInt((go.transform.position.x - 5f) / 10f);
        int gz = Mathf.RoundToInt((go.transform.position.z - 5f) / 10f);
        int y = Mathf.RoundToInt(go.transform.position.y);
        int r = Mathf.RoundToInt(rotY);
        r = (r % 360 + 360) % 360;
        
        return $"{go.name}_x{gx}_z{gz}_y{y}_r{r}";
    }
}
