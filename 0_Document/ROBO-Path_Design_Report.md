# 하드웨어 피드백 기반 입체 주행 경험 데이터베이스 (ROBO-Path) 설계 보고서

**제출자:** 김선욱 (소프트웨어학부, 학번: 2023245143)  
**작성일:** 2026년 5월 16일  

---

## 1. 프로젝트 개요 및 배경

### 1.1 배경 및 문제 정의
현재 대다수의 자율주행 로봇 솔루션은 2차원 또는 정적인 지도 데이터(Node-Edge Graph)에 의존하여 거리를 최소화하는 알고리즘을 적용하고 있습니다. 그러나 이러한 방식은 다음과 같은 현실적인 문제를 야기합니다.

* **플랫폼 비인식 (Platform-Agnostic):** 바퀴형(Wheeled) 플랫폼과 보행형(Legged) 플랫폼은 동역학적 특성과 물리 구조가 완전히 상이함에도 불구하고 동일한 비용 함수를 적용받습니다. 이로 인해 보행형 로봇이 평탄한 아스팔트 길을 두고 비효율적인 경로를 선택하거나, 바퀴형 로봇이 통행 불가능한 계단 경로를 배정받는 문제가 발생합니다.
* **노면 조건 미반영:** 실시간 노면의 경사도, 거칠기, 재질 등 물리적 상태가 경로 연산에 반영되지 않아 모터 과부하, 배터리 급방전, 미끄러짐(Slip)으로 인한 미션 실패 및 하드웨어 손상이 발생합니다.
* **정적 데이터의 한계:** 공사 구간, 유동인구 급증, 빙판길 형성 등 돌발적인 환경 변화를 실시간으로 인지하고 공유할 수 있는 피드백 루프가 부재합니다.

### 1.2 프로젝트 목적 및 핵심 가치
본 프로젝트 **ROBO-Path** 는 시뮬레이션 환경 및 실하드웨어 운영 과정에서 발생하는 물리적 피드백 데이터를 정형화하여 **'경험 기반 입체 주행 데이터베이스'** 를 구축하는 것을 목표로 합니다.

* **플랫폼 어웨어 라우팅 (Platform-Aware Routing):** 로봇의 플랫폼 특성에 따라 경로 비용 가중치를 동적으로 변형하여 최적의 주행 전략을 수립합니다.
* **하이브리드 분산 아키텍처:** 고성능 연산 워크스테이션, 현장 에지 컴퓨팅 서버(라즈베리파이), 클라우드 데이터베이스(Supabase)의 역할을 명확히 분리하여 데이터 처리 효율을 극대화하고 인프라 비용을 절감합니다.
* **페일세이프 및 Stateless 복구:** 워크스테이션의 가동 상태를 실시간 감지하여 시스템의 연속성을 보장하고, 예외 상황 발생 시 데이터를 보호하는 메커니즘을 내재화합니다.

```text
+------------------------------------------------------------+
|                       1. Mac Mini (M2 Pro)                  |
|  - Unity 6.4 (URP 3D) 시뮬레이션 구동                       |
|  - C# to Python Bridge (Process 기반 API 통신)              |
|  - Raycast 기반 가상 탐색, NavMesh 보정, 지표 표준화        |
+-----------------------------+------------------------------+
                              |
     [SFTP / HTTP POST]       |    [Supabase REST API / SDK]
     경량 지도 파일 전송      |    표준화 지표 및 파일 링크 적재
                              v
+-----------------------------+------------------------------+
|             3. 라즈베리파이 에지 서버 (1TB SSD)             |
|  - Streamlit 웹 애플리케이션 (사용자 관제 UI 및 UI 제어)     |
|  - 로컬 스토리지 서버 (경량 지도 파일 및 원천 로그 보관)    |
|  - Gemini API 연동 및 Pydantic 하네스 검증 엔진 구동          |
+-----------------------------+------------------------------+
                              |
                  [실시간 채널 / REST API]
                양방향 데이터 갱신 및 동기화
                              v
+------------------------------------------------------------+
|                    2. 클라우드 데이터베이스                  |
|  - Supabase (PostgreSQL 기반 RDBMS)                        |
|  - 노드 상속 구조 및 JSONB 유연 지표 데이터 관리            |
|  - Realtime 구독 기능을 통한 온라인 플래그 전파             |
+------------------------------------------------------------+
```

---

## 2. 시스템 아키텍처 및 하이브리드 토폴로지

본 시스템은 고성능 연산이 필요한 시뮬레이션 환경과 웹 관제 및 로컬 파일 스토리지를 제공하는 에지 서버, 그리고 유기적 데이터 동기화를 담당하는 클라우드 DB의 **3-Tier 분산 구조** 로 설계되었습니다.

### 2.1 컴포넌트별 역할 분담
1. **Mac Mini M2 Pro:** Unity 6.4 (URP 3D) 시뮬레이션 환경 구동 및 탐색(Raycast) 연산을 전담합니다. 500m x 500m 규모의 가상 캠퍼스 환경에서 로봇 주행 중 발생하는 데이터와 물리 충돌을 실시간으로 계산 및 정제합니다.
2. **라즈베리파이 에지 서버 (Raspberry Pi + 1TB SSD):** 웹 서버와 파일 스토리지 서버 역할을 동시에 수행합니다. 클라우드 용량 한계를 극복하기 위해 Mac Mini에서 추출된 경량 파일 및 원천 로그를 로컬 SSD에 저장하고, 사용자가 접속하는 **Streamlit** 관제 화면을 호스팅합니다.
3. **클라우드 데이터베이스 (Supabase):** 가볍고 정형화된 수치 통계 지표와 라즈베리파이 로컬 파일 저장소의 인덱스 주소(URL 경로)만을 저장합니다. PostgreSQL의 **JSONB** 포맷을 활용해 스키마의 유연성을 확보하고 실시간 상태 변화를 전파합니다.

---

## 3. 데이터 생성 및 계산 상세 명세

데이터의 폭발적인 증가를 막고 네트워크 대역폭을 보존하기 위해, 모든 원천 데이터는 생성 주체인 **Mac Mini** 내에서 1차 가공 및 표준화 지표 변환 과정을 거칩니다.

### 3.1 Mac Mini 생성 데이터
* **고용량 원천 데이터 (Raw Data):**
  * **Raycast 탐색 로그:** 전방 180도 부채꼴 형태의 Ray 36개(최대 거리 30m)가 충돌한 지점의 로그입니다. 반경 5m 내 노드는 즉시 `DISCOVERED`로 전환됩니다.
  * **하드웨어 주행 로그:** NavMeshAgent velocity 및 Rigidbody 진동값 기반의 지표 및 소요 시간 데이터입니다.
* **경량화 및 추출 데이터:**
  * **위상 그래프 데이터 (.json):** Unity 환경에서 추출한 노드 구조와 엣지 가중치 결합 파일입니다.

### 3.2 하드웨어 피드백의 표준화 지표 (Derived Metrics)
워크스테이션은 서로 다른 구조를 가진 기종들을 상호 비교하기 위해 물리적 원시 로그를 다음과 같은 $0.0 \sim 1.0$ 사이의 공통 추상화 지표로 변환합니다.

1. **부하율 (Load Factor, $L$):**
   로봇의 정격 최대 토크 대비 주행 중 실제로 요구된 액추에이터 토크의 평균 비율입니다.
   $$L = \frac{1}{N}\sum_{i=1}^{N}\left(\frac{\tau_{actual, i}}{\tau_{max}}\right)$$
2. **안정성 지수 (Stability Index, $S$):**
   주행 중 IMU 센서에서 감지된 급격한 가속도 변화량(Jerk)과 미끄러짐(Slip) 이벤트 발생 빈도를 역산하여 정상 주행 상태를 수치화합니다. 값이 $1.0$에 가까울수록 진동과 미끄러짐이 없는 안정적인 주행을 의미합니다.
3. **효율성 지수 (Efficiency Index, $E$):**
   단위 거리 및 단위 시간당 소모된 배터리 전력량의 효율성입니다. 기본 배터리 용량 대비 소모 속도를 상대 비교하여 산출합니다.

---

## 4. 컴포넌트 간 데이터 전송 및 제어 메커니즘

각 컴포넌트의 가용 자원과 데이터의 성격에 맞춰 통신 프로토콜을 차별화합니다.

### 4.1 파일 및 메타데이터 전송
* **Mac Mini $\rightarrow$ 라즈베리파이 (대용량 파일 전송):**
  Mac Mini에서 연산이 완료된 파일 및 주행 성적표 파일은 라즈베리파이에 개설된 FastAPI 엔드포인트를 통해 **HTTP POST (Multipart Form-Data)** 프로토콜로 직접 파이의 1TB SSD 저장소에 물리적으로 저장됩니다.
* **Mac Mini $\rightarrow$ Supabase (메타데이터 적재):**
  표준화된 3대 주행 지표($L, S, E$)와 라즈베리파이 로컬 저장소 상의 파일 상대 경로 주소는 C#에서 호출하는 Python 브릿지를 경유하여 Supabase Python SDK를 통해 클라우드 DB 인스턴스에 적재됩니다.

### 4.2 C# - Python 브릿지 및 Supabase 연동 파이프라인
Unity 환경에서의 데이터 처리를 위해 C#과 Python을 연결하는 하이브리드 파이프라인을 도입합니다.

```text
[Unity C# 스크립트]
       |
[System.Diagnostics.Process (JSON Message)]
       v
[Python 브릿지 (bridge.py)]
       |
[Supabase Python SDK]
       v
[Supabase 클라우드 데이터베이스]
```

* **통신 원리:** Unity 내의 C# 스크립트는 엣지 통과 시마다 피드백 지표 및 노드 발견 이벤트를 JSON으로 직렬화한 후, `System.Diagnostics.Process`를 통해 `bridge.py`를 서브 프로세스로 호출합니다.
* **환경 변수 구성:** `bridge.py`는 로컬 `.env`에 등록된 `SUPABASE_URL` 및 `SUPABASE_KEY`를 로드하여 보안을 유지한 채 DB API와 통신합니다.

---

## 5. 데이터베이스 설계 (Database DDL 및 ERD 명세)

데이터 무결성을 보장하고 데이터 출처를 엄격히 분리하기 위해 **상속(Inheritance) 구조**와 **JSONB** 인덱싱 최적화를 적용한 DDL 스크립트입니다.

```sql
-- 1. 공간 참조 메타데이터 테이블 (지도 버전 제어 포함)
CREATE TABLE map_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    origin_lat FLOAT NOT NULL,                  -- 시뮬레이션 원점(0,0,0)의 기준 위도
    origin_lon FLOAT NOT NULL,                  -- 시뮬레이션 원점(0,0,0)의 기준 경도
    origin_alt FLOAT DEFAULT 0,
    unit_scale FLOAT DEFAULT 1.0,               -- 시뮬레이션 1단위당 실제 물리 거리(m) 변환 배율
    complex_name VARCHAR(100) NOT NULL,
    map_version VARCHAR(20) NOT NULL DEFAULT 'v1.0.0',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. 통합 노드 마스터 테이블 (부모 테이블)
CREATE TABLE nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    x FLOAT NOT NULL,
    y FLOAT NOT NULL,
    z FLOAT NOT NULL,
    node_type VARCHAR(20) NOT NULL CHECK (node_type IN ('BASE', 'DISCOVERED')),
    version_added VARCHAR(20) DEFAULT 'v1.0.0',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. 사전 정의 기준점 테이블 (자식 테이블 - 인간 정의 고신뢰 데이터)
CREATE TABLE base_locations (
    node_id UUID PRIMARY KEY REFERENCES nodes(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    priority INTEGER DEFAULT 10,                -- 값이 높을수록 라우팅 시 우선순위 부여
    location_usage VARCHAR(50)                  -- 예: '충전 스테이션', '단지 주입구', '하차 지점'
);

-- 4. 로봇 발견 노드 테이블 (자식 테이블 - 로봇 탐험 데이터)
CREATE TABLE discovered_nodes (
    node_id UUID PRIMARY KEY REFERENCES nodes(id) ON DELETE CASCADE,
    confidence_score FLOAT DEFAULT 0.0 CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    visit_count INTEGER DEFAULT 1,
    is_verified BOOLEAN DEFAULT FALSE,          -- 검증 임계치 도달 시 TRUE 변경
    pcd_file_url TEXT                           -- 라즈베리파이 SSD 내부의 .pcd 파일 경로 주소
);

-- 5. 로봇 정보 테이블
CREATE TABLE robots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    platform VARCHAR(20) NOT NULL CHECK (platform IN ('wheeled', 'legged')),
    weight_profile JSONB NOT NULL DEFAULT '{}', -- A* 알고리즘용 플랫폼별 가중치 초기 설정값
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. 경험 기반 엣지 테이블 (가중치 누적 통계 포함)
CREATE TABLE map_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_node_id UUID NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    to_node_id UUID NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    distance_m FLOAT NOT NULL,
    platform_stats JSONB NOT NULL DEFAULT '{}', -- 기종별 평균 부하율, 안정성, 효율성 요약 데이터
    version_added VARCHAR(20) DEFAULT 'v1.0.0',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- GIN 인덱스 설정을 통한 JSONB 내부 쿼리 속도 최적화
CREATE INDEX idx_map_edges_platform_stats ON map_edges USING GIN (platform_stats);

-- 7. 미션 로그 테이블 (주행별 경량 성적표)
CREATE TABLE mission_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    robot_id UUID REFERENCES robots(id) ON DELETE SET NULL,
    operating_mode VARCHAR(20) CHECK (operating_mode IN ('Exploration', 'Task', 'Hybrid')),
    load_factor FLOAT CHECK (load_factor >= 0.0 AND load_factor <= 1.0),
    stability_index FLOAT CHECK (stability_index >= 0.0 AND stability_index <= 1.0),
    efficiency_index FLOAT,
    log_file_url TEXT,                         -- 라즈베리파이 SSD 내부의 원천 로그 .csv 경로 주소
    profile_version VARCHAR(20) DEFAULT 'v1.0.0',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8. 사건/사고 및 인간 피드백 지식화 테이블 (LLM 정형화 데이터 소스)
CREATE TABLE incidents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    edge_id UUID REFERENCES map_edges(id) ON DELETE CASCADE,
    robot_id UUID REFERENCES robots(id) ON DELETE SET NULL,
    raw_feedback TEXT NOT NULL,                -- 인간 운용자가 입력한 자연어 원문
    llm_analysis JSONB NOT NULL DEFAULT '{}',   -- Gemini API가 추출한 구조화 데이터
    is_applied BOOLEAN DEFAULT FALSE,           -- 관리자 승인 및 가중치 알고리즘 반영 여부
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 6. 데이터 버전 관리 및 실시간 동기화 전략

### 6.1 지도 데이터 버전 제어 (Map Versioning)
지도 정보의 무분별한 갱신과 데이터 오염을 막기 위해 세맨틱 버전 시스템을 차용합니다.
* **메이저 버전 (Major, 예: v1.0.0 $\rightarrow$ v2.0.0):** 단지 내 대규모 공사, 도로 폐쇄 등 공간 구조 자체가 완전히 물리적으로 변형되었을 때 수동으로 격상하며, 기존 그래프 데이터를 아카이빙 처리한 뒤 새 스냅샷 테이블을 구성합니다.
* **마이너 버전 (Minor, 예: v1.0.0 $\rightarrow$ v1.1.0):** 유휴 시간대 '탐험 모드'를 완료한 로봇이 복귀하여 검증된 새로운 노드와 엣지를 등록할 때마다 자동으로 소수점 버전을 올립니다. 각 행의 `version_added` 컬럼을 조회하여 특정 탐험 차수의 데이터만 필터링하거나 롤백할 수 있습니다.

### 6.2 데이터 연산의 분산 처리 주체
* **엣지 가중치 동적 업데이트 연산:** 미션 로그가 Supabase에 최종 완결되는 즉시 라즈베리파이의 Streamlit 백엔드가 트리거됩니다. 해당 주행 구간(`edge_id`)의 기존 `platform_stats` (JSONB) 데이터를 DB에서 호출하여 새로 유입된 하드웨어 지표 값과 산술 누적 평균값으로 결합 계산한 뒤 Supabase에 즉시 UPDATE를 수행합니다.
* **인간 피드백 지식화 연산:** 사용자가 입력한 자연어 텍스트는 라즈베리파이 백엔드에서 Google Gemini API로 전송됩니다. 엄격한 구조화 프롬프트 제약에 맞춰 추출된 JSON 결과물은 라즈베리파이 내부의 Pydantic 하네스 검증기(Harness Validation)를 거치며 데이터 범위 및 규격의 무결성이 100% 입증된 상태로 Supabase에 적재됩니다.

---

## 7. 예외 상황 처리 및 페일세이프(Fail-Safe) 메커니즘

본 시스템은 고성능 연산을 전담하는 워크스테이션이 다운되거나 프로그램이 종료되는 오프라인 예외 상황에 대비하여 철저한 페일세이프 프로토콜을 내재화합니다.

```text
+-----------------------------------------------------------------------+
|                       [Mac Mini 가동 상태 모니터링]                      |
|                                                                       |
|   라즈베리파이 Streamlit 백엔드 -> Mac Mini 상태 체크 API로 주기적 Ping 송신 |
+----------------------------------+------------------------------------+
                                   |
              +--------------------+--------------------+
              | 연결 성공                               | 연결 단절 감지
              v                                         v
+-----------------------------+           +-----------------------------+
|    [State A: Connected]     |           |    [State B: Disconnected]  |
|                             |           |                             |
|  - 정상 실시간 제어 모드 활성화 |           |  - '읽기 전용 모드' 강제 전환  |
|  - 키보드 원격 조작 UI 활성화  |           |  - 경고 배너 출력 및 UI 잠금 |
|  - 미션 명령 및 데이터 생성 허용|           |  - 과거 기록 조회 서비스만 제공 |
+-----------------------------+           +-----------------------------+
                                                        |
                                                        | Mac Mini 재구동 및
                                                        | Unity 시뮬레이션 환경 실행
                                                        v
                                          +-----------------------------+
                                          |   [자동 핸드셰이킹 및 복구]   |
                                          |                             |
                                          | - REST API 온라인 플래그 갱신 |
                                          | - 라즈베리파이 상태 실시간 감지|
                                          | - State A 모드로 자동 원격 복구|
+-----------------------------------------+-----------------------------+
```

### 7.1 하트비트(Heartbeat) 감지를 통한 읽기 전용 모드 동적 전환
* **감지 메커니즘:** 라즈베리파이의 Streamlit 백엔드 스레드는 Mac Mini의 상태 체크 API로 주기적인 연결 확인 신호(Ping)를 송신하여 하트비트를 체크합니다.
* **UI 잠금 (Locking):** Mac Mini의 오프라인 상태가 감지되는 즉시, Streamlit 관제 대시보드 상단에 "시뮬레이션 서버 연결이 끊어졌습니다. 안전을 위해 읽기 전용 모드로 전환됩니다" 라는 적색 경고 배너를 출력합니다. 동시에 사용자의 UI 제어 이벤트 리스너를 강제로 `disabled=True` 처리하고 미션 배정 폼을 차단합니다. 이 상태에서는 오직 Supabase DB에 안전하게 보존되어 있는 과거 주행 로그와 지도 통계 데이터만 안전하게 조회할 수 있는 읽기 전용 서비스만 제공합니다.

### 7.2 데이터베이스의 무상태성(Stateless) 기반 자동 재연결
* **REST API 통신의 이점:** Supabase 클라이언트 백엔드는 상태를 유지하지 않는 연결(Stateless HTTP REST API) 방식으로 작동하기 때문에, Mac Mini가 불시에 종료되더라도 클라우드 데이터베이스 세션이 깨지거나 충돌 에러가 발생하지 않습니다. DB는 완벽히 독립된 안정 상태를 유지합니다.
* **자동 복구 핸드셰이킹:** 사용자가 Mac Mini를 다시 가동하고 Unity 프로그램을 실행하면, 시스템 초기화 스크립트가 구동되면서 Supabase에 온라인 상태 플래그를 `TRUE`로 갱신합니다. 이를 실시간 채널(Realtime Subscription)로 실시간 구독 중이던 라즈베리파이가 즉시 인지하여 대시보드의 경고 배너를 지우고 UI 컴포넌트들의 잠금을 자동으로 완전히 해제(`disabled=False`)합니다. 이로써 어떠한 수동 재부팅 작업 없이도 전체 실시간 데이터 파이프라인이 유기적으로 자동 재개됩니다.

---

### 📝 보고서 핵심 업데이트 내용 요약

1. **3-Tier 분산 연산 토폴로지 구체화:**
   * **Mac Mini (M2 Pro)**는 **Unity 6.4** 구동 및 Raycast 탐색 엔진 연산을 전담합니다.
   * **라즈베리파이**는 1TB SSD 저장소를 활용해 경량화 파일 및 원천 로그를 로컬에 보관하여 클라우드 용량 한계를 극복하고, **Streamlit** 관제 UI 호스팅 및 **Gemini API** 기반 데이터 정제 하네스를 돌립니다.
   * **Supabase**는 유연한 가중치 누적 스탯 관리를 위한 **JSONB** 인덱싱과 파일 경로 인덱스만 경량 보관합니다.

2. **표준화 주행 지표 (Derived Metrics) 연산식 정의:**
   * 각 기종의 상이한 하드웨어 물리 값을 공통의 언어로 정규화하기 위한 **부하율 ($L$)**, **안정성 지수 ($S$)**, **효율성 지수 ($E$)**의 수학적 정의와 연산 분산 주체를 명시했습니다.

3. **C# - Python 브릿지 연동 파이프라인 수립:**
   * 무거운 ROS2를 제거하고, Unity의 C# 스크립트에서 엣지 통과 시마다 `bridge.py` 서브 프로세스를 호출하여 JSON 데이터와 함께 Supabase Python SDK로 데이터를 직접 적재하는 직관적이고 가벼운 하이브리드 제어 구조를 정립했습니다.

4. **지도 및 프로필 세맨틱 버전 관리 전략:**
   * 대규모 구조 변형을 의미하는 메이저 버전과 탐험을 통한 노드/엣지 확장을 뜻하는 마이너 버전을 분리하고, 테이블 스키마에 `version_added` 컬럼을 개설하여 언제든 탐험 차수별로 롤백 및 데이터 필터링이 가능하도록 설계했습니다.

5. **페일세이프 (Fail-Safe) 및 Stateless 복구 매커니즘:**
   * 워크스테이션 오프라인 상태 감지 시 라즈베리파이가 하트비트 체크를 통해 즉시 관제 UI를 **'읽기 전용 모드'**로 강제 제어 잠금하는 로직을 명세했습니다.
   * 워크스테이션 재구동 시 HTTP REST API의 무상태성 이점을 살려, 별도의 수동 재부팅 없이 실시간 채널 동기화를 통해 파이프라인이 자동 복구되는 시나리오를 설계했습니다.
