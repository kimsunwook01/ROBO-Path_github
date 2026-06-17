import os
from supabase import create_client, Client
from dotenv import load_dotenv

# .env 파일에서 환경변수 로드
load_dotenv()

class SupabaseClient:
    """
    Supabase 통신을 위한 싱글톤 클라이언트.
    .env 파일의 SUPABASE_URL 및 SUPABASE_KEY를 사용하여 연결을 초기화합니다.
    """
    _instance = None
    _client: Client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SupabaseClient, cls).__new__(cls)
            cls._instance._initialize_client()
        return cls._instance

    def _initialize_client(self):
        url: str = os.environ.get("SUPABASE_URL")
        key: str = os.environ.get("SUPABASE_KEY")
        
        # 만약 환경변수가 없다면 초기화를 실패하거나 더미 동작을 할 수 있도록 방어 코드 추가 가능
        if not url or not key:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("SUPABASE_URL or SUPABASE_KEY is not set in environment variables.")
        else:
            self._client = create_client(url, key)

    @property
    def client(self) -> Client:
        if not self._client:
            raise ValueError("Supabase client is not initialized. Check your environment variables.")
        return self._client

# 전역적으로 접근 가능한 인스턴스 제공 함수
def get_supabase_client() -> Client:
    return SupabaseClient().client

class SupabaseAdminClient:
    """
    Supabase 백엔드 쓰기 작업을 위한 서비스 롤(관리자) 클라이언트.
    .env 파일의 SUPABASE_URL 및 SUPABASE_SERVICE_KEY를 사용합니다.
    """
    _instance = None
    _client: Client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SupabaseAdminClient, cls).__new__(cls)
            cls._instance._initialize_client()
        return cls._instance

    def _initialize_client(self):
        url: str = os.environ.get("SUPABASE_URL")
        key: str = os.environ.get("SUPABASE_SERVICE_KEY")
        
        if not url or not key:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("SUPABASE_URL or SUPABASE_SERVICE_KEY is not set in environment variables.")
        else:
            self._client = create_client(url, key)

    @property
    def client(self) -> Client:
        if not self._client:
            raise ValueError("Supabase admin client is not initialized. Check your environment variables.")
        return self._client

def get_supabase_admin_client() -> Client:
    return SupabaseAdminClient().client
