-- 모든 테이블에 대해 Row Level Security (RLS) 활성화
-- RLS를 켜면 기본적으로 모든 접근(SELECT, INSERT, UPDATE, DELETE)이 차단됩니다. (단, postgres, service_role 역할은 예외)

ALTER TABLE map_metadata ENABLE ROW LEVEL SECURITY;
ALTER TABLE nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE base_locations ENABLE ROW LEVEL SECURITY;
ALTER TABLE discovered_nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE robots ENABLE ROW LEVEL SECURITY;
ALTER TABLE map_edges ENABLE ROW LEVEL SECURITY;
ALTER TABLE mission_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE incidents ENABLE ROW LEVEL SECURITY;

-- 익명(anon) 사용자에 대한 읽기(SELECT) 권한 허용 정책 추가
-- Streamlit 대시보드 등에서 사용자 로그인 없이 데이터를 조회할 수 있도록 SELECT 권한만 허용합니다.
-- 파이썬 백엔드 데이터 삽입(INSERT/UPDATE)은 'service_role' 키를 사용하여 RLS를 우회하는 방식을 권장합니다.

CREATE POLICY "Enable read access for all users on map_metadata" ON map_metadata FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users on nodes" ON nodes FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users on base_locations" ON base_locations FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users on discovered_nodes" ON discovered_nodes FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users on robots" ON robots FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users on map_edges" ON map_edges FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users on mission_logs" ON mission_logs FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users on incidents" ON incidents FOR SELECT USING (true);
