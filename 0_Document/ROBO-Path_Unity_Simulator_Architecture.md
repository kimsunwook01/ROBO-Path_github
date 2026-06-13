# ROBO-Path Unity 3D 시뮬레이터 아키텍처 명세서

이 문서는 기존 NVIDIA Isaac Sim에서 전환된 **Unity 6.4 기반 시뮬레이터 환경**의 아키텍처와 로봇 피드백 수집 및 외부 통신 메커니즘을 상세히 정의합니다.

## 1. 시뮬레이션 환경 (Environment)
- **플랫폼:** Mac Mini (M2 Pro), macOS
- **엔진:** Unity 6.4 (6000.4.11f1) / Universal Render Pipeline (URP)
- **맵 규모:** 500m × 500m 가상 캠퍼스 (1 Unity Unit = 1m)
- **환경 구성:**
  - **Terrain:** 평지, 언덕, 경사로
  - **ProBuilder:** 야외 계단, 터널, 건물 외관(내부 구현 없음)
- **내비게이션:** AI Navigation 패키지를 활용한 NavMesh 베이크

---

## 2. 로봇 모델 및 내비게이션 (Robots)

ROBO-Path는 두 가지 하드웨어 플랫폼의 상이한 동역학적 특성을 NavMeshArea 및 물리 계산식으로 분리하여 시뮬레이션합니다.

### 2.1 Wheeled (바퀴형 플랫폼)
- **이동 제약:** Walkable, Road 영역만 통행 가능
- **경사 한계:** 15도 초과 경사 및 계단 통행 불가
- **플랫폼 가중치:** $W_L = 0.3$, $W_S = 0.5$, $W_E = 0.2$

### 2.2 Legged (보행형 플랫폼)
- **이동 제약:** 맵 내 전체 영역 이동 가능 (계단 포함)
- **플랫폼 가중치:** $W_L = 0.2$, $W_S = 0.3$, $W_E = 0.5$

---

## 3. 탐색 및 물리 피드백 산출 메커니즘

### 3.1 Raycast 기반 노드 탐색 (Node Discovery)
가상 LiDAR를 모사하기 위해 Raycast를 활용하여 미탐색 구역(`BASE` 노드 제외)을 스캔합니다.
- **방식:** 로봇 전방 180도 부채꼴 방향으로 36개의 Ray 발사
- **사거리:** 최대 30m
- **조건:** Ray가 히트한 지점 반경 5m 내의 노드를 찾아 기존 데이터베이스 필드를 활용하여 `node_type`을 `DISCOVERED`로 전환하고 `confidence_score`를 할당합니다. 탐색 즉시 Supabase로 업데이트됩니다.

### 3.2 엣지 물리 피드백 연산
로봇이 두 노드 사이의 엣지를 횡단 완료할 때마다, 아래 3대 지표를 산출하여 DB의 플랫폼 통계(`platform_stats` JSONB 필드)에 누적 평균치로 갱신(UPDATE)합니다.

- **부하율 ($L$):** NavMeshAgent.velocity 보정 및 경사도 연산
  - 평지: $0.1 \sim 0.2$
  - 경사 10도: $0.4 \sim 0.5$
  - 경사 20도: $0.7 \sim 0.8$
  - 계단: $0.9$ (Legged 전용)
- **안정성 지수 ($S$):** Rigidbody 진동값 보정
  - 평지: $0.9 \sim 1.0$
  - 터널: $0.8 \sim 0.9$
  - 경사: $0.6 \sim 0.8$
  - 계단: $0.5 \sim 0.7$
- **효율성 지수 ($E$):** 예상 이동시간 대비 실제 소요 시간 비율 (내리막길 등으로 예상보다 빠를 경우 1.0 초과 가능)

---

## 4. 통신 네트워크 아키텍처 (3-Way Bridge)

시뮬레이터와 관제 서버(Streamlit/DB) 간의 통신은 역할과 데이터 부하에 따라 3개의 독립된 경로로 분리하여 운영합니다.

### 4.1 경로 1: 명령 하달 (라즈베리파이 $\rightarrow$ Unity)
- **역할:** 사용자 명령(목적지 설정, 시간배율, 날씨 등) 전달
- **위치:** `src/presentation/ros2_bridge/bridge.py`
- **방식:** WebSocket 클라이언트 $\rightarrow$ Unity WebSocket 서버
- **Unity 측:** `Unity/Assets/Scripts/Network/WebSocketServer.cs`
- **통신 설정:** `.env`의 `SIMULATOR_WS_PORT` (기본 8765), IP: `SIMULATOR_HOST`

### 4.2 경로 2: 경량 지표 전송 (Unity $\rightarrow$ Supabase)
- **역할:** 피드백 지표(L, S, E), 노드/엣지 탐색 결과 등 실시간 메타데이터 전송
- **위치:** `src/infrastructure/bridge/bridge.py`
- **방식:** Unity C#가 `System.Diagnostics.Process`로 Python 서브프로세스 호출 $\rightarrow$ Supabase Python SDK로 DB INSERT/UPDATE 수행
- **통신 설정:** `.env`의 `SUPABASE_URL`, `SUPABASE_KEY`

### 4.3 경로 3: 대용량 파일 전송 (Unity $\rightarrow$ 라즈베리파이)
- **역할:** 주행 로그 CSV, 복셀 데이터 파일 등 DB에 직접 넣기 부담스러운 대용량 파일 전송
- **위치 (서버):** `src/infrastructure/storage/api.py` (FastAPI 스토리지 서버)
- **방식:** Unity C#에서 HTTP POST (Multipart Form-Data) 호출 $\rightarrow$ FastAPI `/upload/log` 등의 엔드포인트 수신
- **저장소:** 라즈베리파이 1TB SSD 저장
- **참고:** 기존 `.pcd` 업로드 엔드포인트는 향후 Isaac Sim 연동 등 확장을 대비하여 유지하되, 현재는 CSV 주행 로그 및 복셀 탐색 데이터 파일 위주로 사용합니다.

---

## 5. 페일세이프 (Failsafe) 메커니즘

시뮬레이터(Mac Mini) 오프라인 상태에 대비해 시스템을 보호하는 메커니즘을 구체화합니다.

### 5.1 동작 정의
- Mac Mini 시뮬레이터가 종료되거나 연결이 끊기면 Streamlit이 이를 감지하여 UI를 읽기 전용 모드로 자동 전환합니다.
- Mac Mini 재구동 시 자동으로 정상 상태를 복구합니다.
- 기존 rosbridge 핑 방식에서 Unity 상태(Heartbeat) 기반으로 감지 메커니즘을 변경합니다.

### 5.2 하트비트 메커니즘
- **Unity 측:** `Unity/Assets/Scripts/Network/HeartbeatSender.cs`가 매 10초마다 Supabase `simulator_status` 테이블에 `is_online=TRUE`, `last_heartbeat=NOW()`를 업데이트합니다. 앱 종료 시점(`OnApplicationQuit()`)에 `is_online=FALSE`로 갱신합니다.
- **Streamlit 측:** Supabase Realtime으로 `simulator_status` 테이블을 구독하여 실시간 감시합니다. `is_online=FALSE`이거나 `last_heartbeat`가 30초 이상 갱신되지 않으면 오프라인으로 간주합니다.

### 5.3 Streamlit UI 동작
- **온라인:** 상단 초록색 배너 노출 및 미션 명령 관련 UI 컴포넌트 활성화
- **오프라인:** 상단 적색 경고 배너 노출 및 명령 관련 UI 강제 비활성화(`disabled`). 과거 데이터 조회 및 분석 기능만 허용.
- **복구:** Realtime 구독을 통해 `is_online=TRUE` 상태 변화 감지 시 배너 자동 제거 및 UI 잠금 해제.

---

## 6. 시뮬레이션 세션 및 지도 버전 관리 (Session & Versioning)

세맨틱 버전 관리를 Unity 로직에 결합하고, 다중 "세이브 슬롯" 개념인 세션(Session)과 연동하여 자동화합니다.

### 6.1 활성 세션 동기화 (Active Session Sync)
- **세션 종속성:** 시뮬레이터는 현재 활성화된 세션(`is_active=TRUE`)에 종속되어 구동됩니다.
- **데이터 기록:** Unity 백엔드 로직은 시작 시(또는 실시간으로) Supabase에서 활성 `session_id`를 조회합니다. 이후 발생하는 모든 `INSERT` / `UPDATE` 트랜잭션(발견 노드 기록, 엣지 물리 피드백 전송 등)에는 해당 `session_id`를 필수적으로 포함하여 기록합니다.

### 6.2 버전과 세션의 관계
- **버전의 의미:** 맵 버전은 **현재 활성 세션 내부에서의 탐색 진행 차수**를 의미합니다. 세션(세이브 슬롯)이 완전히 다른 격리된 환경이라면, 버전은 그 환경 내에서의 누적된 변화량입니다.
- **마이너 버전 자동 상승:** 로봇이 탐험을 마치고 `BASE` 노드로 복귀했을 때, 현재 세션에서 새로 발견한 `DISCOVERED` 노드 또는 엣지가 1개 이상 존재하면 `map_metadata.map_version`을 자동으로 1단계 올립니다 (예: v1.0.0 $\rightarrow$ v1.1.0). 새로 발견된 노드/엣지의 `version_added` 필드에는 갱신된 버전이 기록됩니다.
- **메이저 버전 수동 상승:** 건물이 추가되는 등 지도의 근본적인 물리 구조가 변경될 때는 관리자가 수동으로 버전을 격상합니다.
- **구현 위치:** `Unity/Assets/Scripts/Data/MapVersionManager.cs`
- **Streamlit 연동:** 대시보드에 현재 지도 버전과 세션 이름을 표시하고, 필터링 기능을 제공합니다.

---

## 7. 서버 운영 모드 (Operation Modes)
GitHub Actions CI/CD 파이프라인(`.github/workflows/deploy-to-mac.yml`)을 통해 상시 가동되는 Mac Mini 환경에 맞게 구동 모드를 나눕니다.
- **GUI 모드:** 사용자 시연 시 Unity Editor 및 빌드 뷰어를 통해 시각적 피드백 제공
- **헤드리스 (Headless) 모드:** 평상시 백그라운드 구동 및 자원 절약을 위해 `-batchmode -nographics` 플래그로 렌더링 파이프라인을 비활성화한 채 내부 논리 연산만 수행

---

## 8. ROBO-Path Unity 시뮬레이터 검증 구조

### 8.1 핵심 원칙
코드 작성 후 "완성"이라고 판단하지 않습니다. 반드시 아래 검증 루프를 직접 실행하고 결과를 확인한 후에만 다음 단계로 넘어갑니다.

### 8.2 환경 정보
- **Unity 에디터 실행 경로 (Windows):** `"C:/Program Files/Unity/Hub/Editor/6000.4.11f1/Editor/Unity.exe"`
- **Unity 프로젝트 경로:** `[현재 작업 중인 ROBO-Path 저장소]/Unity/`
- **테스트 결과 출력 경로:** `[현재 작업 중인 ROBO-Path 저장소]/Unity/Logs/TestResults_Edit.xml` 및 `TestResults_Play.xml`
- **로그 출력 경로:** `[현재 작업 중인 ROBO-Path 저장소]/Unity/Logs/simulator.log`

### 8.3 AI 직접 실행 검증 루프
코드 작성 후 반드시 아래 순서를 따릅니다.

#### 1단계: EditMode 테스트 실행
터미널에서 아래 명령을 실행하고 `TestResults_Edit.xml`을 읽어 failed 항목이 0건인지 확인합니다.
```bat
"C:/Program Files/Unity/Hub/Editor/6000.4.11f1/Editor/Unity.exe" ^
  -batchmode ^
  -nographics ^
  -projectPath "[프로젝트 경로]/Unity" ^
  -runTests ^
  -testPlatform EditMode ^
  -testResults "[프로젝트 경로]/Unity/Logs/TestResults_Edit.xml" ^
  -quit
```

#### 2단계: PlayMode 테스트 실행
터미널에서 아래 명령을 실행하고 `TestResults_Play.xml`을 읽어 failed 항목이 0건인지 확인합니다.
```bat
"C:/Program Files/Unity/Hub/Editor/6000.4.11f1/Editor/Unity.exe" ^
  -batchmode ^
  -nographics ^
  -projectPath "[프로젝트 경로]/Unity" ^
  -runTests ^
  -testPlatform PlayMode ^
  -testResults "[프로젝트 경로]/Unity/Logs/TestResults_Play.xml" ^
  -quit
```

#### 3단계: 시뮬레이터 헤드리스 실행
터미널에서 아래 명령을 실행하여 30초간 시뮬레이션을 실행하고, `simulator.log`를 확인하여 오류 여부와 로그 정상 출력(이동, Raycast, Supabase 전송)을 검증합니다.
```bat
"C:/Program Files/Unity/Hub/Editor/6000.4.11f1/Editor/Unity.exe" ^
  -batchmode ^
  -nographics ^
  -projectPath "[프로젝트 경로]/Unity" ^
  -executeMethod SimulatorValidator.RunValidation ^
  -logFile "[프로젝트 경로]/Unity/Logs/simulator.log" ^
  -quit
```

#### 4단계: Supabase 데이터 검증
터미널에서 `python scripts/validate_simulation.py`를 실행하여 Supabase의 `simulation_logs` 테이블 레코드를 조회하고 피드백 이상값 및 적재 여부를 확인합니다.

### 8.4 테스트 코드 구조
- **EditMode 테스트 (`Unity/Assets/Tests/EditMode/`)**
  1. `CostCalculatorTests.cs` (부하율, 비용 계산식, 범위 검증)
  2. `NodeValidationTests.cs` (노드 좌표 및 엣지 거리 무결성 검증)
  3. `RaycastConfigTests.cs` (Ray 개수, 범위, 각도 검증)
- **PlayMode 테스트 (`Unity/Assets/Tests/PlayMode/`)**
  1. `RobotMovementTests.cs` (플랫폼별 목적지 이동 및 계단 통과 제약 등 검증)
  2. `RaycastScannerTests.cs` (오브젝트 감지 및 `DISCOVERED` 전환 검증)
  3. `DataPipelineTests.cs` (브릿지 호출 및 데이터 전송 검증)
- **SimulatorValidator (`Unity/Assets/Scripts/Debug/SimulatorValidator.cs`)**
  - 헤드리스 실행용 엔트리포인트 (`-executeMethod`로 호출)

### 8.5 단계별 검증 의무 (Validation Checklist)
- **Step 1 (초기 설정):** EditMode 테스트 전체 통과 확인
- **Step 2 (맵 제작):** EditMode `NodeValidationTests` 통과 및 헤드리스 맵 로드 성공 확인
- **Step 3 (로봇 구현):** PlayMode `RobotMovementTests`, `RaycastScannerTests` 통과 및 헤드리스 탐색/이동 로그 확인
- **Step 4 (파이프라인):** PlayMode `DataPipelineTests` 통과 및 `validate_simulation.py` 통과 확인
- **Step 5 (배포 설정):** 맥미니 헤드리스 `simulator.log` 확인 및 `validate_simulation.py` 통과 확인
- **Step 6 (UI 업데이트):** 대시보드 `DISCOVERED` 노드 및 A* 경로 시각화 확인
