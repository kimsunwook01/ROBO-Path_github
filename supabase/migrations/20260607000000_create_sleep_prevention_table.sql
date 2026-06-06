-- 휴면 방지(Keep-Alive)를 위한 더미 테이블 생성
CREATE TABLE sleep_prevention_table (
    id SERIAL PRIMARY KEY,
    message VARCHAR(50) NOT NULL,
    last_pinged_at TIMESTAMPTZ DEFAULT NOW()
);

-- "wake_up" 문자열 데이터 삽입
INSERT INTO sleep_prevention_table (message) VALUES ('wake_up');

-- 누구나 읽을 수 있도록 RLS 설정
ALTER TABLE sleep_prevention_table ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow anonymous read access on sleep_prevention_table"
    ON sleep_prevention_table FOR SELECT
    TO anon
    USING (true);
