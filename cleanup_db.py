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
