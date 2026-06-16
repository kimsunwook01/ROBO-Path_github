# Phase 4: Unity 내장 WebSocket 서버 및 Python 브릿지 구현 명세서

> 작성일: 2026-06-17  
> 대상 파이프라인: `Unity 시뮬레이터 (Server)` ↔ `Python Backend (Client)` ↔ `Supabase DB`

---

## 1. 목적 및 개요

Unity 시뮬레이터 내부에서 자체적인 **WebSocket 서버**를 구동하여, 로봇 주행 중 발생하는 텔레메트리(발견된 노드, 주행 완료에 따른 피드백 성적 등)를 외부로 브로드캐스트합니다.
동시에 파이썬 기반의 **브릿지(Client)** 프로그램이 이에 접속하여 데이터를 수신한 뒤, 백엔드의 `FeedbackAggregationService`를 통해 Supabase 데이터베이스에 적재하고 엣지 가중치(`platform_stats`)를 갱신합니다. 또한, 파이썬 브릿지는 Unity 쪽으로 돌발 이벤트(예: `Tile_Hazard` 활성화) 명령을 송신하여 양방향 제어를 완성합니다.

---

## 2. 프로젝트 현황 대조 및 사전 검증

본 계획을 수립하기 위해 프로젝트의 현재 상태를 검증한 결과입니다.

| 검증 항목 | 확인 결과 | 조치 필요 사항 |
|-----------|-----------|----------------|
| **Unity 통신 기반** | `ITelemetrySink` 인터페이스 및 로컬 로그용 `LogTelemetrySink` 존재함. | `ITelemetrySink`를 구현하는 `WebSocketTelemetrySink` 신규 작성 필요. |
| **장애물 타일 제어** | `HazardTileController.SetHazardActive(bool)` API가 구현됨(Phase 3c). | WebSocket 수신부에서 특정 명령을 파싱해 이 API를 호출하는 브릿징 코드 필요. |
| **Python 백엔드 서비스** | `FeedbackAggregationService` 및 Supabase 저장소 레포지토리가 이미 구현되어 있음. | 수신된 WebSocket JSON 페이로드를 도메인 모델로 매핑하고 서비스를 호출하는 `unity_bridge.py` 작성 필요. |
| **비동기 통신 라이브러리** | Python 측 `websockets`, `asyncio` 모듈. Unity 측 `System.Net.HttpListener` 및 `System.Net.WebSockets`. | 추가 플러그인 없이 Unity 내장 클래스와 Python 기본 생태계로 구현 가능. |

---

## 3. 구현 단계 (작업 세분화)

작업의 복잡도를 낮추고 오류를 추적하기 쉽도록 총 4개의 세부 단계로 나누어 진행합니다.

### STEP 1. Unity `WebSocketServer` 및 통신 인프라 구축
**대상 파일:** `Assets/Scripts/Network/WebSocketServer.cs` (신규)

**작업 내용:**
- `HttpListener`를 사용하여 로컬 포트(예: 8080)에서 WebSocket 연결을 수락하는 기본 서버 구동 (별도 스레드 또는 `async/await` 활용).
- 연결된 클라이언트 리스트 관리 및 브로드캐스트(`BroadcastMessage`) 기능 구현.
- MonoBehaviour 기반으로 Unity 생명주기(`OnEnable`, `OnDisable`)에 맞춰 서버 안전 종료 로직 작성.

### STEP 2. Unity `WebSocketTelemetrySink` 구현 및 연동
**대상 파일:** `Assets/Scripts/Network/WebSocketTelemetrySink.cs` (신규)

**작업 내용:**
- `ITelemetrySink` 인터페이스 구현.
- `EmitFeedback(feedback)` 및 `EmitDiscovery(pos)` 호출 시, 데이터를 JSON 문자열로 직렬화하여 `WebSocketServer`를 통해 전송.
- 로봇 프리팹(`Robot_Wheeled`, `Robot_Legged`)의 `LogTelemetrySink`를 대체(또는 병행)하도록 부착 및 연결.

### STEP 3. Python 브릿지 클라이언트 구현 (수신 및 DB 적재)
**대상 파일:** `src/presentation/ros2_bridge/unity_bridge.py` (신규)

**작업 내용:**
- 파이썬 `websockets` 라이브러리를 사용해 `ws://localhost:8080`에 지속적으로 연결 유지.
- 수신된 JSON 데이터 파싱 (예: 메시지 타입이 `FEEDBACK`인지 `DISCOVERY`인지 분류).
- `FEEDBACK` 수신 시: 
  1. `MissionLog` 도메인 객체 생성.
  2. `FeedbackAggregationService.process_feedback()`을 호출하여 `mission_logs` DB 삽입 및 `map_edges`의 `platform_stats` 업데이트 수행.

### STEP 4. 양방향 제어: Python $\rightarrow$ Unity 장애물 타일 제어
**대상 파일:** 
- `Assets/Scripts/Network/WebSocketServer.cs` (수신부 추가)
- `src/presentation/ros2_bridge/unity_bridge.py` (송신부 추가)

**작업 내용:**
- **[Python]** 무작위 타이머 또는 특정 조건에 맞춰 `{"type": "HAZARD_TOGGLE", "active": true}` 형태의 제어 명령을 Unity로 송신.
- **[Unity]** 수신한 명령을 메인 스레드(Dispatcher) 큐로 전달. 맵에 존재하는 `Tile_Hazard` 오브젝트들을 찾아 `SetHazardActive()`를 호출하여 투명도 및 활성 상태 전환.

---

## 4. 제약 사항 및 고려 사항
- **스레드 안전성 (Thread Safety):** `System.Net.WebSockets` 수신 콜백은 백그라운드 스레드에서 실행되므로, 여기서 직접 Unity GameObject에 접근하면 에러가 발생합니다. 반드시 `ConcurrentQueue`와 `Update()`를 활용한 메인 스레드 디스패칭(Main Thread Dispatching) 패턴을 사용해야 합니다.
- **직렬화 성능:** Unity에서 JSON 파싱은 `Newtonsoft.Json`을 활용하여 박싱/언박싱 오버헤드를 최소화합니다.
