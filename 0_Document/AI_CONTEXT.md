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
- [ ] **7. Unity 시뮬레이터 연동 및 구축 (`Unity/`)**
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
  - [ ] [Phase 4] Unity 내장 WebSocket 서버(`WebSocketServer.cs`) 및 C# Python 브릿지(Supabase 적재) 로직 작성
  - [ ] [Phase 5] macOS 환경 GitHub Actions 자동 배포 파이프라인 구축
- [ ] **8. 관제 대시보드 UI 및 통신 브릿지 구축 (`src/presentation/`)**
  - [x] [Phase 1] Supabase-Streamlit 데이터 연동 검증 및 테이블 출력 (`app.py`) - **완료**
  - [ ] [Phase 2] Streamlit $\rightarrow$ Unity 통신용 Python WebSocket 클라이언트(`ros2_bridge/bridge.py`) 작성
  - [ ] [Phase 3] Plotly 2D 지도 시각화 (BASE, DISCOVERED 노드 및 로봇 현재 위치)
  - [ ] [Phase 4] A* 경로 탐색 UI (플랫폼 선택, 출발지/목적지, 경로 하이라이트 및 시뮬레이션 명령 송신)
  - [ ] [Phase 5] Supabase Realtime 구독으로 지도 실시간 업데이트
- [x] **9. 에지 서버(라즈베리파이) 인프라 구현 (`src/infrastructure/storage/`)**
  - [x] GitHub Actions CI/CD 구축, SSD 마운트, FastAPI 구현, Systemd/Nginx 세팅 완료

> **Update Rule:** 이 파일은 프로젝트의 주요 마일스톤이 달성되거나 아키텍처 정책이 변경될 때마다 AI에 의해 갱신되어야 합니다.
