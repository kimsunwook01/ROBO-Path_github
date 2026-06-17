using System;
using System.Net;
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
    public class Waypoint
    {
        public float x;
        public float y;
        public float z;
    }

    [Serializable]
    public class CommandMessage
    {
        public string type;
        public bool active;
        public string robot_id;
        public string dest_node_id;
        public Waypoint[] waypoints;
    }

    /// <summary>
    /// Python → Unity 명령 수신 서버 (HTTP POST 방식).
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
            string portStr = Environment.GetEnvironmentVariable("SIMULATOR_WS_PORT");
            int port = defaultPort;
            if (!string.IsNullOrEmpty(portStr) && int.TryParse(portStr, out int parsedPort))
                port = parsedPort;

            string host = Environment.GetEnvironmentVariable("SIMULATOR_HOST");
            if (string.IsNullOrEmpty(host))
                host = "127.0.0.1";

            cancellationTokenSource = new CancellationTokenSource();
            string uri = $"http://{host}:{port}/";
            StartServer(uri);
        }

        private async void StartServer(string uri)
        {
            httpListener = new HttpListener();
            try
            {
                httpListener.Prefixes.Add(uri);
                httpListener.Start();
                Debug.Log($"[WebSocketServer] Listening on {uri}");
            }
            catch (Exception e)
            {
                Debug.LogError($"[WebSocketServer] Failed to start: {e.Message}");
                return;
            }

            while (!cancellationTokenSource.IsCancellationRequested)
            {
                try
                {
                    HttpListenerContext context = await httpListener.GetContextAsync();
                    if (context.Request.HttpMethod == "POST")
                        HandlePost(context);
                    else
                    {
                        context.Response.StatusCode = 400;
                        context.Response.Close();
                    }
                }
                catch (HttpListenerException) { break; }
                catch (Exception e)
                {
                    if (!cancellationTokenSource.IsCancellationRequested)
                        Debug.LogError($"[WebSocketServer] Accept Error: {e.Message}");
                }
            }
        }

        private async void HandlePost(HttpListenerContext context)
        {
            try
            {
                using (var reader = new System.IO.StreamReader(context.Request.InputStream, context.Request.ContentEncoding ?? Encoding.UTF8))
                {
                    string message = await reader.ReadToEndAsync();
                    messageQueue.Enqueue(message);
                }
                context.Response.StatusCode = 200;
                byte[] resp = Encoding.UTF8.GetBytes("OK");
                context.Response.ContentLength64 = resp.Length;
                await context.Response.OutputStream.WriteAsync(resp, 0, resp.Length);
                context.Response.Close();
            }
            catch (Exception e)
            {
                Debug.LogError($"[WebSocketServer] POST Error: {e.Message}");
                try { context.Response.StatusCode = 500; context.Response.Close(); } catch { }
            }
        }

        void Update()
        {
            while (messageQueue.TryDequeue(out string message))
                ProcessMessageOnMainThread(message);
        }

        private void ProcessMessageOnMainThread(string message)
        {
            Debug.Log($"[WebSocketServer] Received: {message.Substring(0, Math.Min(message.Length, 200))}");
            try
            {
                CommandMessage cmd = JsonUtility.FromJson<CommandMessage>(message);
                if (cmd == null) return;

                if (cmd.type == "HAZARD_TOGGLE")
                {
                    HazardTileController[] controllers = FindObjectsOfType<HazardTileController>();
                    foreach (var ctrl in controllers)
                        ctrl.SetHazardActive(cmd.active);
                    Debug.Log($"[HAZARD_TOGGLE] active={cmd.active}, tiles={controllers.Length}");
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
                                if (cmd.waypoints != null && cmd.waypoints.Length > 0)
                                {
                                    // 웨이포인트 경로를 따라가도록 설정
                                    Vector3[] wps = new Vector3[cmd.waypoints.Length];
                                    for (int i = 0; i < cmd.waypoints.Length; i++)
                                        wps[i] = new Vector3(cmd.waypoints[i].x, cmd.waypoints[i].y, cmd.waypoints[i].z);

                                    controller.SetDestinationWithWaypoints(wps, cmd.dest_node_id);
                                    Debug.Log($"[ASSIGN_MISSION] {cmd.robot_id} -> {cmd.dest_node_id} ({wps.Length} waypoints)");
                                }
                                else
                                {
                                    // 웨이포인트 없이 직접 목적지 (하위 호환)
                                    controller.SetDestination(new Vector3(cmd.waypoints[0].x, cmd.waypoints[0].y, cmd.waypoints[0].z), cmd.dest_node_id);
                                    Debug.Log($"[ASSIGN_MISSION] {cmd.robot_id} -> {cmd.dest_node_id} (direct)");
                                }
                                found = true;
                                break;
                            }
                        }
                    }
                    if (!found)
                        Debug.LogWarning($"[ASSIGN_MISSION] Robot {cmd.robot_id} not found.");
                }
            }
            catch (Exception e)
            {
                Debug.LogError($"[WebSocketServer] Parse/Execute Error: {e.Message}");
            }
        }

        void OnDestroy()
        {
            cancellationTokenSource?.Cancel();
            if (httpListener != null)
            {
                if (httpListener.IsListening) httpListener.Stop();
                httpListener.Close();
            }
        }
    }
}
