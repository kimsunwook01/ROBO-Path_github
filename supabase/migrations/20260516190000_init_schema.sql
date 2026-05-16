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
    pcd_file_url TEXT
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
