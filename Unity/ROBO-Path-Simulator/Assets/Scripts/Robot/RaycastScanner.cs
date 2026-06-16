using UnityEngine;
using System.Collections;

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
                        if (col.gameObject.name.StartsWith("Node_") || col.CompareTag("Node_Station"))
                        {
                            if (telemetrySink != null)
                            {
                                telemetrySink.EmitDiscovery(col.transform.position);
                            }
                        }
                    }
                }
            }
        }
    }
}
