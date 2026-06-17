# Phase 4: Unity-Python 통신 파이프라인 (3-Way Bridge) 연동 명세서

> 작성일: 2026-06-17  
> 대상 아키텍처: `ROBO-Path Unity Simulator Architecture` 내 3-Way Bridge (Path 1 & Path 2)

---

## 1. 목적 및 개요

기존 확정된 아키텍처 4장 '3-Way Bridge' 설계에 따라 Unity 시뮬레이터와 관제 시스템/DB 간의 통신망을 구축합니다.
1. **명령 채널 (Path 1):** Python(클라이언트) $\rightarrow$ Unity(서버) 웹소켓 구조. 환경 제어(예: 장애물 타일 활성화) 등을 담당.
2. **피드백 채널 (Path 2):** Unity $\rightarrow$ Python(서브프로세스) $\rightarrow$ Supabase 직접 연결 구조. 로봇 텔레메트리를 지연 없이 DB에 적재.

> **[설계 변경 고지 (단순화)]**  
> 아키텍처 3.2절의 '엣지 횡단마다 피드백 산출' 로직을 **Step 4(현재) 범위에서는 '목적지 도착 시 1회'로 단순화**합니다.  
> - 사유: 구현 시간 제약 및 난이도 조절. 세분화된 개별 엣지 단위 피드백 처리는 후속 과제로 남깁니다.
> - 따라서 `SetDestination`(출발지~도착지) 이동 전체를 논리적 1구간으로 취급하고, 목적지에 도착했을 때 단 1회의 `EmitFeedback`을 발생시킵니다.

※ 기존 제안되었던 "Python이 WebSocket으로 상시 수신 대기하며 피드백을 받는 구조"는 폐기하며, 아키텍처 원안을 준수합니다.

---

## 2. 해결된 설계 공백 (피드백 식별자 불일치)

현재 `ITelemetrySink.EmitFeedback(platform, terrainTag, L, S, E)`에는 엣지 식별자가 누락되어 백엔드 통계 갱신 시 매핑이 불가능합니다. 이를 다음과 같이 해결합니다.

- **단위 정의:** 엣지 32개를 지나는 세부 경로라도 개별 추적하지 않고, 단일 '논리적 구간'으로 보아 도착 시 1회 피드백합니다.
- **Unity 측 수정:** `RobotController`는 출발 노드 ID(`fromNodeId`)와 목적지 노드 ID(`toNodeId`) 필드를 유지하며 추적합니다. `ITelemetrySink.EmitFeedback(string platform, string fromNodeId, string toNodeId, ...)` 로 수정하여 두 식별자 쌍을 피드백에 전달합니다. (이를 위해 `SetDestination` 함수 인자도 문자열 식별자를 함께 받도록 확장)
- **Python 측 수정:** 파이썬 서브프로세스(`push_feedback.py`)는 수신받은 `fromNodeId`, `toNodeId` 쌍을 통해 `map_edges`에서 일치하는 `edge_id`를 조회합니다. 조회 성공 시 `process_new_log(edge_id, ...)`를 통해 통계를 갱신하며, 일치하는 엣지가 없으면 (논리적 통짜 구간이므로) 통계 갱신은 건너뛰고 `mission_logs` 기록만 남기는 폴백(Fallback) 처리를 수행합니다.

---

## 3. 구현 단계 (STEP 1 ~ STEP 4)

### STEP 1. Path 1: Unity 명령 수신용 WebSocket 서버 구축
- **위치:** `Unity/Assets/Scripts/Network/WebSocketServer.cs`
- **구현 내용:** 
  - `.env`에 정의된 `SIMULATOR_WS_PORT`(기본 8765)와 `SIMULATOR_HOST`를 기준으로 포트를 바인딩.
  - Python으로부터 송신되는 제어 명령 JSON(예: `HAZARD_TOGGLE` 등)을 수신.
  - 백그라운드 스레드에서 받은 메시지를 `ConcurrentQueue`와 `Update()`를 통해 Unity 메인 스레드로 전달.

### STEP 2. Path 1: 양방향 제어 명령 브릿지 연결 (장애물 타일)
- **위치:** `src/presentation/ros2_bridge/bridge.py` 및 Unity `WebSocketServer.cs` 연동부
- **구현 내용:**
  - Python에서 `websockets`를 이용해 Unity(ws://SIMULATOR_HOST:SIMULATOR_WS_PORT)에 접속.
  - Python이 임의의 조건에 따라 `{"type": "HAZARD_TOGGLE", "active": true}` 송신.
  - Unity 메인 스레드는 이를 파싱해 맵 안의 `Tile_Hazard` 객체들을 찾아 `HazardTileController.SetHazardActive()`를 호출.

### STEP 3. Path 2: Unity 피드백 Subprocess 전송 로직 구현
- **위치:** `Unity/Assets/Scripts/Network/SubprocessTelemetrySink.cs` (신규)
- **구현 내용:**
  - `ITelemetrySink`를 구현.
  - `EmitFeedback` 호출 시 파라미터(`from_node_id`, `to_node_id`, `platform`, `L`, `S`, `E`)를 JSON으로 직렬화.
  - `System.Diagnostics.Process`를 사용해 백엔드의 `python src/infrastructure/bridge/push_feedback.py '[JSON]'`을 비동기(또는 fire-and-forget) 방식으로 즉시 호출.

### STEP 4. Path 2: Python 피드백 수신 스크립트 및 DB 적재
- **위치:** `src/infrastructure/bridge/push_feedback.py` (CLI 진입점 신규) 및 `FeedbackAggregationService`
- **구현 내용:**
  - CLI 인자로 넘어온 JSON을 파싱.
  - 파싱된 `from_node_id`와 `to_node_id`를 사용하여 `map_edges` 테이블에서 일치하는 엣지의 `edge_id` 조회.
  - 엣지가 존재하면 `FeedbackAggregationService.process_new_log(edge_id, robot, mission_log)` 호출 (통계 갱신 + 로그 적재).
  - 엣지가 존재하지 않으면(단순화된 논리적 장거리 구간이라 그래프에 직통 엣지가 없는 경우) 엣지 통계 갱신은 스킵(Skip)하고 `mission_logs` 테이블에 삽입(Insert)만 수행하는 예외 처리 추가.

---

## 4. 고려 사항
- **Path 2 서브프로세스 오버헤드:** 수많은 로봇이 짧은 주기로 잦은 엣지를 통과할 때 `System.Diagnostics.Process` 스핀업 비용이 우려된다면, 향후 Batching 메커니즘 추가를 검토할 수 있으나 현재는 아키텍처 명세대로 "즉시 서브프로세스 호출" 방식을 준수하여 안정성을 최우선으로 확보합니다.
