# ROBO-Path

### 로봇 기종별 하드웨어 피드백 기반 입체(3D) 주행 경로탐색 시스템

> 정적인 2D 지도를 넘어, 플랫폼(바퀴형/보행형)의 **실제 물리적 주행 피드백**(부하율·안정성·효율성)을 비용 가중치로 환류하여 *기종별 최적 경로*를 탐색하는, 경험 기반 자율주행 경로 데이터베이스.

`Python 3.10+` · `Supabase (PostgreSQL)` · `Streamlit` · `Unity 6.4 (C#)` · `FastAPI` · `GitHub Actions CI/CD`

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [핵심 아이디어](#2-핵심-아이디어)
3. [시스템 아키텍처](#3-시스템-아키텍처)
4. [기술 스택](#4-기술-스택)
5. [소프트웨어 설계 — 클린 아키텍처](#5-소프트웨어-설계--클린-아키텍처)
6. [주요 구성요소](#6-주요-구성요소)
7. [데이터 모델](#7-데이터-모델)
8. [디렉토리 구조](#8-디렉토리-구조)
9. [설치 및 실행](#9-설치-및-실행)
10. [배포 (CI/CD)](#10-배포-cicd)
11. [시뮬레이션 운영 방법](#11-시뮬레이션-운영-방법)
12. [결과 및 의의](#12-결과-및-의의)
13. [알려진 한계 및 향후 과제](#13-알려진-한계-및-향후-과제)
14. [관련 문서](#14-관련-문서)

---

## 1. 프로젝트 개요

**ROBO-Path**는 캠퍼스와 같은 입체 환경에서 로봇의 **하드웨어 특성(바퀴형 vs 보행형)** 에 따라 달라지는 주행 난이도를 경로 탐색에 반영하는 시스템이다.

기존의 단순 거리/시간 기반 경로 탐색은 "어떤 로봇이 가느냐"를 고려하지 않는다. 그러나 현실에서는 동일한 경로라도 바퀴형 로봇에게 계단은 통행 불가이고 경사는 큰 부하이며, 보행형 로봇은 계단을 오를 수 있지만 평지 주행 효율은 떨어진다. ROBO-Path는 이러한 **플랫폼별 물리 피드백을 정량 지표(부하율·안정성·효율성)로 측정**하고, 이를 그래프의 간선 비용에 누적 반영하여 *기종에 최적화된 경로*를 산출한다.

- **프로젝트명:** ROBO-Path (로봇 기종별 하드웨어 피드백 기반 입체 주행 경험 데이터베이스)
- **목표:** 플랫폼의 실제 주행 피드백을 가중치로 반영하는 최적 경로 탐색 시스템 구축
- **검증 환경:** Unity 6.4 기반 3D 가상 캠퍼스(약 3,200개 주행 노드, 88m 고저차)에서 바퀴형·보행형 로봇이 자율 임무를 수행하며 데이터를 축적

---

## 2. 핵심 아이디어

```
         [정적 지도]                          [ROBO-Path: 경험 기반 지도]
   거리만 보고 최단경로 선택          플랫폼별 물리 피드백을 비용에 반영한 경로 선택

   A ──5── B ──5── C                  A ──(휠:5)── B ──(휠:∞ 계단)── C
        \________/                         \____(휠:8 경사)________/
          (10)                                  ⇒ 휠 로봇은 경사 우회로 선택
                                                ⇒ 보행 로봇은 계단 직진 선택
```

1. **측정(Measure):** Unity 시뮬레이터에서 로봇이 한 구간(segment)을 주행할 때마다 부하율(Load)·안정성(Stability)·효율성(Efficiency)을 계산한다. 지형 태그(평지/경사/계단/차도 등)와 플랫폼에 따라 값이 달라지며, 현실성을 위해 노이즈가 주입된다.
2. **환류(Feedback):** 측정된 지표는 Python 브릿지를 통해 클라우드 DB에 적재되고, 해당 간선의 통계로 **누적(Aggregation)** 된다.
3. **탐색(Plan):** A* 경로 탐색이 누적된 플랫폼별 간선 비용을 사용하여 다음 임무의 경로를 계산한다. 측정 → 환류 → 탐색이 끊김 없이 반복되며 경로 품질이 경험적으로 정제된다.

---

## 3. 시스템 아키텍처

전기세 절감과 연산 효율화를 위해 **3-Tier 하이브리드 분산 구조**로 동작한다. 각 계층은 자신이 가장 잘하는 역할만 담당한다.

```
┌─────────────────────────────┐     명령(ASSIGN_MISSION, HTTP POST)
│   Mac Mini (M2 Pro)         │◀─────────────────────────────────────┐
│  · Unity 6.4 가상 캠퍼스    │                                       │
│  · NavMeshAgent 실주행      │     피드백(Subprocess 호출)            │
│  · Raycast 탐색 엔진        │──────────────┐                        │
│  · 헤드리스 자동 구동(launchd)             │                        │
└─────────────────────────────┘              ▼                        │
                                  ┌───────────────────────┐           │
                                  │  Python 코어 (브릿지) │───────────┘
                                  │  · A* 경로탐색        │
                                  │  · 임무 배정/재배정   │   읽기/쓰기
                                  │  · 피드백 통계 누적   │──────────────┐
                                  └───────────────────────┘              ▼
┌─────────────────────────────┐                          ┌──────────────────────────┐
│   Raspberry Pi 5            │   읽기(조회)             │  Supabase (PostgreSQL)   │
│  · Streamlit 관제 대시보드  │─────────────────────────▶│  · 노드/간선/로봇/임무   │
│  · FastAPI 스토리지(1TB SSD)│                          │  · 지표 통계 (RLS 적용)  │
│  · Nginx 리버스 프록시      │                          └──────────────────────────┘
└─────────────────────────────┘                                   ▲
       ▲                                                          │ 조회(공개)
       │ 웹 접속                                       ┌──────────────────────────┐
   [관리자/평가자]                                     │  Streamlit Community Cloud│
                                                       │  (공개 대시보드 미러)     │
                                                       └──────────────────────────┘
```

**데이터 흐름은 두 방향으로 분리된다.**

- **명령 경로 (Python → Unity):** A* 가 계산한 웨이포인트 경로를 HTTP POST(`ASSIGN_MISSION`)로 Unity의 수신 서버에 전달한다. Unity는 명령을 받아야만 로봇을 움직이는 **리스너**로 동작한다.
- **피드백 경로 (Unity → Python → DB):** 로봇이 구간을 주파(`FEEDBACK`)하거나 새 노드를 발견(`DISCOVERY`)하거나 목적지 도달에 실패(`MISSION_FAILED`)하면, Unity가 Python 서브프로세스(`push_feedback.py`)를 호출하여 DB에 반영하고 **다음 임무를 자동 재배정**한다.

---

## 4. 기술 스택

| 영역 | 기술 |
|------|------|
| 백엔드 코어 | Python 3.10+ (Pydantic 데이터 검증, 클린 아키텍처) |
| 시뮬레이터 | Unity 6.4 (6000.4.11f1), C#, NavMesh(AI Navigation), Newtonsoft.Json |
| 데이터베이스 | Supabase (PostgreSQL, PostgREST, Row Level Security) |
| 관제 대시보드 | Streamlit, Plotly |
| 엣지 스토리지 | FastAPI, Uvicorn, Nginx, systemd (Raspberry Pi 5) |
| CI/CD | GitHub Actions + Self-Hosted Runner (macOS / Linux-ARM64) |
| 경로 탐색 | A* (플랫폼 가중 간선 비용), 그래프 오클루전 프루닝 |

---

## 5. 소프트웨어 설계 — 클린 아키텍처

"바이브 코딩"으로 인한 스파게티 코드를 방지하기 위해 엄격한 **클린 아키텍처(Clean Architecture)** 4계층 구조를 따른다.

```
presentation  ─ 진입점/UI (Streamlit 대시보드, Python↔Unity 브릿지, CLI 스크립트)
     │ 의존
application   ─ Use Case / 서비스 (경로탐색·임무배정·피드백누적), Repository 인터페이스(Protocol)
     │ 의존
domain        ─ 순수 비즈니스 로직 (A* 알고리즘, Edge Cost 산출, Pydantic 모델) — 외부 의존 0
     ▲ 구현/주입
infrastructure ─ 외부 기술 구현체 (Supabase Repository, FastAPI Storage, LLM 클라이언트)
```

**절대 준수 규칙**

1. **의존성 방향:** `domain` 계층은 DB 클라이언트·Streamlit 등 외부 라이브러리를 절대 `import`하지 않는다. 순수 파이썬 로직만 존재한다.
2. **의존성 주입(DI):** DB 통신은 `infrastructure`에 구현하고, 인터페이스(Protocol)를 통해 `application`에 주입하여 결합도를 낮춘다.
3. **데이터 검증:** DB 입출력은 반드시 `src/domain/models`의 `Pydantic` 클래스를 통과해 타입·값 무결성을 검증한다.

---

## 6. 주요 구성요소

### 6.1 Unity 3D 시뮬레이터 (`Unity/`)

- **가상 캠퍼스 맵:** 블록 프리팹 25종(평지/경사/계단/차도/차도경사 × 높이 5단계)과 타일 5종(거점·횡단보도·장애물)으로 구성된 대규모 입체 맵(약 3,162블록, 88m 고저차). 전용 **맵 에디터 도구**(격자 배치/적층/회전/삭제, 동적 팔레트)로 제작.
- **로봇 2종:** 바퀴형(`Robot_Wheeled`)·보행형(`Robot_Legged`). NavMeshAgent, Kinematic Rigidbody, BoxCollider, `RobotIdentify` 컴포넌트로 구성. 운용 개체는 `Wheeled-01`, `Legged-01`~`Legged-04`.
- **Raycast 탐색 엔진:** 180° 팬 스캔으로 전방 노드를 발견(`DISCOVERY`)하여 지도를 점진적으로 밝힌다(Fog of War). 로봇 레이어는 스캔에서 제외하고 HashSet으로 중복을 제거한다.
- **장애물 타일(`HazardTileController`):** 기본 비활성. 활성 시 `NavMeshObstacle` carving으로 NavMesh를 동적으로 도려내 통행을 차단하고, 비활성 시 복원한다(에디터 재베이크 불필요).
- **헤드리스 자동 구동:** `SimulatorLauncher.RunHeadless`가 씬 로드 후 플레이모드로 진입하여, Mac에서 GUI 없이 launchd 서비스로 상시 구동된다.

### 6.2 경로 탐색 엔진 — A* with 플랫폼 가중 비용 (`src/domain/algorithms/`)

- 간선 비용은 **플랫폼별 비용 프로파일**(`config/cost_profiles.json`)과 누적 피드백 통계로 산출된다. 예: 바퀴형은 계단 통행 불가(`traversable:false`), 경사는 고비용.
- **그래프 오클루전 프루닝(`block_occlusion.py`):** 위 블록과 맞붙어 덮인 하부 '함정 평지' 타일을 A* 노드에서 제외하여 "블록 윗면만 주행" 규칙을 강제하고 탐색 성능을 개선한다.
- **NavMesh 정합성:** A* 의 의도와 Unity NavMeshAgent의 실주행을 일치시키기 위해 NavMesh를 Area(Stair/Road/Ramp/Hazard)로 분리한다. 바퀴형은 Stair/Road Area를 areaMask에서 제외하여, 계단·차도를 침범하지 않고 **횡단보도로만 도로를 건넌다.**

### 6.3 통신 브릿지 (`src/presentation/ros2_bridge/`, `src/infrastructure/bridge/`)

- **명령 송신(`bridge.py`):** A* 웨이포인트를 HTTP POST로 Unity 수신 서버에 전달. (`SIMULATOR_HOST=0.0.0.0`은 접속 시 자동으로 루프백으로 정규화하여 Windows/Mac 모두 호환.)
- **피드백 수신(`push_feedback.py`):** Unity가 호출하는 서브프로세스. `FEEDBACK`/`DISCOVERY`/`MISSION_FAILED` 이벤트를 분기 처리한다.

### 6.4 임무 시스템 — 연속 자율 주행 루프 (`src/application/services/`)

- **자동 배정:** `MissionAssignmentService`가 Idle 로봇에 목적지를 배정하고 A* 경로를 송신한다.
- **연속 루프:** 로봇이 도착하면 `FEEDBACK`이 발생하고, `push_feedback`이 다음 임무를 즉시 재배정하여 시뮬레이션이 멈추지 않는다.
- **임무 실패/재배정(견고화):** 로봇이 최종 목적지에 도달하지 못하면(경로 막힘/끊김으로 NavMeshAgent STUCK) `MISSION_FAILED`를 발신한다. 해당 임무는 `Failed`로 처리되고 로봇은 Idle로 복귀 후 새 임무를 재배정받는다. 과거 도달 실패 시 로봇이 조용히 멈춰 루프가 영구 정지하던 문제를 근본적으로 해결했다.

### 6.5 피드백 지표 (`FeedbackCalculator`, `FeedbackAggregationService`)

- 한 구간 주행마다 **부하율·안정성·효율성**을 계산한다. 플랫폼과 지형 태그로 비용 프로파일을 정확히 lookup하며, `null`/`traversable:false`를 안전 처리하고 노이즈를 주입한다(`INoiseGenerator` DI).
- 주행 로그가 적재되면 해당 간선의 통계가 누적 갱신되어 다음 탐색에 반영된다.

### 6.6 관제 대시보드 (`src/presentation/dashboard/`)

- **실시간 맵 시각화:** 실제 맵 데이터(노드·간선·거점)를 탑뷰로 렌더링. 지형 태그별 색상, **Fog of War**(미발견 노드 반투명), 거점은 금색 다이아몬드로 표시. (간선은 약 20만 개이므로 기본 비표시, 켜면 샘플링.)
- **함대 현황/임무 로그:** 로봇 상태·배터리, 임무 진행/완료/실패 현황을 실시간(Supabase 연동)으로 표시. 3분할 독립 스크롤 레이아웃.

### 6.7 엣지 스토리지 서버 (`src/infrastructure/storage/`)

- Raspberry Pi 5의 1TB SSD를 활용한 FastAPI 기반 대용량 파일 스토리지. Nginx 리버스 프록시(`/` → 대시보드 8501, `/api/` → FastAPI 8000) + systemd 무중단 구성.

### 6.8 CI/CD 자동 배포 (`.github/workflows/`)

- `main` 푸시 시 Self-Hosted Runner가 자동으로 코드를 당겨와 배포한다.
- **`deploy-to-mac.yml`** (macOS/ARM64): 코드 pull → Secrets로 `.env` 생성 → conda 의존성 + **pytest 게이트** → launchd 헤드리스 시뮬레이터 재시작.
- **`deploy-to-pi.yml`** (Linux/ARM64): 코드 pull → `.env` 생성 → 의존성 → Nginx/systemd 동기화 → 대시보드·API 서버 재시작.
- **`supabase-migrations.yml`** / **`supabase-keep-alive.yml`**: DB 마이그레이션 자동 적용 및 무료 요금제 휴면 방지.

---

## 7. 데이터 모델

핵심 도메인 모델(`src/domain/models/`)은 모두 Pydantic으로 검증된다.

| 엔티티 | 설명 |
|--------|------|
| `MapMetadata` | 맵 메타데이터 |
| `Node` 계층 | 주행 그래프의 노드(좌표 x/z, 지형 태그, 노드 타입, 발견 여부) |
| `Edge` (`map_edges`) | 노드 간 간선 + 플랫폼별 누적 비용/지표 통계 |
| `Robot` | 로봇 개체(플랫폼, 상태, 배터리, 현재 임무) |
| `MissionLog` (`missions`) | 임무(출발/목적지, 상태: Active/Completed/Failed) |
| `Incident` | 사건/이상 기록 |
| `base_locations` | 거점(픽업/배달 위치) |

> 보안: 모든 테이블에 Row Level Security(RLS)가 활성화되어 있으며, 조회는 익명(anon) 키로 허용, 쓰기는 `service_role` 키로만 수행한다.

---

## 8. 디렉토리 구조

```text
ROBO-Path_project/
├── Unity/                       # Unity 6.4 가상 캠퍼스 및 시뮬레이션 환경 (C#)
├── .github/workflows/           # CI/CD 자동 배포(macOS, RPi) 및 마이그레이션/Keep-Alive
├── 0_Document/                  # 기획 및 아키텍처 설계 문서, AI 컨텍스트
├── config/                      # 비용 프로파일, Nginx, systemd/launchd 서비스 정의
├── scripts/                     # 시뮬레이터 실행, 환경 스냅샷, DB 유지보수 셸 스크립트
├── src/                         # 핵심 소스 코드 (클린 아키텍처)
│   ├── domain/                  #   순수 알고리즘(A*) 및 Pydantic 데이터 모델
│   ├── application/             #   Use Case(서비스) 및 Repository 인터페이스(Protocol)
│   ├── infrastructure/          #   외부 기술 구현체 (Supabase DB, FastAPI Storage, Bridge)
│   └── presentation/            #   진입점 (Streamlit 대시보드, Python↔Unity 브릿지, CLI)
├── supabase/migrations/         # DB 스키마 마이그레이션 SQL (버전 관리)
├── tests/                       # 단위/통합 테스트
├── environment.yml              # Conda 환경 의존성
├── requirements.txt             # Pip 의존성 목록
└── README.md                    # 현재 파일
```

---

## 9. 설치 및 실행

### 9.1 사전 요구 사항

- **Python:** 3.10 이상 (시뮬레이터 코어는 3.12에서 검증)
- **시뮬레이터:** macOS, Unity 6.4 (6000.4.11f1)
- **엣지 서버:** Raspberry Pi 5 (Nginx, systemd, GitHub Actions Runner)
- **클라우드:** Supabase 프로젝트 (RLS 정책 적용)

### 9.2 로컬 환경 구성

```bash
# 1. 저장소 클론
git clone https://github.com/kimsunwook01/ROBO-Path_github.git
cd ROBO-Path_github

# 2. 가상환경 (venv 또는 conda)
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. 환경 변수 (.env 를 프로젝트 루트에 생성)
#   SUPABASE_URL=...
#   SUPABASE_KEY=...              # anon(publishable) 키 (읽기)
#   SUPABASE_SERVICE_KEY=...      # service_role 키 (쓰기)
#   SIMULATOR_HOST=127.0.0.1      # Unity 수신 서버 호스트
#   SIMULATOR_WS_PORT=8765        # Unity 수신 포트
```

### 9.3 대시보드 로컬 실행

```bash
streamlit run src/presentation/dashboard/app.py
# 브라우저에서 http://localhost:8501 접속
```

---

## 10. 배포 (CI/CD)

운영 환경은 GitHub Actions를 통해 **무중단 자동 배포(CI/CD)** 된다.

1. 코드를 수정해 `main` 브랜치에 푸시한다.
2. 각 Self-Hosted Runner(Mac/Pi)가 즉시 가동되어 최신 코드를 당겨오고, 의존성·서비스를 갱신한 뒤 재시작한다. (Mac은 **pytest 게이트**를 통과해야 시뮬레이터가 재시작된다.)
3. **공개 대시보드:** 평가/시연용으로 Streamlit Community Cloud에 동일 대시보드를 미러 배포할 수 있다. Main file은 `src/presentation/dashboard/app.py`, Secrets에 `SUPABASE_URL`·`SUPABASE_KEY`(anon)만 등록하면 어디서든 접속 가능한 공개 URL이 생성된다.

> 의존성 동기화: 새 Python 패키지를 설치하면 반드시 `requirements.txt`에 반영·커밋하여 서버 환경과 동기화한다.

---

## 11. 시뮬레이션 운영 방법

Unity 시뮬레이터는 명령을 받아야만 로봇을 움직이는 **리스너**다. 첫 임무를 던져 연속 루프를 시작한다.

```bash
# (Unity 시뮬레이터가 구동 중인 상태에서)
# 첫 임무 배정 → 이후 도착/실패마다 push_feedback 이 다음 임무를 자동 재배정
python src/presentation/ros2_bridge/start_mission.py Wheeled-01
python src/presentation/ros2_bridge/start_mission.py Legged-01
# ... Legged-02 ~ 04

# 로봇 상태 일괄 리셋(Idle) — 이전 실행 잔여 상태 정리 시
python -c "from src.infrastructure.database.client import get_supabase_admin_client as g; \
c=g(); print(c.table('robots').update({'status':'Idle'}).neq('name','').execute().data)"
```

> `assign_next_mission`은 로봇이 **Idle** 상태일 때만 임무를 배정한다.

---

## 12. 결과 및 의의

- 바퀴형·보행형 로봇이 **동일 출발/목적지에 대해 서로 다른 경로**를 선택함을 시뮬레이션으로 검증했다(바퀴형은 계단·차도를 회피하고 횡단보도로만 도로를 건넘).
- 측정 → 환류 → 탐색의 **자율 주행 루프**가 도달 불가 상황(장애물·끊긴 경로)에서도 멈추지 않고 지속되도록 견고화하여, 장시간 무인 데이터 축적이 가능하다.
- A* 의도와 NavMesh 실주행을 일치시켜, **경로 계획과 물리 시뮬레이션의 정합성**을 확보했다.
- 모든 인프라(시뮬레이터·DB·대시보드)가 GitHub Actions로 자동 배포되는 **재현 가능한 운영 파이프라인**을 구축했다.

---

## 13. 알려진 한계 및 향후 과제

- **로봇 실시간 위치 오버레이:** 대시보드 맵에 로봇의 현재 위치를 실시간 표시하려면 위치 텔레메트리 컬럼/전송이 필요하다(현재 미구현).
- **LLM 피드백 지식화(보류):** 자연어 피드백을 구조화하는 `gemini_client.py` 모듈은 구현했으나, 런타임 연동(incidents 적재 + 분석 UI + 간선 페널티 환류)은 우선순위상 의도적으로 제외(De-scoped)했다.
- **중복 마이그레이션 정리:** 동일 타임스탬프의 `add_discovery.sql` / `add_discovery_columns.sql` 중복분 정리 예정(원격 마이그레이션 히스토리 확인 후).

---

## 14. 관련 문서

상세 기술 명세는 `0_Document/` 에서 확인할 수 있다.

- 전체 기획 및 분산 처리 명세: `0_Document/ROBO-Path_Design_Report.md`
- 데이터베이스 ERD 및 DDL: `0_Document/ROBO-Path_Supabase_DB_Architecture.md`
- 폴더 구조 및 계층 분리 전략: `0_Document/ROBO-Path_Software_Architecture.md`
- 애플리케이션 서비스 계층 설계: `0_Document/ROBO-Path_Application_Service_Layer.md`
- 맵 설계 및 비용 프로파일 명세: `0_Document/ROBO-Path_Map_Design_Specification.md`
- 씬 덤프 도구 명세: `0_Document/ROBO-Path_Scene_Dump_Specification.md`
- 대시보드 데이터 계약: `0_Document/ROBO-Path_Dashboard_Data_Contract.md`
- 프로젝트 상태/컨텍스트 요약: `0_Document/AI_CONTEXT.md`
