import os
import sys
import logging
import argparse
from dotenv import load_dotenv

# src 패키지를 인식할 수 있도록 PYTHONPATH 경로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.infrastructure.database.client import get_supabase_client
from src.infrastructure.database.supabase_node_repo import SupabaseNodeRepository
from src.infrastructure.database.supabase_edge_repo import SupabaseEdgeRepository
from src.application.services.map_import_service import MapImportService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Import scene_dump.json into Supabase")
    parser.add_argument("filepath", type=str, help="Path to scene_dump.json file")
    args = parser.parse_args()

    load_dotenv()
    
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        logger.error("SUPABASE_URL and SUPABASE_KEY must be set in .env")
        sys.exit(1)

    try:
        # DB Client 및 Repo 초기화
        db_client = get_supabase_client()
        node_repo = SupabaseNodeRepository(db_client)
        edge_repo = SupabaseEdgeRepository(db_client)

        # 서비스 생성 및 실행
        service = MapImportService(node_repo, edge_repo)
        
        logger.info(f"Starting import from {args.filepath}...")
        nodes_count, edges_count = service.import_from_json(args.filepath)
        
        logger.info(f"Import completed successfully!")
        logger.info(f"Upserted Nodes: {nodes_count}")
        logger.info(f"Upserted Edges: {edges_count}")

    except Exception as e:
        logger.error(f"Failed during import: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
