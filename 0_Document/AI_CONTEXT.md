# 🤖 AI Context & Project Status Reference

이 문서는 AI 어시스턴트가 프로젝트의 컨텍스트를 기억 상실 없이 명확히 인지하고, 일관된 방향으로 코딩 및 아키텍처 설계를 이어나가기 위한 **상태 요약 및 지침서**입니다. 
> **AI Instruction:** 새로운 대화 세션을 시작하거나 구조적인 코드를 작성하기 전에 반드시 이 문서를 최우선으로 읽고 지침을 따르세요.

---

## 1. 프로젝트 요약 (Project Overview)
- **프로젝트명:** ROBO-Path (로봇 기종별 하드웨어 피드백 기반 입체 주행 경험 데이터베이스)
- **목표:** 정적인 2D 지도를 넘어, 플랫폼(바퀴형/보행형)의 실제 물리적 주행 피드백(부하율, 안정성 등)을 가중치로 반영하는 최적 경로 탐색 시스템 구축
- **핵심 기술 스택:** Python 3.10+, Supabase (PostgreSQL DB), Streamlit (UI), Google Gemini API (자연어 피드백), Unity 6.4 (3D 시뮬레이터), C# (제어 브릿지)

## 2. 핵심 아키텍처 및 코딩 원칙 (Core Principles)

본 프로젝트는 "바이브 코딩"으로 인한 스파게티 코드를 방지하기 위해 엄격한 **클린 아키텍처(Clean Architecture)**를 따릅니다.

- **인프라 분산 구조 (3-Tier):** 
  1. Mac Mini M2 Pro (Unity 시뮬레이터 구동 및 Raycast 탐색 연산)
  2. Raspberry Pi 5 (대용량 파일 스토리지 및 관제 대시보드 호스팅)
  3. Supabase (경량화 메타데이터 및 지표 통계 클라우드 DB)
- **🚨 AI가 코딩 시 절대 준수해야 할 규칙:**
  1. **의존성 방향:** `domain` 계층은 절대 외부 라이브러리(DB 클라이언트, Streamlit 등)를 `import`해서는 안 됩니다. 순수 파이썬 로직만 존재해야 합니다.
  2. **의존성 주입 (DI):** DB 통신 로직은 `infrastructure` 계층에 작성하고, 인터페이스(Protocol)를 통해 `application` 계층에 주입하여 결합도를 낮춰야 합니다.
  3. **데이터 검증:** 모든 DB 삽입 전후에는 반드시 `Pydantic` 클래스를 통해 타입 및 값의 무결성을 검증해야 합니다.

### 2.1 고정 문서 관리 규칙 (Frozen Documents)
다음 문서는 특정 시점의 설계 스냅샷을 영구 보존하기 위해 **고정(Frozen)** 처리되었습니다.
- **`0_Document/ROBO-Path_Migration_Decision_Report.md`**
> **AI 지시사항:** 문서 최신화, 일괄 용어 수정, 구조 정리, 내용 갱신 등 어떠한 문서 수정 지시가 있더라도 위 고정 문서들은 항상 대상에서 **제외**하십시오. 현재 프로젝트 구조와 불일치하는 내용이 발견되더라도 당시의 맥락 보존을 위해 절대로 수정하지 마십시오.

### 2.2 Git 커밋 표준 절차 (Standard Commit Procedure)
Unity 기반 프로젝트에서 에셋 누락을 방지하기 위해 매 커밋 시 다음 절차를 반드시 따릅니다.
1. **산출물 생성 완료 확인 (Wait & Check):** Unity `-batchmode` 등의 실행 후 고정 시간에 의존하지 않고, `git status`를 짧게 반복 확인하여 기대한 산출물(`.meta`, `.asset`, `scene_dump.json` 등)이 모두 기록되었는지 검증합니다.
2. **포괄적 Staging (Add):** 디렉토리 단위 포괄 `git add`를 사용하여 `.meta` 파일 누락을 방지합니다.
3. **Amend 절대 금지 (No Amend):** 어떠한 경우에도 `git commit --amend`를 사용하지 않습니다. 뒤늦게 발견된 누락본은 `FIX: 누락본 추가` 형태의 후속 일반 커밋으로 처리합니다.
4. **사후 검증 (Post-Commit Check):** 커밋 직후 `git status`를 실행하여 Working Tree가 완전히 `clean`한 지 확인합니다. `clean` 상태가 아니라면 남은 파일을 후속 커밋으로 처리하고, `clean`이 될 때까지 반복합니다.

### 2.3 Unity 변경사항 처리 원칙 (Unity Change Handling Rules)
Unity 기반 작업 중 의도치 않은 파일 변경이 발생하여 사용자의 씬 작업물이 소실되는 사고를 방지하기 위해 다음 원칙을 절대 준수합니다.

1. **임의 삭제/되돌리기 금지 + 보고 의무:**
   - 작업 중 `git status`에 예정에 없던 변경/생성 파일(특히 Unity 관련: `Assets/`, `ProjectSettings/`, `Packages/` 등)이 발견되면, `git restore` / `git checkout` / 파일 삭제 등으로 임의 처리하지 마십시오.
   - 대신 그 파일 목록과 성격을 사용자에게 보고하고, 어떻게 처리할지(커밋할지, 무시할지, 그대로 둘지) 사용자의 판단을 기다려야 합니다.
   - 특히 `git restore "Unity/"` 처럼 광범위한 경로를 한 번에 되돌리는 명령은 **절대 사용하지 않습니다.** 커밋되지 않은 사용자의 수동 작업물(씬 등)이 영구 소실될 수 있습니다.

2. **씬/작업물 보존:**
   - `.unity` 씬 파일 등 사용자 작업물은 변경이 감지되면 임의로 되돌리지 말고 보존을 최우선으로 합니다.
   - 사용자가 Unity 작업을 했다고 하면, 관련 `.unity` 파일이 커밋되었는지 `git status`로 확인하고, 누락되어 있으면 사용자에게 알려 커밋하도록 안내합니다.

3. **잡음 파일과 작업물의 구분:**
   - Unity 자동생성 파일(캐시, 세션 설정 등)이 잡음으로 반복해서 뜨는 경우, 임의로 지우지 말고 `.gitignore` 정비를 사용자에게 제안합니다. (직접 `.gitignore`를 고치는 것도 사용자 승인 후에 진행합니다.)
## 3. 관련 문서 링크 (Related Documents)
자세한 기술 명세가 필요할 경우 아래 문서들을 참조하세요.
- (고정) 설계 전환 의사결정 기록: `0_Document/ROBO-Path_Migration_Decision_Report.md`
- 전체 기획 및 분산 처리 명세: `0_Document/ROBO-Path_Design_Report.md`
- 데이터베이스 ERD 및 DDL 스키마: `0_Document/ROBO-Path_Supabase_DB_Architecture.md`
- 폴더 구조 및 계층별 분리 전략: `0_Document/ROBO-Path_Software_Architecture.md`
- 대시보드 연동 기획(Streamlit): `0_Document/ROBO-Path_Streamlit_Dashboard_Plan.md`
- 애플리케이션 서비스 계층 설계: `0_Document/ROBO-Path_Application_Service_Layer.md`
- LLM 기반 피드백 지식화 파이프라인 설계: `0_Document/ROBO-Path_LLM_Pipeline_Design.md`
- 맵 설계 및 비용 프로파일 명세: `0_Document/ROBO-Path_Map_Design_Specification.md`
- 씬 덤프 도구 명세: `0_Document/ROBO-Path_Scene_Dump_Specification.md`
- 맵 에디터 도구 설계: `0_Document/ROBO-Path_Map_Editor_Tool_Design.md`
---

## 4. 진행 상황 타임라인 (Current Status & Next Steps)

**✅ [완료된 작업]**
- [x] 프로젝트 초기 요구사항 분석 및 방향성 수립
- [x] .env 파일 추적 해제 및 Git 기초 설정 완료
- [x] 클린 아키텍처 기반의 4계층(`domain`, `application`, `infrastructure`, `presentation`) 폴더 구조 세팅
- [x] Supabase 클라우드 데이터베이스 초기 DDL 및 스키마 설계 완료
- [x] Supabase 초기화용 마이그레이션 SQL 코드(`supabase/migrations/...`) 작성 및 로컬 Git 커밋 완료
- [x] **DB 구축 및 연동:** Supabase 콘솔에서 프로젝트 생성 후 GitHub Actions 기반의 마이그레이션 자동 배포 파이프라인 구축 완료
- [x] 모든 테이블에 대한 Row Level Security (RLS) 활성화 및 익명 읽기 허용 정책 마이그레이션 SQL 코드 작성 완료
- [x] **2. 핵심 도메인 모델 작성 (`src/domain/models/`)**
  - `MapMetadata`, `Robot`, `Node` 계층, `Edge`, `MissionLog`, `Incident` 등 Pydantic 기반 무결성 검증 모델 작성 완료
- [x] **3. Supabase Client 및 의존성 주입 구조 설계 (`src/infrastructure/`, `src/application/`)**
  - Supabase 연결 싱글톤 클라이언트, Repository 통신 규약(Protocol), Supabase용 Repository 구현체 작성 완료
- [x] **4. 순수 도메인 알고리즘 설계 및 구현 (`src/domain/algorithms/`)**
  - 플랫폼 가중치 기반 Edge Cost 산출, A* 경로 탐색, 하드웨어 피드백 통계 누적(Aggregation) 로직 구현 완료
- [x] **DB 휴면 방지:** Supabase 무료 요금제 휴면 방지를 위한 더미 테이블(`sleep_prevention_table`) 추가 및 GitHub Actions 기반 3일 주기 자동 Ping 파이프라인 구축 완료

**🚀 [현재 대기 중인 작업 (Next Action)]**
- [x] **5. 애플리케이션 서비스 계층 구현 (`src/application/services/`)**
  - [x] 도메인 알고리즘(A*)과 인프라(Repository)를 연결하여 경로를 탐색하는 `PathPlanningService` 작성
  - [x] 주행 로그가 삽입되면 엣지 통계를 갱신하는 `FeedbackAggregationService` 작성
- [x] **6. LLM 기반 피드백 지식화 파이프라인 (`src/infrastructure/llm/`)**
  - [x] Google Gemini API 연동 모듈 작성 (자연어 피드백 -> 구조화된 JSON)
  - [~] **런타임 통합 보류 (2026-06-19 결정):** 모듈(`gemini_client.py`) 작성까지만 완료하고, 런타임 연동(incidents 적재 + 대시보드 분석 UI + 엣지 페널티 환류)은 **현재 구현 범위에서 의도적으로 제외**한다. 본 프로젝트에서 LLM 파이프라인의 구현 우선순위가 낮다고 판단한 결정이며, 추후 우선순위가 재조정될 경우 재개한다.
- [x] **7. Unity 시뮬레이터 연동 및 구축 (`Unity/`)** — Phase 1~5 전부 완료(맵/로봇/통신 브릿지/피드백 루프 + macOS 자동 배포 파이프라인)
  - [x] [Phase 1] Unity 프로젝트 생성 및 GitHub 연동 (.gitignore 설정)
  - [x] [Phase 2] 메인 캠퍼스 맵 제작 및 파이프라인 구축 완료
    - [x] 블록 프리팹 25종(평지/경사/계단/차도/차도경사 × 높이 5) 및 타일 5종(거점3/횡단보도/장애물) 제작 완료
    - [x] 맵 에디터 도구 구현 및 검증 완료 (격자 배치/적층/회전/삭제/선택, 동적 팔레트)
    - [x] 대규모 메인 맵 제작 완료 (약 3162블록 규모, 88m 고저차, 거점/타일 배치, NavMesh 베이크 완료)
    - [x] 씬 덤프 개편 완료 (고유 ID 체계 도입, overlay_tiles 섹션 분리, covers_block_id 매핑) - A* 그래프 변환용 고품질 데이터 확보
  - [x] [Phase 3] 로봇 2종(Wheeled/Legged) 구현 및 테스트 완료
    - [x] [Phase 3a] 로봇 프리팹 2종 구현 완료 (Robot_Wheeled, Robot_Legged)
      - NavMeshAgent(radius 0.5), Rigidbody(kinematic), BoxCollider, RobotIdentify 컴포넌트 구성
      - Robot 레이어 분리, SensorOrigin 계층구조
    - [x] [Phase 3a] RobotSpawner 구현 완료 (Node_Station 기반 자동 배치, NavMesh.SamplePosition + Warp)
    - [x] [Phase 3a] RobotController 구현 완료
      - NavMesh 경로 탐색 + ValidatePath (Wheeled의 Path_Stair 태그 거부)
      - **부분 경로(PathPartial) 거부** — 도달 불가 목적지로의 부분 주행 방지
      - 수동/자동 모드 전환, manualInterventionOccurred 플래그
    - [x] [Phase 3a] RaycastScanner 구현 완료 (180° 팬 스캔, Robot 레이어 제외, ITelemetrySink 연동)
    - [x] [Phase 3a] FeedbackCalculator 구현 완료
      - **Newtonsoft.Json(JObject)** 기반 JSON 파싱 (정규식/IndexOf 제거)
      - 플랫폼(wheeled/legged) + 지형 태그로 정확 lookup
      - null L/S/E 및 traversable=false 안전 처리, 노이즈 주입(INoiseGenerator DI)
      - 저장소 루트 `config/cost_profiles.json` 직접 읽기 (단일 원본 원칙)
    - [x] [Phase 3a] LogTelemetrySink 구현 완료 (ITelemetrySink 인터페이스, 피드백/발견 이벤트 로깅)
    - [x] [Phase 3a] 테스트 전체 통과 (EditMode 6/6 + PlayMode 6/6 = 12/12, Failed 0)
      - EditMode: FeedbackCalculator 3종 + Phase3a 프리팹 검증 2종 + 기본 1종
      - PlayMode: Spawner NavMesh 스냅 / RaycastScanner 발견 / 경로 거부(태그) / 부분 경로 거부 / 플래그 리셋 / 기본 1종
    - [x] [Phase 3b] 백엔드 그래프 연결 (덤프 맵 데이터 → DB `map_edges` 및 Graph 객체 변환)
      - [x] STEP 1: DB Repository에 `upsert_nodes`, `upsert_edges` 배치 처리 기능 추가
      - [x] STEP 2: `MapImportService` 구현 (scene_dump.json 파싱 및 도메인 객체 변환)
      - [x] STEP 3: CLI 실행 스크립트 `import_map_dump.py` 작성
      - [x] STEP 4: Mock JSON을 활용한 단위 테스트 검증 (Failed 0)
      - 관련 명세: `0_Document/ROBO-Path_Phase3b_Graph_DB_Import_Spec.md`
    - [x] [Phase 3c] `HazardTileController` 구현 완료 — Tile_Hazard 활성/비활성 상태 전환 및 투명화 기능
      - `Assets/Scripts/Tile/HazardTileController.cs` 신규 작성 (ROBOPath.Tile 어셈블리)
      - `startActive = false` 기본값 → 비활성 시 MeshRenderer 비표시, Collider 유지(NavMesh 통행 허용)
      - Lazy 초기화(`MeshRend` property) — EditMode 테스트 환경 호환
      - `public void SetHazardActive(bool)` API 노출 → Phase 4 WebSocket 연동 시 호출
      - `Tile_Hazard.prefab`에 컴포넌트 부착 완료
      - EditMode 테스트 4개 추가 (비표시/표시/토글/Collider 유지)
      - **테스트 현황: EditMode 10/10 + PlayMode 7/7 = 총 17개, Failed 0**
  - [x] [Phase 4] Unity 통신 브릿지 (명령: WebSocket 수신, 피드백: Subprocess 송신 - 3-Way Bridge 아키텍처 적용)
    - [x] [STEP 1] Unity 명령 수신 서버 (`Network/WebSocketServer.cs`) — HAZARD_TOGGLE / ASSIGN_MISSION 처리. (명세는 WebSocket이었으나 실제 구현은 HTTP POST(HttpListener)로 단순화 — 클래스명만 WebSocketServer 유지)
    - [x] [STEP 2] Python→Unity 명령 송신 브릿지 (`ros2_bridge/bridge.py`, HTTP POST) + `MissionAssignmentService` 연동 (A* 경로 → 웨이포인트 송신)
    - [x] [STEP 3] Unity 피드백 송신 Sink (`Network/SubprocessTelemetrySink.cs`) — 도착/발견 시 `push_feedback.py` 서브프로세스 호출
    - [x] [STEP 4] 피드백 파이프라인 (Unity $\rightarrow$ Python Subprocess $\rightarrow$ Supabase) 기반 확립 (`push_feedback.py`) — FEEDBACK/DISCOVERY 분기, 엣지 매핑+폴백, 연속 임무 재배정
    - [x] RLS(Row Level Security) 쓰기 권한 우회를 위한 `service_role` 클라이언트 적용
  - [x] [Phase 5] macOS 환경 GitHub Actions 자동 배포 파이프라인 구축 (완료 2026-06-19, 실 Mac 러너 등록 + 전 구간 자동 배포 GREEN 검증 완료)
    - [x] `.github/workflows/deploy-to-mac.yml` 작성 (runs-on [self-hosted, macOS, ARM64], 코드 pull → Secrets .env → conda 의존성+pytest 게이트 → launchd 설치 → kickstart -k 재시작 → 리포트)
    - [x] `scripts/run_simulator.sh` (헤드리스 Unity 실행; launchd supervise 위해 `&` 대신 `exec` 포그라운드 실행). **`ROBOPATH_PYTHON` 절대경로 export 추가** — SubprocessTelemetrySink 의 파이썬 경로 추정이 Windows 전용(USERPROFILE/python.exe)이라 Mac 에서 피드백 서브프로세스가 실패하던 문제를 C# 1순위 오버라이드 환경변수로 해결.
    - [x] `config/mac_services/com.robopath.simulator.plist` (사용자 LaunchAgent, KeepAlive, __HOME__ 치환 템플릿 — sudo 불필요). EnvironmentVariables 에 ROBOPATH_ROOT/ROBOPATH_PYTHON 주입.
    - [x] Unity 헤드리스 진입점 `SimulatorLauncher.RunHeadless` (Debug/Editor, CampusMainMap 로드 → delayCall EnterPlaymode)
    - [x] 러너 라벨 충돌 방지: 기존 `deploy-to-pi.yml` 의 runs-on 을 [self-hosted, Linux, ARM64] 로 분리
    - [x] **(실 Mac) 환경 구축·검증 완료:** conda `robopath`(py3.12) 생성 + `pytest tests/` 42 passed/1 skipped, Unity 6000.4.11f1 + Mac Build Support(IL2CPP) 설치, 헤드리스 플레이모드 실동작 확인(RunHeadless→씬 로드→플레이), 피드백 루프 E2E 확인(`push_feedback.log` Supabase 200 OK + DISCOVERY 처리)
    - [x] **(실 Mac) self-hosted runner 등록** — `self-hosted, macOS, ARM64` 라벨, `svc.sh` 사용자 LaunchAgent 서비스로 상시 구동(로그인 세션 필요)
    - [x] **(실 Mac) GitHub Secrets 설정** — SUPABASE_URL/KEY/SERVICE_KEY 3개로 충분. GEMINI_API_KEY/EDGE_SERVER_URL 은 미생성(없는 secret 참조 시 빈 문자열 치환 → LLM 미사용·Pi 미연동이라 무해)
    - [x] **launchd 재시작 멱등화 (deploy 핵심 버그픽스):** 이미 로드된 에이전트를 다시 bootstrap 하면 `Bootstrap failed: 5: Input/output error` 로 단계가 깨지던 문제 → bootout/bootstrap/kickstart 를 모두 `|| true` 로 감싸고 `kickstart -k` 가 실제 재시작을 담당, 마지막에 `launchctl print` 로 로드 여부만 검증하도록 변경
    - [x] **전 구간 자동 배포 GREEN 확인** — main push → 러너 자동 pull → Secrets .env 생성 → pytest 게이트 통과 → launchd 설치 → 헤드리스 시뮬레이터 재시작까지 Actions 전 단계 성공
- [ ] **8. 관제 대시보드 UI 및 통신 브릿지 구축 (`src/presentation/`)**
  - [x] Data Contract 정의 (`ROBO-Path_Dashboard_Data_Contract.md`)
  - [x] Streamlit 관제 대시보드 1차 UI 목업 구현 (`app.py`, 3분할 독립 스크롤 레이아웃 및 토글 기능 완성)
  - [x] [Spec A] 임무 시스템 (Pickup $\rightarrow$ Delivery) 및 목적지 자동 배정 로직 구현 — 웨이포인트 내비게이션 + 연속 주행 루프 (커밋 `e48273c`)
  - [x] [Spec B] 로봇 상태/배터리 모델링 및 `robots` DB 동기화 — 지형별 배터리 소모, 상태 변경 시점 갱신 (커밋 `6300915`)
  - [x] [Spec C] Discovery 텔레메트리 파이프라인(Raycast 탐색 결과 $\rightarrow$ `nodes.is_discovered`) 연동 — HashSet 중복 제거, 일반 타일 발견 (커밋 `d2705bc`)
  - [x] [Spec D] 대시보드 Mock 데이터를 실제 Supabase 쿼리로 교체 (DB 연동) — get_robots/get_fleet_breakdown/get_missions(robots 조인)/get_simulator_status (커밋 `9be3b08`)
  - [x] [Spec E] Streamlit $\rightarrow$ Unity 통신용 Python WebSocket 클라이언트(`ros2_bridge/bridge.py`) 및 실시간 명령 송신 — 임무 배정 명령 송신 동작 확인
  - [x] **[NavMesh 정합성] 휠 로봇 계단/도로 침범 문제 근본 해결 (A* 의도와 NavMesh 실주행 일치화)**
    - 배경: A* 경로 탐색과 Unity NavMeshAgent 의 실주행이 별개 시스템으로 동작 → A* 가 회피하도록 계산한 경로(계단/도로)를 NavMesh 가 무시하고 최단 경로로 가로지르는 문제 발견
    - [x] **A* 레벨 1 — cost_profiles 주입:** `cost_profile_loader.py`(신규)로 로봇 로딩 시 `config/cost_profiles.json`을 `robot.weight_profile["cost_profiles"]`에 주입. robots 테이블의 weight_profile 기본값이 '{}'라 계단 차단(traversable:false)이 무력화되던 문제 해결. `mission_assignment_service.py`에서 호출(push_feedback 자동 배정도 커버)
    - [x] **A* 레벨 2 — 덮인 블록(함정 평지) 제외:** `block_occlusion.py`(신규)로 같은 그리드 칸에서 위 블록과 맞붙어(gap≈0) 덮인 하부 블록을 A* 노드에서 제외. 명세 2장 '블록 윗면만 주행' 규칙 구현. 단 지붕/처마처럼 공중에 떠서(gap>0) 덮는 경우는 하부 주행면 보존. `map_import_service.py`에 연결. (계단 19개에 덮여있던 '함정 평지' 21개 제거, 그래프 연결성 100% 단일 컴포넌트 유지, 엣지 16.3만→9036개로 감소하여 A* 성능도 개선)
    - [x] **NavMesh 레벨 — Area 분리 (근본 해결):** NavMeshAgent 가 자체 경로 계산 시에도 A* 의도를 따르도록 NavMesh Area 의 비용/통행 구조를 A* 와 일치시킴. `StairNavMeshSetup.cs`(신규 Editor 도구)로 지형 프리팹에 NavMeshModifier 자동 부착:
      - **Stair Area:** 휠 로봇 `agent.areaMask`에서 완전 제외(통행 불가). 보행 로봇은 사용.
      - **Road Area (연석):** 휠 로봇 `agent.areaMask`에서 완전 제외(평지→도로 직접 진입 불가). 횡단보도 타일은 도로 위 +0.5m에 얹힌 블록이라 NavMesh 가 그 윗면을 별도 주행면(Road Area 아님)으로 굽기 때문에 휠 로봇도 횡단보도로는 건넘. 보행 로봇은 단차 극복 가능하므로 Road 비용 3만 부여.
      - **Ramp Area:** 경사를 평지와 구분해 NavMesh 가 인식하도록 분리(비용 1, 통행 영향 없음). 향후 대응용 사전 분리.
      - **Hazard Area:** `HazardTileController` 가 NavMeshObstacle carving 으로 활성 시 NavMesh 를 동적으로 도려내 통행 차단, 비활성 시 복원(에디터 재베이크 불필요).
    - [x] `RobotController.cs` 수정: `ApplyPlatformAreaMask()` 추가(Awake 호출), 도달 반경 8m→3.5m/5m 축소(칸 건너뛰고 대각선 질러가기 완화)
    - [x] **검증 완료(실제 플레이 테스트):** 휠 로봇이 계단/도로를 한 번도 침범하지 않고 횡단보도로만 도로를 건넘. 장애물 타일 활성/비활성에 따라 NavMesh 가 동적으로 길을 막거나 엶. 경사/장애물/도로가 각각 다른 색으로 베이크됨.
    - 비고: 횡단보도 없이 도로로만 둘러싸인 목적지(현재 맵엔 없음) 및 장애물로 모든 경로 차단 시 → 향후 임무 실패/재배정 로직으로 대응(맵이 올바르게 동작한 증거). 보행 로봇은 도로 통행 가능하므로 그런 목적지 전담 가능.
- [x] **9. 에지 서버(라즈베리파이) 인프라 구현 (`src/infrastructure/storage/`)**
  - [x] GitHub Actions CI/CD 구축, SSD 마운트, FastAPI 구현, Systemd/Nginx 세팅 완료

### ⚠️ 알려진 불일치 및 후속 정리 항목 (2026-06-19 코드베이스 전수 감사 기준)
프로젝트 전체 파일 열람 검사에서 발견된, 추후 정리가 필요한 항목들:
- **stale 테스트 (해결— 2026-06-19):** `tests/test_push_feedback.py` 정합화 완료. 감사 시점엔 1건만 stale로 판단했으나, 실제 실행 검증 결과 `push_feedback.py`의 로깅이 `StreamHandler(sys.stdout)`로 stdout에 찍히는데 어서션은 stderr를 보고 있어 4개 중 3개(invalid_json/ignore/missing_fields)가 실제로 깨져 있었고, DISCOVERY는 이제 정식 처리되어 과거 메시지가 폐기됨. 수정 내용: (1) 메시지 검사를 stdout+stderr 합산으로 전환, (2) DISCOVERY 정식 처리/unknown 무시 동작을 반영해 케이스 재작성, (3) 서브프로세스에 cwd/PYTHONPATH 주입으로 `from src...` 절대 임포트를 호출 환경과 무관하게 해결, (4) 실 DB 쓰기를 수반하는 해피패스는 `ROBOPATH_RUN_DB_TESTS` 옵트인으로 분리. 검증: 4 passed, 1 skipped.
- **중복 마이그레이션:** `supabase/migrations/`에 동일 타임스탬프(20260618030000) `add_discovery.sql`과 `add_discovery_columns.sql` 공존. 후자가 정본(컬럼 + `idx_nodes_xz` 인덱스). 전자의 고유분(거점 `is_discovered` UPDATE)은 `map_import_service.py`의 import-time `is_discovered=True`와 기능 중복. → `add_discovery.sql` 삭제 권장(단, 원격 DB 마이그레이션 히스토리 정합성 확인 후).
- **대시보드 맵 시각화:** `presentation/dashboard/app.py` 중앙 맵은 아직 랜덤 Plotly 목업이며 일부 텔레메트리(경과시간 등) 하드코딩. 데이터 계층(`mock_data.py`)은 실제 Supabase 연동 완료(Spec D). 맵 실연동은 후속 과제.
- **LLM 파이프라인 (런타임 통합 제외 — 2026-06-19 결정):** `infrastructure/llm/gemini_client.py` 모듈은 구현됐으나 런타임 연동(incidents 적재 + 대시보드 분석 UI)은 미연결. LLM_Pipeline_Design 명세 범위(모듈 작성)와는 일치한다. **런타임 통합은 구현 우선순위가 낮아 현재 범위에서 의도적으로 제외**되었으며, '후속 과제'가 아닌 보류(De-scoped) 상태로 둔다. 우선순위가 재조정되면 재개한다.

> **Update Rule:** 이 파일은 프로젝트의 주요 마일스톤이 달성되거나 아키텍처 정책이 변경될 때마다 AI에 의해 갱신되어야 합니다.