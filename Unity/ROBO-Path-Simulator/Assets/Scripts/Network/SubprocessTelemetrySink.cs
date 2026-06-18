using UnityEngine;
using System.Diagnostics;
using System.IO;
using ROBOPath.Robot;
using System.Threading.Tasks;
using Debug = UnityEngine.Debug;

namespace ROBOPath.Network
{
    [System.Serializable]
    public class FeedbackPayload
    {
        public string from_node_id;
        public string to_node_id;
        public string platform;
        public float L;
        public float S;
        public float E;
        public float battery_pct;
    }

    /// <summary>
    /// Phase 4 Path 2: Unity -> Python(Subprocess) -> Supabase
    /// 로봇이 목적지에 도착하면 피드백을 Python 스크립트로 전달하여 DB에 적재합니다.
    /// Discovery(탐색)는 Spec C 구현 전까지 서브프로세스를 호출하지 않습니다.
    /// </summary>
    public class SubprocessTelemetrySink : MonoBehaviour, ITelemetrySink
    {
        // robopath conda 환경의 python.exe 절대 경로.
        // Unity가 띄우는 서브프로세스는 conda 환경을 자동으로 활성화하지 않으므로,
        // supabase 등이 설치된 환경의 python을 정확히 지정해야 한다.
        // 환경변수 ROBOPATH_PYTHON 이 있으면 그것을 우선 사용.
        private string pythonPath;
        private string scriptPath = "src/infrastructure/bridge/push_feedback.py";
        private string projectRoot;

        void Start()
        {
            projectRoot = Path.GetFullPath(Path.Combine(Application.dataPath, "../../../"));

            // 1순위: 환경변수 ROBOPATH_PYTHON
            pythonPath = System.Environment.GetEnvironmentVariable("ROBOPATH_PYTHON");

            // 2순위: 일반적인 conda 환경 경로 추정 (Windows)
            if (string.IsNullOrEmpty(pythonPath))
            {
                string userProfile = System.Environment.GetEnvironmentVariable("USERPROFILE");
                if (!string.IsNullOrEmpty(userProfile))
                {
                    string candidate = Path.Combine(userProfile, "anaconda3", "envs", "robopath", "python.exe");
                    if (File.Exists(candidate))
                        pythonPath = candidate;
                }
            }

            // 3순위: 폴백 (PATH의 python)
            if (string.IsNullOrEmpty(pythonPath))
                pythonPath = "python";

            Debug.Log($"[SubprocessTelemetrySink] Project root: {projectRoot}");
            Debug.Log($"[SubprocessTelemetrySink] Python path: {pythonPath}");
            Debug.Log($"[SubprocessTelemetrySink] Script exists: {File.Exists(Path.Combine(projectRoot, scriptPath))}");
        }

        public void EmitFeedback(RobotPlatform platform, string fromNodeId, string toNodeId, float? load, float? stability, float? efficiency, float batteryPct)
        {
            FeedbackPayload payloadObj = new FeedbackPayload
            {
                from_node_id = fromNodeId,
                to_node_id = toNodeId,
                platform = platform.ToString().ToLower(),  // Python Robot 모델은 "wheeled"/"legged"(소문자)만 허용
                L = load ?? 0f,
                S = stability ?? 0f,
                E = efficiency ?? 0f,
                battery_pct = batteryPct
            };

            string json = JsonUtility.ToJson(payloadObj);
            string finalJson = $"{{\"type\":\"FEEDBACK\",\"data\":{json}}}";

            Debug.Log($"[SubprocessTelemetrySink] Sending FEEDBACK: {finalJson}");
            FireAndForgetPython(finalJson);
        }

        public void EmitDiscovery(Vector3 nodePos)
        {
            // Spec C: 처음 본 타일일 때만 RaycastScanner가 이 메서드를 호출한다
            // (중복 제거는 RaycastScanner의 HashSet이 담당). 좌표를 push_feedback.py로 전달.
            string json = $"{{\"x\":{nodePos.x},\"y\":{nodePos.y},\"z\":{nodePos.z}}}";
            string finalJson = $"{{\"type\":\"DISCOVERY\",\"data\":{json}}}";

            Debug.Log($"[SubprocessTelemetrySink] Sending DISCOVERY: ({nodePos.x:F1}, {nodePos.z:F1})");
            FireAndForgetPython(finalJson);
        }

        private async void FireAndForgetPython(string jsonArgs)
        {
            await Task.Run(() =>
            {
                try
                {
                    string escapedArgs = jsonArgs.Replace("\"", "\\\"");

                    ProcessStartInfo psi = new ProcessStartInfo
                    {
                        FileName = pythonPath,
                        Arguments = $"{scriptPath} \"{escapedArgs}\"",
                        UseShellExecute = false,
                        RedirectStandardOutput = true,
                        RedirectStandardError = true,
                        CreateNoWindow = true,
                        WorkingDirectory = projectRoot
                    };

                    // PYTHONPATH를 프로젝트 루트로 설정 (src 모듈 import 가능하게)
                    psi.EnvironmentVariables["PYTHONPATH"] = projectRoot;

                    using (Process process = Process.Start(psi))
                    {
                        // 비동기로 읽어 파이프 버퍼 데드락 방지 (ReadToEnd 먼저 호출 후 WaitForExit 은 대용량 출력 시 마비함)
                        Task<string> outputTask = process.StandardOutput.ReadToEndAsync();
                        Task<string> errorTask = process.StandardError.ReadToEndAsync();

                        bool exited = process.WaitForExit(30000); // 최대 30초 대기

                        if (!exited)
                        {
                            Debug.LogError("[SubprocessTelemetrySink] Python 프로세스가 30초 내에 끝나지 않아 강제 종료함");
                            try { process.Kill(); } catch { }
                            return;
                        }

                        string output = outputTask.Result;
                        string error = errorTask.Result;

                        if (process.ExitCode != 0)
                        {
                            Debug.LogError($"[SubprocessTelemetrySink] Python Error (Code {process.ExitCode}):\n{error}");
                        }
                        else
                        {
                            if (!string.IsNullOrEmpty(output))
                                Debug.Log($"[SubprocessTelemetrySink] Python Output:\n{output.Trim()}");
                            else
                                Debug.Log("[SubprocessTelemetrySink] Python 종료(exit 0), 출력 없음");

                            if (!string.IsNullOrEmpty(error))
                                Debug.LogWarning($"[SubprocessTelemetrySink] Python stderr:\n{error.Trim()}");
                        }
                    }
                }
                catch (System.Exception ex)
                {
                    Debug.LogError($"[SubprocessTelemetrySink] Exception: {ex.Message}\n{ex.StackTrace}");
                }
            });
        }
    }
}
