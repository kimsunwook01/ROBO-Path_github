using System;
using System.Net;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Collections.Concurrent;
using UnityEngine;
using ROBOPath.Tile;

namespace ROBOPath.Network
{
    [Serializable]
    public class CommandMessage
    {
        public string type;
        public bool active;
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
            string uri = $"http://+:{port}/";
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
                    if (context.Request.IsWebSocketRequest)
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
                HttpListenerWebSocketContext wsContext = await context.AcceptWebSocketAsync(subProtocol: null);
                WebSocket webSocket = wsContext.WebSocket;
                Debug.Log("WebSocket Client Connected.");

                await ReceiveMessages(webSocket);
            }
            catch (Exception e)
            {
                Debug.LogError($"WebSocket Accept Error: {e.Message}");
                context.Response.StatusCode = 500;
                context.Response.Close();
            }
        }

        private async Task ReceiveMessages(WebSocket webSocket)
        {
            byte[] buffer = new byte[4096];
            try
            {
                while (webSocket.State == WebSocketState.Open && !cancellationTokenSource.IsCancellationRequested)
                {
                    WebSocketReceiveResult result = await webSocket.ReceiveAsync(
                        new ArraySegment<byte>(buffer), cancellationTokenSource.Token);

                    if (result.MessageType == WebSocketMessageType.Close)
                    {
                        await webSocket.CloseAsync(WebSocketCloseStatus.NormalClosure, string.Empty, CancellationToken.None);
                        Debug.Log("WebSocket Client Disconnected.");
                    }
                    else if (result.MessageType == WebSocketMessageType.Text)
                    {
                        string message = Encoding.UTF8.GetString(buffer, 0, result.Count);
                        messageQueue.Enqueue(message);
                    }
                }
            }
            catch (OperationCanceledException)
            {
                // 정상 종료
            }
            catch (Exception e)
            {
                if (webSocket.State != WebSocketState.Closed && webSocket.State != WebSocketState.Aborted)
                {
                    Debug.LogError($"WebSocket Receive Error: {e.Message}");
                }
            }
            finally
            {
                if (webSocket != null)
                    webSocket.Dispose();
            }
        }

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
                if (cmd != null && cmd.type == "HAZARD_TOGGLE")
                {
                    // 활성/비활성 명령에 따라 모든 Hazard 타일 제어
                    HazardTileController[] controllers = FindObjectsOfType<HazardTileController>();
                    foreach (var ctrl in controllers)
                    {
                        ctrl.SetHazardActive(cmd.active);
                    }
                    Debug.Log($"[HAZARD_TOGGLE] active: {cmd.active}, affected tiles: {controllers.Length}");
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
