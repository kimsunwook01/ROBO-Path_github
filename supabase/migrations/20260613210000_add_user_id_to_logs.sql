-- =====================================================================
-- ⚠️ 적용 보류 (Pending Application) ⚠️
-- 본 마이그레이션 파일은 웹 사용자 인증 및 권한 구현 단계에서 적용될 예정입니다.
-- 현 단계(시뮬레이터 구축 단계)에서는 실제 DB에 마이그레이션을 실행하지 마십시오.
-- (mission_logs, incidents 개인 데이터화 및 RLS 적용 스크립트)
-- =====================================================================

-- 1. mission_logs 테이블에 user_id 컬럼 추가 (NULL 허용: 기존 데이터 호환용)
ALTER TABLE mission_logs
ADD COLUMN user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL;

-- 2. incidents 테이블에 user_id 컬럼 추가 (NULL 허용: 기존 데이터 호환용)
ALTER TABLE incidents
ADD COLUMN user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL;

-- =====================================================================
-- ⚠️ RLS 정책 방향 (추후 구현 시 주석 해제하여 적용 예정) ⚠️
--
-- ALTER TABLE mission_logs ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE incidents ENABLE ROW LEVEL SECURITY;
--
-- CREATE POLICY "Users can only view their own missions"
-- ON mission_logs FOR SELECT
-- USING (auth.uid() = user_id);
--
-- CREATE POLICY "Users can insert their own missions"
-- ON mission_logs FOR INSERT
-- WITH CHECK (auth.uid() = user_id);
--
-- CREATE POLICY "Users can only view their own incidents"
-- ON incidents FOR SELECT
-- USING (auth.uid() = user_id);
--
-- CREATE POLICY "Users can insert their own incidents"
-- ON incidents FOR INSERT
-- WITH CHECK (auth.uid() = user_id);
-- =====================================================================
