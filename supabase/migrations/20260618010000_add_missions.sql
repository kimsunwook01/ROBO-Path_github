-- 1. robots 테이블에 상태 컬럼 추가 (Spec B 연계)
ALTER TABLE robots ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'Idle';
ALTER TABLE robots ADD COLUMN IF NOT EXISTS battery_pct FLOAT DEFAULT 100.0;
ALTER TABLE robots ADD COLUMN IF NOT EXISTS current_speed_mps FLOAT DEFAULT 0.0;
ALTER TABLE robots ADD COLUMN IF NOT EXISTS current_mission_id UUID;

-- 2. robots 초기 데이터 9대 INSERT (Wheeled-01~05, Legged-01~04)
-- 중복 삽입 방지를 위해 WHERE NOT EXISTS 사용
INSERT INTO robots (name, platform, status)
SELECT name, platform, 'Idle'
FROM (VALUES
    ('Wheeled-01', 'wheeled'),
    ('Wheeled-02', 'wheeled'),
    ('Wheeled-03', 'wheeled'),
    ('Wheeled-04', 'wheeled'),
    ('Wheeled-05', 'wheeled'),
    ('Legged-01', 'legged'),
    ('Legged-02', 'legged'),
    ('Legged-03', 'legged'),
    ('Legged-04', 'legged')
) AS v(name, platform)
WHERE NOT EXISTS (SELECT 1 FROM robots WHERE robots.name = v.name);

-- 3. missions 테이블 생성
CREATE TABLE missions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    robot_id UUID REFERENCES robots(id) ON DELETE CASCADE,
    mission_type VARCHAR(20) NOT NULL CHECK (mission_type IN ('Delivery', 'Exploration')),
    status VARCHAR(20) NOT NULL CHECK (status IN ('Pending', 'Active', 'Completed', 'Failed')),
    from_node_id UUID REFERENCES nodes(id) ON DELETE SET NULL,
    to_node_id UUID REFERENCES nodes(id) ON DELETE SET NULL,
    accumulated_cost FLOAT DEFAULT 0.0,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    acknowledged BOOLEAN DEFAULT FALSE
);

-- 이제 robots.current_mission_id에 FK를 건다.
ALTER TABLE robots
ADD CONSTRAINT fk_current_mission
FOREIGN KEY (current_mission_id) REFERENCES missions(id) ON DELETE SET NULL;
