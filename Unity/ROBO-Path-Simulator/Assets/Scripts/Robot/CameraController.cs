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

            Cursor.lockState = CursorLockMode.Locked;
            Cursor.visible = false;

            RefreshRobots();
        }

        void RefreshRobots()
        {
            robots = FindObjectsByType<RobotController>(FindObjectsSortMode.None);
            UpdateActiveRobot();
        }

        void UpdateActiveRobot()
        {
            if (robots == null || robots.Length == 0) return;
            for (int i = 0; i < robots.Length; i++)
            {
                robots[i].isActiveControlled = (i == currentTargetIndex);
            }
        }

        private bool isCursorLocked = true;

        void OnApplicationFocus(bool hasFocus)
        {
            if (hasFocus && isCursorLocked)
            {
                Cursor.lockState = CursorLockMode.Locked;
                Cursor.visible = false;
            }
        }

        void Update()
        {
            // 에디터 환경: Esc를 누르면 커서 잠금 해제, 화면 클릭 시 다시 잠금 (표준 FPS 방식)
            if (Input.GetKeyDown(KeyCode.Escape))
            {
                isCursorLocked = false;
                Cursor.lockState = CursorLockMode.None;
                Cursor.visible = true;
            }
            else if (Input.GetMouseButtonDown(0) || Input.GetMouseButtonDown(1))
            {
                isCursorLocked = true;
            }

            // 에디터 포커스 변화 등으로 잠금이 풀리는 현상 방지를 위해 매 프레임 재적용
            // (참고: 에디터 Play에선 Game 뷰를 한 번 클릭해야 잠금이 완전 적용되며,
            // 마우스가 에디터 밖으로 나가면 보이는 것은 에디터의 특성. 실제 빌드에선 발생하지 않음)
            if (isCursorLocked)
            {
                Cursor.lockState = CursorLockMode.Locked;
                Cursor.visible = false;
            }
        }

        void LateUpdate()
        {

            if (Input.GetKeyDown(KeyCode.Tab))
            {
                RefreshRobots();
                if (robots.Length > 0)
                {
                    currentTargetIndex = (currentTargetIndex + 1) % robots.Length;
                    UpdateActiveRobot();
                }
            }

            if (robots == null || robots.Length == 0) return;

            Transform target = robots[currentTargetIndex].transform;

            if (Input.GetKeyDown(KeyCode.M))
            {
                robots[currentTargetIndex].ToggleMode();
                Debug.Log($"[CameraController] Toggled Mode for {target.name}. Manual: {robots[currentTargetIndex].isManualMode}");
            }

            // 클릭 없이 마우스 이동만으로 회전 (커서가 잠겨 있을 때만)
            if (Cursor.lockState == CursorLockMode.Locked)
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
