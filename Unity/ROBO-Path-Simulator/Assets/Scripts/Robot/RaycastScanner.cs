using UnityEngine;
using System.Collections;
using System.Collections.Generic;

namespace ROBOPath.Robot
{
    public class RaycastScanner : MonoBehaviour
    {
        public Transform sensorOrigin;
        public float scanInterval = 0.2f;
        public float maxDistance = 30f;
        public int numRays = 36;
        public float angleSpan = 180f;

        private ITelemetrySink telemetrySink;
        private int layerMask;

        // 이미 발견(EmitDiscovery 호출)한 타일을 기억해 중복 호출을 막는다.
        // RaycastScanner는 0.2초마다 수백 번 같은 타일을 다시 보므로, 이게 없으면
        // 서브프로세스가 폭발한다. 처음 본 타일일 때만 1회 EmitDiscovery 한다.
        private HashSet<string> discoveredKeys = new HashSet<string>();

        void Start()
        {
            telemetrySink = GetComponent<ITelemetrySink>();

            if (sensorOrigin == null)
            {
                sensorOrigin = transform.Find("Body/Sensor/SensorOrigin");
                if (sensorOrigin == null) sensorOrigin = transform;
            }

            layerMask = ~(1 << 8);

            StartCoroutine(ScanRoutine());
        }

        private IEnumerator ScanRoutine()
        {
            while (true)
            {
                yield return new WaitForSeconds(scanInterval);
                PerformScan();
            }
        }

        private void PerformScan()
        {
            float startAngle = -angleSpan / 2f;
            float angleStep = angleSpan / (numRays - 1);

            for (int i = 0; i < numRays; i++)
            {
                float currentAngle = startAngle + (angleStep * i);
                Vector3 direction = Quaternion.Euler(0, currentAngle, 0) * sensorOrigin.forward;

                if (Physics.Raycast(sensorOrigin.position, direction, out RaycastHit hit, maxDistance, layerMask))
                {
                    Collider[] colliders = Physics.OverlapSphere(hit.point, 5f, layerMask);
                    foreach (var col in colliders)
                    {
                        // Spec C: 거점(Station/Pickup/Destination)은 이미 알려진 곳이므로 제외.
                        // 발견 대상은 일반 지형 타일이다.
                        bool isStationTag = col.CompareTag("Node_Station")
                                         || col.CompareTag("Node_Pickup")
                                         || col.CompareTag("Node_Destination");
                        if (isStationTag) continue;

                        // 일반 타일만 통과. 좌표를 키로 중복 제거 (10m 그리드라 좌표가 고유 식별자 역할).
                        Vector3 pos = col.transform.position;
                        string key = $"{Mathf.RoundToInt(pos.x)}_{Mathf.RoundToInt(pos.z)}";

                        if (discoveredKeys.Contains(key)) continue;  // 이미 발견한 타일 → 무시
                        discoveredKeys.Add(key);

                        if (telemetrySink != null)
                        {
                            telemetrySink.EmitDiscovery(pos);
                        }
                    }
                }
            }
        }
    }
}
