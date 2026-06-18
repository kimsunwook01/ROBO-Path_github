-- Spec C: Fog of War — nodes 테이블에 탐색 여부 컬럼 추가
-- 기존 node_type enum(BASE/DISCOVERED)과 discovered_nodes 별도 테이블은 건드리지 않고,
-- nodes 테이블에 "탐색 여부" 신호를 덧붙이는 최소 변경 방식.

ALTER TABLE nodes ADD COLUMN IF NOT EXISTS is_discovered BOOLEAN DEFAULT FALSE;
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS discovered_at TIMESTAMPTZ;
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS discovery_confidence FLOAT DEFAULT 0.0
    CHECK (discovery_confidence >= 0.0 AND discovery_confidence <= 1.0);

-- 좌표 기반 조회(get_node_near) 성능을 위한 인덱스 (선택적이지만 권장)
CREATE INDEX IF NOT EXISTS idx_nodes_xz ON nodes (x, z);
