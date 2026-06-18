import sys
import os
# 프로젝트 루트를 sys.path에 추가 (이 파일은 루트에 있으므로 자기 디렉터리 기준)
_root = os.path.dirname(os.path.abspath(__file__))
if _root not in sys.path:
    sys.path.insert(0, _root)

from src.infrastructure.database.client import get_supabase_admin_client
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cleanup():
    db = get_supabase_admin_client()
    
    # 1. robots 테이블 리셋
    logger.info("Resetting robots table...")
    res1 = db.table("robots").update({"status": "Idle", "current_mission_id": None}).neq("id", "00000000-0000-0000-0000-000000000000").execute()
    logger.info(f"Reset {len(res1.data)} robots to Idle.")
    
    # 2. missions 테이블 삭제
    logger.info("Deleting all missions...")
    res2 = db.table("missions").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    logger.info(f"Deleted {len(res2.data)} missions.")

if __name__ == "__main__":
    cleanup()
