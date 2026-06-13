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
