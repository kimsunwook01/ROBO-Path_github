-- Spec C: Discovery(탐색) 파이프라인
-- nodes 테이블에 "탐색 여부" 표현을 위한 컬럼 추가.
-- 기존 node_type enum(BASE/DISCOVERED)과 discovered_nodes 별도 테이블 구조를 건드리지 않고,
-- 최소 변경으로 Fog of War(미탐색=가려짐, 발견=드러남)를 구현한다.

ALTER TABLE nodes ADD COLUMN IF NOT EXISTS is_discovered BOOLEAN DEFAULT FALSE;
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS discovered_at TIMESTAMPTZ;
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS discovery_confidence FLOAT DEFAULT 0.0
    CHECK (discovery_confidence >= 0.0 AND discovery_confidence <= 1.0);

-- 거점(BaseLocation에 대응하는 node)은 처음부터 알려진 주소지이므로 is_discovered=true 로 둔다.
-- base_locations 테이블에 node_id 가 존재하는 nodes 행을 거점으로 간주.
UPDATE nodes
SET is_discovered = TRUE, discovery_confidence = 1.0
WHERE id IN (SELECT node_id FROM base_locations);
