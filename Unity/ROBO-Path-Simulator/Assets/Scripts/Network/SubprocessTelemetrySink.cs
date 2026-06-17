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
        public float? L;
        public float? S;
        public float? E;
    }

    [System.Serializable]
    public class DiscoveryPayload
    {
        public float x;
        public float y;
        public float z;
    }

    /// <summary>
    /// Phase 4 Path 2: Unity -> Python(Subprocess) -> Supabase
    /// 피드백을 실시간으로 백엔드 파이썬 스크립트를 호출하여 적재합니다.
    /// </summary>
    public class SubprocessTelemetrySink : MonoBehaviour, ITelemetrySink
    {
        private string pythonPath = "python";
        private string scriptPath = "src/infrastructure/bridge/push_feedback.py";

        void Start()
        {
            // 프로젝트 루트 기준의 경로가 될 수 있도록 보정할 수 있으나,
            // 보통 Unity 에디터/빌드에서 실행될 때 CWD나 .env를 활용.
            // 일단은 상대 경로로 지정.
        }

        public void EmitFeedback(RobotPlatform platform, string fromNodeId, string toNodeId, float? load, float? stability, float? efficiency)
        {
            FeedbackPayload payloadObj = new FeedbackPayload
            {
                from_node_id = fromNodeId,
                to_node_id = toNodeId,
                platform = platform.ToString(),
                L = load,
                S = stability,
                E = efficiency
            };

            string json = JsonUtility.ToJson(payloadObj);
            
            // "type":"FEEDBACK" 래핑
            string finalJson = $"{{\"type\":\"FEEDBACK\",\"data\":{json}}}";
            
            FireAndForgetPython(finalJson);
        }

        public void EmitDiscovery(Vector3 nodePos)
        {
            DiscoveryPayload payloadObj = new DiscoveryPayload
            {
                x = nodePos.x,
                y = nodePos.y,
                z = nodePos.z
            };

            string json = JsonUtility.ToJson(payloadObj);
            
            // "type":"DISCOVERY" 래핑
            string finalJson = $"{{\"type\":\"DISCOVERY\",\"data\":{json}}}";

            FireAndForgetPython(finalJson);
        }

        private async void FireAndForgetPython(string jsonArgs)
        {
            // 백그라운드 스레드에서 서브프로세스 실행 (Unity 메인 스레드 블로킹 방지)
            await Task.Run(() =>
            {
                try
                {
                    // 파이썬 명령어에서 JSON을 안전하게 감싸기 (윈도우/맥 호환)
                    string escapedArgs = jsonArgs.Replace("\"", "\\\"");

                    ProcessStartInfo psi = new ProcessStartInfo
                    {
                        FileName = pythonPath,
                        Arguments = $"{scriptPath} \"{escapedArgs}\"",
                        UseShellExecute = false,
                        RedirectStandardOutput = true,
                        RedirectStandardError = true,
                        CreateNoWindow = true,
                        // 환경변수 PYTHONPATH="." 적용 효과를 위해 WorkingDirectory를 설정하거나,
                        // 실행 시점에서 루트 디렉토리 기준이라고 가정
                        WorkingDirectory = Path.GetFullPath(Path.Combine(Application.dataPath, "../../")) // ROBO-Path_project root
                    };

                    using (Process process = Process.Start(psi))
                    {
                        process.WaitForExit();
                        string output = process.StandardOutput.ReadToEnd();
                        string error = process.StandardError.ReadToEnd();

                        if (process.ExitCode != 0)
                        {
                            // 콜백을 통해 Main Thread에서 로깅해야 하지만, 
                            // UnityEngine.Debug는 스레드 안전성 보장이 완벽하진 않음(단, 2017 이상에서 로깅은 대부분 스레드 세이프)
                            Debug.LogError($"[SubprocessTelemetrySink] Python Error (Code {process.ExitCode}): {error}");
                        }
                        else if (!string.IsNullOrEmpty(output))
                        {
                            Debug.Log($"[SubprocessTelemetrySink] Python Output: {output.Trim()}");
                        }
                    }
                }
                catch (System.Exception ex)
                {
                    Debug.LogError($"[SubprocessTelemetrySink] Exception starting process: {ex.Message}");
                }
            });
        }
    }
}
