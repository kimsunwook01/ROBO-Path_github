-- 6-2. simulation_logs (검증용)
CREATE TABLE simulation_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    event_type VARCHAR(50) NOT NULL,
    robot_id VARCHAR(50),
    platform VARCHAR(20),
    from_node_id UUID,
    to_node_id UUID,
    load_factor FLOAT,
    stability FLOAT,
    efficiency FLOAT,
    discovered_node_id UUID,
    ray_distance FLOAT,
    is_valid BOOLEAN DEFAULT TRUE,
    validation_note TEXT
);

-- RLS 활성화
ALTER TABLE simulation_logs ENABLE ROW LEVEL SECURITY;

-- 익명 사용자 읽기 허용 정책 추가
CREATE POLICY "Enable read access for all users on simulation_logs" ON simulation_logs FOR SELECT USING (true);
