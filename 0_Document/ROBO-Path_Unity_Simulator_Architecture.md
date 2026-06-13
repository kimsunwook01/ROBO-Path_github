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
- **효율성 지수 ($E$):** 예상 이동시간 대비 실제 소요 시간 비율 (최대 1.0)

---

## 4. 양방향 통신 네트워크 아키텍처

로봇의 자율 주행 명령과 시뮬레이션 피드백 결과는 라즈베리파이 에지 서버(Streamlit)와 Mac Mini 시뮬레이터 간에 외부 의존성을 최소화한 클린 아키텍처 구조로 실시간 동기화됩니다.

### 4.1 명령 하달 (사용자 $\rightarrow$ 시뮬레이터)
Streamlit 관제 UI에서 조작한 명령은 라즈베리파이를 거쳐 Unity로 즉각 전송됩니다.
- **클라이언트 (라즈베리파이):** `src/presentation/ros2_bridge/bridge.py` 스크립트가 WebSocket 클라이언트 모듈로 동작합니다.
- **서버 (Mac Mini):** Unity에 내장된 WebSocket 서버 (`Unity/Assets/Scripts/Network/WebSocketServer.cs`)
- **통신 포트:** `.env`의 `SIMULATOR_WS_PORT` (기본값: 8765) 활용, IP는 `SIMULATOR_HOST` 활용.
- **JSON 메시지 규격 예시:**
  ```json
  {
    "type": "set_destination",
    "robot_id": "robot_alpha",
    "platform": "wheeled",
    "target_node_id": "uuid-xxxx"
  }
  ```

### 4.2 피드백 업로드 및 UI 갱신 (시뮬레이터 $\rightarrow$ 사용자)
시뮬레이터에서 연산된 성적은 DB에 기록되고, 사용자의 브라우저 화면에 마법처럼 실시간 반영됩니다.
- **프로세스 브릿지 호출:** Unity 내의 C# 스크립트는 엣지 통과 이벤트를 JSON으로 직렬화한 후 `System.Diagnostics.Process`를 통해 Python 서브프로세스(`src/infrastructure/bridge/bridge.py`)를 호출합니다.
- **DB 적재:** 호출된 Python 프로세스가 `.env`에서 `SUPABASE_URL`, `SUPABASE_KEY`를 로드하고 Supabase Python SDK를 통해 데이터를 즉시 INSERT/UPDATE 합니다.
- **UI 자동 동기화:** 라즈베리파이의 Streamlit 앱(`app.py`)은 **Supabase Realtime** 기능을 구독하고 있으므로, DB의 레코드가 변경되는 순간 별도의 API 호출 없이 지도의 노드 및 엣지 피드백 정보가 자동 갱신됩니다.

---

## 5. 서버 운영 모드 (Operation Modes)
GitHub Actions CI/CD 파이프라인(`.github/workflows/deploy-to-mac.yml`)을 통해 상시 가동되는 Mac Mini 환경에 맞게 구동 모드를 나눕니다.
- **GUI 모드:** 사용자 시연 시 Unity Editor 및 빌드 뷰어를 통해 시각적 피드백 제공
- **헤드리스 (Headless) 모드:** 평상시 백그라운드 구동 및 자원 절약을 위해 `-batchmode -nographics` 플래그로 렌더링 파이프라인을 비활성화한 채 내부 논리 연산만 수행

---

## 6. ROBO-Path Unity 시뮬레이터 검증 구조

### 6.1 핵심 원칙
코드 작성 후 "완성"이라고 판단하지 않습니다. 반드시 아래 검증 루프를 직접 실행하고 결과를 확인한 후에만 다음 단계로 넘어갑니다.

### 6.2 환경 정보
- **Unity 에디터 실행 경로 (Windows):** `"C:/Program Files/Unity/Hub/Editor/6000.4.11f1/Editor/Unity.exe"`
- **Unity 프로젝트 경로:** `[현재 작업 중인 ROBO-Path 저장소]/Unity/`
- **테스트 결과 출력 경로:** `[현재 작업 중인 ROBO-Path 저장소]/Unity/Logs/TestResults_Edit.xml` 및 `TestResults_Play.xml`
- **로그 출력 경로:** `[현재 작업 중인 ROBO-Path 저장소]/Unity/Logs/simulator.log`

### 6.3 AI 직접 실행 검증 루프
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

### 6.4 테스트 코드 구조
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

### 6.5 단계별 검증 의무 (Validation Checklist)
- **Step 1 (초기 설정):** EditMode 테스트 전체 통과 확인
- **Step 2 (맵 제작):** EditMode `NodeValidationTests` 통과 및 헤드리스 맵 로드 성공 확인
- **Step 3 (로봇 구현):** PlayMode `RobotMovementTests`, `RaycastScannerTests` 통과 및 헤드리스 탐색/이동 로그 확인
- **Step 4 (파이프라인):** PlayMode `DataPipelineTests` 통과 및 `validate_simulation.py` 통과 확인
- **Step 5 (배포 설정):** 맥미니 헤드리스 `simulator.log` 확인 및 `validate_simulation.py` 통과 확인
- **Step 6 (UI 업데이트):** 대시보드 `DISCOVERED` 노드 및 A* 경로 시각화 확인
