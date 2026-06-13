-- =====================================================================
-- ⚠️ 적용 보류 (Pending Application) ⚠️
-- 본 마이그레이션 파일은 웹 사용자 인증 및 세션 관리 구현 단계에서 적용될 예정입니다.
-- 현 단계(시뮬레이터 구축 단계)에서는 실제 DB에 마이그레이션을 실행하지 마십시오.
-- (세션 관리 테이블 생성 및 기존 테이블 세션 격리 스크립트)
-- =====================================================================

-- 1. sessions 테이블 신설
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT FALSE,  -- 현재 활성 세션 여부 (애플리케이션에서 동시 1개 보장)
    created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL, -- 생성한 사용자
    created_at TIMESTAMPTZ DEFAULT NOW(),
    description TEXT
);

-- 2. active_sessions (동시성 제어용 접속자 추적 테이블) 신설
CREATE TABLE active_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    last_ping TIMESTAMPTZ DEFAULT NOW(),
    connected_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. 세션 종속 테이블에 session_id 추가 (NULL 허용: 기존 데이터 및 마이그레이션 호환)
-- 주의: map_edges의 경우 platform_stats가 세션 종속이므로,
--       동일한 엣지라도 세션마다 별도의 행(또는 별도의 통계 기록 방식)이 필요할 수 있습니다.
--       향후 구현 단계에서 복합 키(from, to, session) 적용 등을 검토해야 합니다.
ALTER TABLE discovered_nodes
ADD COLUMN session_id UUID REFERENCES sessions(id) ON DELETE CASCADE;

ALTER TABLE map_edges
ADD COLUMN session_id UUID REFERENCES sessions(id) ON DELETE CASCADE;

ALTER TABLE mission_logs
ADD COLUMN session_id UUID REFERENCES sessions(id) ON DELETE CASCADE;

ALTER TABLE incidents
ADD COLUMN session_id UUID REFERENCES sessions(id) ON DELETE CASCADE;

ALTER TABLE simulation_logs
ADD COLUMN session_id UUID REFERENCES sessions(id) ON DELETE CASCADE;
