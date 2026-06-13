# ROBO-Path 데이터베이스 아키텍처 및 Supabase 세팅 가이드

## 1. 개요 및 목적
ROBO-Path 시스템에서 **Supabase** (PostgreSQL 기반)는 로봇의 입체 주행 경로 탐색에 필요한 **경량화된 공간 메타데이터**와 **경험 기반 수치 지표(부하율, 안정성 등)**를 저장하는 핵심 클라우드 데이터베이스입니다. 
대용량 파일(Point Cloud 데이터, 모터 원천 로그)은 라즈베리파이 스토리지(로컬)에 저장하고, Supabase는 해당 파일의 **접근 경로(URL/URI) 및 가중치 통계 지표**만을 관리하는 하이브리드 아키텍처를 채택하여 트래픽 비용을 최소화합니다.

---

## 2. 데이터베이스 스키마 설계 및 테이블 관계

데이터의 무결성을 보장하고 유연성을 확보하기 위해 '논리적 상속 구조'와 'JSONB 필드'를 혼합하여 사용합니다.

### 2.1 테이블 카테고리 구성
* **🗺️ 공간 및 노드 (Nodes)**
  * `map_metadata`: 시뮬레이션 원점(Origin) 좌표 및 지도 세맨틱 버전 관리
  * `nodes` (통합 부모): 3차원 공간 상의 모든 주요 경유점의 통합 $X, Y, Z$ 좌표
    * ↳ `base_locations` (자식): 인간이 명시적으로 정의한 고신뢰 주요 지점 (충전소, 로비 등)
    * ↳ `discovered_nodes` (자식): 로봇이 탐험(Exploration) 모드 중 자율적으로 발견한 경유점
* **🔗 연결성 및 로봇 (Edges & Robots)**
  * `robots`: 등록된 로봇 기종 목록 및 초기 하드웨어 특성 (바퀴형 vs 보행형 등)
  * `map_edges`: 노드와 노드 사이의 이동 경로. 핵심 컬럼인 `platform_stats` (JSONB)에 기종별 주행 성적 평균값을 누적하여 저장.
* **📈 경험 로그 및 LLM 피드백 (Logs & Feedbacks)**
  * `mission_logs`: 개별 주행 임무 완료 후 도출된 플랫폼별 부하율($L$), 안정성($S$), 효율성($E$) 요약 성적표
  * `incidents`: 운용자의 자연어 피드백 및 이를 Gemini API가 정형화한 구조적 위험 인자(JSONB) 테이블

---

## 3. 사용자 데이터 소유권 및 시뮬레이션 세션 모델 (향후 구현 항목)

**⚠️ 중요: 본 인증/소유권 및 세션 모델 설계의 실제 적용은 시뮬레이터 완성 이후 구현 단계에서 진행됩니다.**

ROBO-Path 시스템은 웹 공개에 대비하여 공용(Public) 데이터와 개인(Private) 데이터를 분리 관리하며, 탐색 상태를 격리하는 '세션(Session)' 개념을 도입합니다.

### 3.1 공용(전역) vs 개인 데이터
* **공용 데이터 (모든 사용자 공유):** `nodes`, `base_locations`, `discovered_nodes`, `map_edges`, `robots`
  * 집단 공간지능 형성을 위해 인증된 모든 사용자가 읽고/쓰기를 공유합니다.
* **개인 데이터 (본인만 소유 및 관리):** `mission_logs`, `incidents`
  * 사용자별 식별을 위해 **`user_id` (UUID) 컬럼을 추가**합니다.
  * 자신이 생성한 명령 기록과 피드백 데이터만 조회 및 수정이 가능하도록 Row Level Security (RLS) 정책을 적용할 예정입니다.
  * 시스템 백그라운드 자동 적재 시에는 `service_role` 키를 사용하여 RLS를 우회합니다.

### 3.2 세션 종속 vs 고정 데이터 (Session-dependent Data)
시뮬레이션 환경의 다중 "세이브 슬롯" 지원을 위해 `session_id` 컬럼을 도입합니다.
*   **고정 데이터 (세션과 무관하게 유지):** `nodes`의 `base_locations`, `map_metadata`, `robots`, `auth.users`
*   **세션 종속 데이터 (세션별로 격리):** `discovered_nodes`, `mission_logs`, `incidents`, `simulation_logs`
*   **특수 케이스 (`map_edges`):** 엣지 연결성 자체는 고정이나, `platform_stats`(피드백 통계)는 세션 종속입니다. 향후 구현 단계에서 동일 엣지에 대해 세션별로 통계를 분리 기록하는 구조(예: 복합 키 등)를 적용할 예정입니다.

---

## 4. 초기 세팅용 DDL 스크립트 (SQL)

아래 스크립트는 Supabase 웹 대시보드의 **SQL Editor** 탭에서 실행하거나, 향후 파이썬 마이그레이션 스크립트에서 자동 실행할 용도로 작성된 스키마입니다.

```sql
-- 1. 공간 참조 메타데이터 테이블 (지도 버전 제어 포함)
CREATE TABLE map_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    origin_lat FLOAT NOT NULL,
    origin_lon FLOAT NOT NULL,
    origin_alt FLOAT DEFAULT 0,
    unit_scale FLOAT DEFAULT 1.0,
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

-- 3. 사전 정의 기준점 테이블 (인간 정의 고신뢰 데이터)
CREATE TABLE base_locations (
    node_id UUID PRIMARY KEY REFERENCES nodes(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    priority INTEGER DEFAULT 10,
    location_usage VARCHAR(50)
);

-- 4. 로봇 발견 노드 테이블 (로봇 탐험 데이터)
CREATE TABLE discovered_nodes (
    node_id UUID PRIMARY KEY REFERENCES nodes(id) ON DELETE CASCADE,
    confidence_score FLOAT DEFAULT 0.0 CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    visit_count INTEGER DEFAULT 1,
    is_verified BOOLEAN DEFAULT FALSE,
    pcd_file_url TEXT -- [의미 재정의] 3D 포인트 클라우드가 아닌 탐색 복셀 데이터 파일(Octree 직렬화) 경로 (스키마 호환성 유지)
);

-- 5. 로봇 정보 테이블
CREATE TABLE robots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    platform VARCHAR(20) NOT NULL CHECK (platform IN ('wheeled', 'legged')),
    weight_profile JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. 경험 기반 엣지 테이블 (A* 알고리즘용 가중치 누적 통계 포함)
CREATE TABLE map_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_node_id UUID NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    to_node_id UUID NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    distance_m FLOAT NOT NULL,
    platform_stats JSONB NOT NULL DEFAULT '{}',
    version_added VARCHAR(20) DEFAULT 'v1.0.0',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- JSONB 내부 쿼리 속도 최적화를 위한 GIN 인덱스
CREATE INDEX idx_map_edges_platform_stats ON map_edges USING GIN (platform_stats);

-- 7. 미션 로그 테이블 (개별 주행 성적표)
CREATE TABLE mission_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    robot_id UUID REFERENCES robots(id) ON DELETE SET NULL,
    operating_mode VARCHAR(20) CHECK (operating_mode IN ('Exploration', 'Task', 'Hybrid')),
    load_factor FLOAT CHECK (load_factor >= 0.0 AND load_factor <= 1.0),
    stability_index FLOAT CHECK (stability_index >= 0.0 AND stability_index <= 1.0),
    efficiency_index FLOAT,
    log_file_url TEXT,
    profile_version VARCHAR(20) DEFAULT 'v1.0.0',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8. 사건/사고 및 인간 피드백 지식화 테이블 (LLM 분석 결과)
CREATE TABLE incidents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    edge_id UUID REFERENCES map_edges(id) ON DELETE CASCADE,
    robot_id UUID REFERENCES robots(id) ON DELETE SET NULL,
    raw_feedback TEXT NOT NULL,
    llm_analysis JSONB NOT NULL DEFAULT '{}',
    is_applied BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 5. 파이썬 연동 파이프라인 (supabase-py)

### 5.1. 환경 변수 세팅
향후 로컬 개발 및 라즈베리파이 서버 환경에서는 반드시 `.env` 파일에 다음 정보가 기입되어야 합니다.
```env
# .env 
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=eyJhbGci... (anon public key 또는 service_role key)
```

### 5.2. 데이터 플로우 설계
1. **Pydantic 기반 검증 필터:** 파이썬에서 발생하는 모든 데이터 삽입(Insert) 요청은 `src/database/schemas.py` 에 정의될 Pydantic 클래스에 의해 1차적으로 무결성(타입, $0.0 \sim 1.0$ 제약조건 등)이 검증됩니다.
2. **Supabase Client 통신:** `src/database/client.py` 에서 싱글톤(Singleton) 패턴으로 구현될 클라이언트 객체가 검증된 JSON 딕셔너리를 REST API 방식으로 Supabase에 전송합니다.
3. **가중치 업데이트 트리거:** 새로운 `mission_logs`가 적재되면, 관련 엣지의 `platform_stats` 값을 조회하고 새 평균값을 계산하여 `map_edges`를 `UPDATE` 하는 연산이 파이썬 백엔드에서 수행됩니다.

---

## 6. 다음 실행 목표 (Action Items)

본 설계 문서를 바탕으로 다음과 같은 개발을 진행합니다.

1. **[사용자]** Supabase 웹사이트에서 프로젝트(Database)를 생성하고 URL과 Key를 확보하여 `.env` 파일에 작성.
2. **[사용자/개발자]** 본 문서의 DDL 스크립트를 Supabase SQL Editor에서 실행하여 테이블 뼈대 구축.
3. **[개발자]** `src/database/` 하위에 파이썬 연동 클래스(`client.py`)와 Pydantic 모델(`schemas.py`) 코딩 시작.
