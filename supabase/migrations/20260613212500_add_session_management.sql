-- =====================================================================
-- ⚠️ 적용 보류 (Pending Application) ⚠️
-- 본 마이그레이션 파일은 웹 사용자 인증 및 세션 관리 구현 단계에서 적용될 예정입니다.
-- 현 단계(시뮬레이터 구축 단계)에서는 실제 DB에 마이그레이션을 실행하지 마십시오.
-- (세션 스냅샷 아카이빙을 위한 테이블 신설 스크립트)
-- =====================================================================

-- 1. sessions 테이블 신설 (스냅샷 아카이빙 방식)
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT FALSE,   -- 현재 활성 세션 여부 (동시에 1개만 TRUE 유지)
    snapshot_url TEXT,                 -- 라즈베리파이 SSD에 저장된 스냅샷 파일 경로 (비활성 세션의 보관 데이터)
    created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_saved_at TIMESTAMPTZ,         -- 마지막으로 스냅샷이 저장된 시각
    description TEXT
);

-- 2. active_sessions (동시성 제어용 접속자 추적 테이블) 신설
CREATE TABLE active_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    last_ping TIMESTAMPTZ DEFAULT NOW(),
    connected_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================================
-- ⚠️ 핵심 동작 정의 (스냅샷 아카이빙 방식)
-- =====================================================================
-- 1. 현재 활성 세션의 데이터는 기존 작업 테이블(discovered_nodes, map_edges 등)에 "그대로" 존재합니다.
--    즉, 작업 테이블에는 session_id가 없으며, 항상 "현재 세션의 데이터"만 담고 있습니다.
-- 2. 세션 전환 절차:
--    가. 현재 작업 테이블의 세션 종속 데이터(discovered_nodes, mission_logs 등)를 직렬화하여
--        스냅샷 파일로 저장합니다. (라즈베리파이 SSD, FastAPI 경유)
--    나. sessions 테이블에 현재 세션의 snapshot_url, last_saved_at을 갱신합니다.
--    다. 작업 테이블의 세션 종속 데이터를 초기화(비우기)합니다.
--    라. 대상 세션이 기존 세션이면 해당 snapshot_url에서 데이터를 복원하여 작업 테이블에 적재하고,
--        새 세션이면 빈 상태로 시작합니다.
--    마. sessions.is_active 플래그를 전환합니다. (동시 1개만 active 보장)
-- 3. 스냅샷 대상 데이터: discovered_nodes, map_edges의 platform_stats, 복셀 데이터, 
--                      mission_logs, incidents, simulation_logs
-- 4. 맵 구조(base_locations, 길)는 스냅샷 대상이 아니며 전역적으로 고정 유지됩니다.
