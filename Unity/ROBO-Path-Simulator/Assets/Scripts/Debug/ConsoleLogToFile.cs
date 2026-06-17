using UnityEngine;
using System;
using System.IO;
using System.Text;

namespace ROBOPath.Debugging
{
    /// <summary>
    /// Unity 콘솔의 모든 로그를 프로젝트 루트의 logs/unity_console.log 파일에 저장한다.
    /// Claude(또는 외부 도구)가 이 파일을 직접 읽어 디버깅할 수 있게 하기 위함.
    ///
    /// 사용법: 씬의 빈 GameObject 하나에 이 컴포넌트를 붙이면 된다.
    /// (RobotSpawner나 WebSocketServer가 붙어있는 오브젝트에 같이 붙여도 됨)
    /// </summary>
    public class ConsoleLogToFile : MonoBehaviour
    {
        private string logFilePath;
        private StreamWriter writer;
        private readonly object lockObj = new object();

        void Awake()
        {
            // 프로젝트 루트/logs/unity_console.log
            string projectRoot = Path.GetFullPath(Path.Combine(Application.dataPath, "../../../"));
            string logDir = Path.Combine(projectRoot, "logs");

            try
            {
                if (!Directory.Exists(logDir))
                    Directory.CreateDirectory(logDir);

                logFilePath = Path.Combine(logDir, "unity_console.log");

                // 매 실행마다 새로 시작 (append가 아니라 overwrite)
                writer = new StreamWriter(logFilePath, false, Encoding.UTF8);
                writer.AutoFlush = true;

                writer.WriteLine($"=== Unity Console Log — Session started {DateTime.Now:yyyy-MM-dd HH:mm:ss} ===");
            }
            catch (Exception e)
            {
                UnityEngine.Debug.LogError($"[ConsoleLogToFile] Failed to open log file: {e.Message}");
            }

            Application.logMessageReceivedThreaded += HandleLog;
        }

        private void HandleLog(string logString, string stackTrace, LogType type)
        {
            if (writer == null) return;

            lock (lockObj)
            {
                try
                {
                    string ts = DateTime.Now.ToString("HH:mm:ss");
                    string prefix = type switch
                    {
                        LogType.Error => "[ERROR]",
                        LogType.Exception => "[EXCEPTION]",
                        LogType.Warning => "[WARN]",
                        LogType.Assert => "[ASSERT]",
                        _ => "[INFO]"
                    };

                    writer.WriteLine($"{ts} {prefix} {logString}");

                    // 에러/예외는 스택트레이스도 기록 (디버깅에 유용)
                    if (type == LogType.Error || type == LogType.Exception)
                    {
                        if (!string.IsNullOrEmpty(stackTrace))
                            writer.WriteLine($"    {stackTrace.Replace("\n", "\n    ").TrimEnd()}");
                    }
                }
                catch { /* 로깅 실패가 게임을 멈추면 안 됨 */ }
            }
        }

        void OnDestroy()
        {
            Application.logMessageReceivedThreaded -= HandleLog;
            lock (lockObj)
            {
                if (writer != null)
                {
                    try
                    {
                        writer.WriteLine($"=== Session ended {DateTime.Now:yyyy-MM-dd HH:mm:ss} ===");
                        writer.Flush();
                        writer.Close();
                    }
                    catch { }
                    writer = null;
                }
            }
        }
    }
}
