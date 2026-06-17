using System;
using System.Net;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Collections.Concurrent;
using UnityEngine;
using ROBOPath.Tile;
using ROBOPath.Robot;

namespace ROBOPath.Network
{
    [Serializable]
    public class CommandMessage
    {
        public string type;
        public bool active;
        public string robot_id;
        public float dest_x;
        public float dest_y;
        public float dest_z;
        public string dest_node_id;
    }

    /// <summary>
    /// Phase 4 Path 1: Python 클라이언트의 명령(예: 장애물 토글)을 수신하기 위한 
    /// Unity 내장 WebSocket 서버.
    /// System.Net.HttpListener를 사용하여 로컬 포트를 수신 대기하고,
    /// ConcurrentQueue를 통해 안전하게 Unity Main Thread에서 명령을 실행한다.
    /// </summary>
    public class WebSocketServer : MonoBehaviour
    {
        [Header("Server Configuration")]
        [Tooltip("환경변수 SIMULATOR_WS_PORT가 없을 경우 사용할 기본 포트")]
        public int defaultPort = 8765;

        private HttpListener httpListener;
        private CancellationTokenSource cancellationTokenSource;
        private ConcurrentQueue<string> messageQueue = new ConcurrentQueue<string>();

        void Start()
        {
            // .env 또는 환경변수에서 포트 확인
            string portStr = Environment.GetEnvironmentVariable("SIMULATOR_WS_PORT");
            int port = defaultPort;
            if (!string.IsNullOrEmpty(portStr) && int.TryParse(portStr, out int parsedPort))
            {
                port = parsedPort;
            }

            cancellationTokenSource = new CancellationTokenSource();
            string uri = $"http://127.0.0.1:{port}/";
            StartServer(uri);
        }

        private async void StartServer(string uri)
        {
            httpListener = new HttpListener();
            try
            {
                httpListener.Prefixes.Add(uri);
                httpListener.Start();
                Debug.Log($"WebSocket Server listening on {uri}");
            }
            catch (Exception e)
            {
                Debug.LogError($"Failed to start HttpListener: {e.Message}");
                return;
            }

            while (!cancellationTokenSource.IsCancellationRequested)
            {
                try
                {
                    HttpListenerContext context = await httpListener.GetContextAsync();
                    if (context.Request.HttpMethod == "POST")
                    {
                        ProcessWebSocketRequest(context);
                    }
                    else
                    {
                        context.Response.StatusCode = 400;
                        context.Response.Close();
                    }
                }
                catch (HttpListenerException)
                {
                    // Listener stopped or disposed
                    break;
                }
                catch (Exception e)
                {
                    if (!cancellationTokenSource.IsCancellationRequested)
                        Debug.LogError($"HttpListener Accept Error: {e.Message}");
                }
            }
        }

        private async void ProcessWebSocketRequest(HttpListenerContext context)
        {
            try
            {
                if (context.Request.HttpMethod == "POST")
                {
                    using (var reader = new System.IO.StreamReader(context.Request.InputStream, context.Request.ContentEncoding ?? Encoding.UTF8))
                    {
                        string message = await reader.ReadToEndAsync();
                        messageQueue.Enqueue(message);
                    }
                    context.Response.StatusCode = 200;
                    byte[] response = Encoding.UTF8.GetBytes("OK");
                    context.Response.ContentLength64 = response.Length;
                    await context.Response.OutputStream.WriteAsync(response, 0, response.Length);
                    context.Response.Close();
                }
                else
                {
                    context.Response.StatusCode = 405; // Method Not Allowed
                    context.Response.Close();
                }
            }
            catch (Exception e)
            {
                Debug.LogError($"HTTP Post Accept Error: {e.Message}");
                context.Response.StatusCode = 500;
                context.Response.Close();
            }
        }

        // ReceiveMessages was removed because we now use HTTP POST directly

        void Update()
        {
            // 백그라운드 스레드에서 수신한 메시지를 Main Thread로 꺼내 처리
            while (messageQueue.TryDequeue(out string message))
            {
                ProcessMessageOnMainThread(message);
            }
        }

        private void ProcessMessageOnMainThread(string message)
        {
            Debug.Log($"Received Command: {message}");
            try
            {
                CommandMessage cmd = JsonUtility.FromJson<CommandMessage>(message);
                if (cmd != null)
                {
                    if (cmd.type == "HAZARD_TOGGLE")
                    {
                        // 활성/비활성 명령에 따라 모든 Hazard 타일 제어
                        HazardTileController[] controllers = FindObjectsOfType<HazardTileController>();
                        foreach (var ctrl in controllers)
                        {
                            ctrl.SetHazardActive(cmd.active);
                        }
                        Debug.Log($"[HAZARD_TOGGLE] active: {cmd.active}, affected tiles: {controllers.Length}");
                    }
                    else if (cmd.type == "ASSIGN_MISSION")
                    {
                        RobotIdentify[] robots = FindObjectsOfType<RobotIdentify>();
                        bool found = false;
                        foreach (var robot in robots)
                        {
                            if (robot.robotId == cmd.robot_id)
                            {
                                RobotController controller = robot.GetComponent<RobotController>();
                                if (controller != null)
                                {
                                    controller.SetDestination(new Vector3(cmd.dest_x, cmd.dest_y, cmd.dest_z), cmd.dest_node_id);
                                    Debug.Log($"[ASSIGN_MISSION] Robot {cmd.robot_id} moving to {cmd.dest_node_id} ({cmd.dest_x}, {cmd.dest_y}, {cmd.dest_z})");
                                    found = true;
                                    break;
                                }
                            }
                        }
                        if (!found)
                        {
                            Debug.LogWarning($"[ASSIGN_MISSION] Robot {cmd.robot_id} not found to assign mission to.");
                        }
                    }
                }
            }
            catch (Exception e)
            {
                Debug.LogError($"Failed to parse or execute WebSocket command: {e.Message}");
            }
        }

        void OnDestroy()
        {
            cancellationTokenSource?.Cancel();

            if (httpListener != null)
            {
                if (httpListener.IsListening)
                    httpListener.Stop();
                httpListener.Close();
            }
        }
    }
}
