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
    }

    /// <summary>
    /// Phase 4 Path 2: Unity -> Python(Subprocess) -> Supabase
    /// 로봇이 목적지에 도착하면 피드백을 Python 스크립트로 전달하여 DB에 적재합니다.
    /// Discovery(탐색)는 Spec C 구현 전까지 서브프로세스를 호출하지 않습니다.
    /// </summary>
    public class SubprocessTelemetrySink : MonoBehaviour, ITelemetrySink
    {
        private string pythonPath = "python";
        private string scriptPath = "src/infrastructure/bridge/push_feedback.py";
        private string projectRoot;

        void Start()
        {
            projectRoot = Path.GetFullPath(Path.Combine(Application.dataPath, "../../../"));
            Debug.Log($"[SubprocessTelemetrySink] Project root: {projectRoot}");
            Debug.Log($"[SubprocessTelemetrySink] Script exists: {File.Exists(Path.Combine(projectRoot, scriptPath))}");
        }

        public void EmitFeedback(RobotPlatform platform, string fromNodeId, string toNodeId, float? load, float? stability, float? efficiency)
        {
            FeedbackPayload payloadObj = new FeedbackPayload
            {
                from_node_id = fromNodeId,
                to_node_id = toNodeId,
                platform = platform.ToString().ToLower(),  // Python Robot 모델은 "wheeled"/"legged"(소문자)만 허용
                L = load ?? 0f,
                S = stability ?? 0f,
                E = efficiency ?? 0f
            };

            string json = JsonUtility.ToJson(payloadObj);
            string finalJson = $"{{\"type\":\"FEEDBACK\",\"data\":{json}}}";

            Debug.Log($"[SubprocessTelemetrySink] Sending FEEDBACK: {finalJson}");
            FireAndForgetPython(finalJson);
        }

        public void EmitDiscovery(Vector3 nodePos)
        {
            // Spec C(Discovery 파이프라인) 구현 전까지 서브프로세스를 호출하지 않음.
            // RaycastScanner가 0.2초마다 수백 번 호출하므로, 여기서 서브프로세스를
            // 띄우면 시스템이 먹통이 됨. push_feedback.py도 DISCOVERY를 무시하므로
            // 호출해봐야 의미 없음.
            // TODO: Spec C 구현 시 배치/스로틀 방식으로 변경
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
                        string output = process.StandardOutput.ReadToEnd();
                        string error = process.StandardError.ReadToEnd();
                        process.WaitForExit();

                        if (process.ExitCode != 0)
                        {
                            Debug.LogError($"[SubprocessTelemetrySink] Python Error (Code {process.ExitCode}):\n{error}");
                        }
                        else
                        {
                            if (!string.IsNullOrEmpty(output))
                                Debug.Log($"[SubprocessTelemetrySink] Python Output:\n{output.Trim()}");
                        }
                    }
                }
                catch (System.Exception ex)
                {
                    Debug.LogError($"[SubprocessTelemetrySink] Exception: {ex.Message}");
                }
            });
        }
    }
}
