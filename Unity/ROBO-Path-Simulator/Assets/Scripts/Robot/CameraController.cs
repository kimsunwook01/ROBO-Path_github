using UnityEngine;
using System.Linq;

namespace ROBOPath.Robot
{
    public class CameraController : MonoBehaviour
    {
        public RobotController[] robots;
        private int currentTargetIndex = 0;

        public float distance = 10.0f;
        public float xSpeed = 120.0f;
        public float ySpeed = 120.0f;
        public float scrollSpeed = 5.0f;

        public float yMinLimit = -20f;
        public float yMaxLimit = 80f;

        private float x = 0.0f;
        private float y = 0.0f;

        void Start()
        {
            Vector3 angles = transform.eulerAngles;
            x = angles.y;
            y = angles.x;

            RefreshRobots();
        }

        void RefreshRobots()
        {
            robots = FindObjectsOfType<RobotController>();
        }

        void LateUpdate()
        {
            if (Input.GetKeyDown(KeyCode.Tab))
            {
                RefreshRobots();
                if (robots.Length > 0)
                {
                    currentTargetIndex = (currentTargetIndex + 1) % robots.Length;
                }
            }

            if (robots == null || robots.Length == 0) return;

            Transform target = robots[currentTargetIndex].transform;

            if (Input.GetKeyDown(KeyCode.M))
            {
                robots[currentTargetIndex].ToggleMode();
                Debug.Log($"[CameraController] Toggled Mode for {target.name}. Manual: {robots[currentTargetIndex].isManualMode}");
            }

            if (Input.GetMouseButton(1) || Input.GetMouseButton(0))
            {
                x += Input.GetAxis("Mouse X") * xSpeed * distance * 0.02f;
                y -= Input.GetAxis("Mouse Y") * ySpeed * 0.02f;
            }

            y = ClampAngle(y, yMinLimit, yMaxLimit);

            distance -= Input.GetAxis("Mouse ScrollWheel") * scrollSpeed;
            distance = Mathf.Clamp(distance, 2f, 50f);

            Quaternion rotation = Quaternion.Euler(y, x, 0);
            Vector3 position = rotation * new Vector3(0.0f, 0.0f, -distance) + target.position + Vector3.up * 1f;

            transform.rotation = rotation;
            transform.position = position;
        }

        static float ClampAngle(float angle, float min, float max)
        {
            if (angle < -360F) angle += 360F;
            if (angle > 360F) angle -= 360F;
            return Mathf.Clamp(angle, min, max);
        }
    }
}
