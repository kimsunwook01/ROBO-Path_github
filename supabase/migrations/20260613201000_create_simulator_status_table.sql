-- 6-1. simulator_status (페일세이프용)
CREATE TABLE simulator_status (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    is_online BOOLEAN DEFAULT FALSE,
    last_heartbeat TIMESTAMPTZ DEFAULT NOW(),
    host VARCHAR(100),
    ws_port INT DEFAULT 8765,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS 활성화
ALTER TABLE simulator_status ENABLE ROW LEVEL SECURITY;

-- 익명 사용자 읽기 허용 정책 추가
CREATE POLICY "Enable read access for all users on simulator_status" ON simulator_status FOR SELECT USING (true);
