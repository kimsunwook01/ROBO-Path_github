# ROBO-Path 소프트웨어 아키텍처 설계서 (Software Architecture Design)

## 1. 아키텍처 철학 (Design Philosophy)

본 프로젝트는 초기의 무계획적인 개발(Vibe Coding)로 인해 발생할 수 있는 스파게티 코드와 강결합(Tight Coupling) 문제를 원천적으로 방지하기 위해 **클린 아키텍처(Clean Architecture)** 및 **포트 앤 어댑터(Hexagonal Architecture)** 패턴을 일부 차용합니다.

**핵심 목표:**
1. **관심사의 분리 (Separation of Concerns):** UI(Streamlit), 데이터베이스(Supabase), 외부 통신(ROS2, Gemini)은 핵심 비즈니스 로직(A* 알고리즘)과 철저히 분리됩니다.
2. **의존성 역전 원칙 (Dependency Inversion Principle):** 상위 계층(도메인 로직)은 하위 계층(DB, 외부 API)에 의존하지 않습니다. 오직 추상화된 인터페이스(Protocol)에만 의존합니다.
3. **결합도 최소화 (Low Coupling):** 특정 기술(예: Supabase, Streamlit)을 나중에 다른 기술(예: MySQL, React)로 교체하더라도 핵심 코드는 단 한 줄도 수정하지 않도록 설계합니다.

---

## 2. 계층형 폴더 구조 (Layered Directory Structure)

디렉토리 구조는 아키텍처의 의도를 명확히 반영합니다. 의존성은 항상 **바깥쪽(Infrastructure, UI)에서 안쪽(Domain, Core)**으로만 향해야 합니다.

### 2.1 소프트웨어 계층 구조 (`src/`)

핵심 애플리케이션 코드의 4계층 구조입니다. 의존성은 항상 **바깥쪽(Infrastructure, UI)에서 안쪽(Domain)**으로만 향해야 합니다.

```text
src/
├── domain/                      # 1. 도메인 계층 (가장 안쪽, 외부 의존성 없음) ✅ 구현 완료
│   ├── models/                  # 순수 Pydantic 데이터 모델
│   │   ├── edge.py              # Edge 모델 (platform_stats JSONB 포함)
│   │   ├── node.py              # Node, BaseLocation, DiscoveredNode 계층 모델
│   │   ├── log.py               # MissionLog, Incident 모델
│   │   └── metadata.py          # MapMetadata, Robot 모델
│   └── algorithms/              # 순수 도메인 알고리즘 (I/O 코드 절대 포함 불가)
│       ├── a_star.py            # 플랫폼 가중치 기반 A* 경로 탐색
│       ├── cost_calculator.py   # Edge 비용 함수 (부하율/안정성/효율성 가중합)
│       └── statistics.py        # 하드웨어 피드백 통계 누적(Aggregation) 로직
│
├── application/                 # 2. 애플리케이션 계층 (Use Case)
│   ├── interfaces/              # 외부 인프라가 구현해야 할 Repository Protocol ✅
│   │   ├── edge_repository.py
│   │   └── node_repository.py
│   └── services/                # 도메인 + 인터페이스 조합 비즈니스 흐름 제어 🔲 미구현
│
├── infrastructure/              # 3. 인프라 계층 (외부 기술 구현체)
│   ├── database/                # Supabase 클라이언트 및 Repository 구현체 ✅
│   │   ├── client.py            # Supabase 연결 싱글톤 클라이언트
│   │   ├── supabase_edge_repo.py
│   │   └── supabase_node_repo.py
│   ├── storage/                 # 라즈베리파이 로컬 파일 시스템 제어 구현체 🔲 미구현
│   │   └── api.py               # (예정) FastAPI 스토리지 서버 진입점
│   ├── bridge/                  # 시뮬레이터 통신 브릿지 (경량 지표 전송용) 🔲 미구현
│   │   └── bridge.py            # (예정) Unity -> Supabase 메타데이터 전송
│   └── llm/                     # Google Gemini API 호출 구현체 🔲 미구현
│
└── presentation/                # 4. 프레젠테이션 계층 (UI 및 진입점)
    ├── dashboard/               # Streamlit 관제 웹 화면 🔲 미구현
    │   └── app.py               # (예정) 관제 대시보드 진입점
    └── ros2_bridge/             # WebSocket 클라이언트 브릿지 (시뮬레이터 명령 수신) 🔲 미구현
        └── bridge.py            # (예정) 웹소켓 명령 수신 진입점
```

### 2.2 전체 프로젝트 루트 구조

에지 서버 인프라 파일까지 포함한 전체 리포지토리 루트 구조입니다.

```text
ROBO-Path_project/               # 리포지토리 루트
├── .github/
│   └── workflows/
│       ├── supabase-migrations.yml  # Supabase DB 마이그레이션 자동 배포 ✅
│       └── deploy-to-pi.yml         # 라즈베리파이 Self-Hosted Runner 배포 🔲 미구현
│
├── config/                      # 라즈베리파이 전용 시스템 설정 (Git 버전 관리됨)
│   ├── pi_services/
│   │   ├── robo-path-api.service    # FastAPI Systemd 서비스 유닛
│   │   └── robo-path-web.service    # Streamlit Systemd 서비스 유닛
│   └── nginx/
│       └── robo-path.conf           # Nginx 리버스 프록시 설정
│
├── scripts/                     # 파이 유지보수 셸 스크립트 (Git 버전 관리됨)
│   └── snapshot_env.sh              # apt/pip 환경 스냅샷 저장
│
├── src/                         # 소프트웨어 계층 구조 (위 2.1 참고)
├── supabase/                    # Supabase 마이그레이션 SQL 파일
├── tests/                       # 테스트 코드
├── 0_Document/                  # 프로젝트 기술 문서
├── requirements.txt             # Python 패키지 목록 (맥미니 + 파이 공용)
├── environment.yml              # Conda 환경 정의
└── .env                         # 환경 변수 (Git 추적 제외)
```

---

## 3. 코드 레벨 결합도 낮추기 전략 (Decoupling Strategies)

### 3.1 추상화(Interface) 기반의 저장소(Repository) 패턴
A* 알고리즘이나 비즈니스 로직이 `SupabaseClient`를 직접 임포트(Import)하여 사용하면 강결합이 발생합니다. 파이썬의 `typing.Protocol`을 사용하여 인터페이스만 정의하고, 실제 구현체는 인프라 계층으로 밀어냅니다.

```python
# src/application/interfaces/edge_repository.py
from typing import Protocol, List
from src.domain.models import Edge

class EdgeRepository(Protocol):
    def get_edges_by_platform(self, platform: str) -> List[Edge]:
        """플랫폼에 맞는 엣지 데이터를 가져오는 인터페이스"""
        pass

# src/infrastructure/database/supabase_edge_repo.py
from src.application.interfaces.edge_repository import EdgeRepository

class SupabaseEdgeRepository: # EdgeRepository 인터페이스의 실제 구현체
    def __init__(self, db_client):
        self.db = db_client
        
    def get_edges_by_platform(self, platform: str) -> List[Edge]:
        # 실제 Supabase 쿼리 로직
        response = self.db.table("map_edges").select("*").execute()
        # ... 변환 로직 ...
        return edges
```

### 3.2 의존성 주입 (Dependency Injection)
비즈니스 로직을 담당하는 서비스 클래스는 자신이 사용할 저장소가 Supabase인지 로컬 DB인지 알 필요가 없습니다. 생성자를 통해 인터페이스를 주입(Inject)받습니다.

```python
# src/application/services/path_planning_service.py
from src.application.interfaces.edge_repository import EdgeRepository
from src.domain.algorithms.a_star import a_star_search

class PathPlanningService:
    def __init__(self, edge_repo: EdgeRepository):
        # 의존성 주입 (결합도 낮춤)
        self.edge_repo = edge_repo
        
    def calculate_optimal_path(self, start_node_id: str, end_node_id: str, platform: str):
        # DB에서 데이터 가져오기 (실제 DB가 무엇이든 상관 없음)
        edges = self.edge_repo.get_edges_by_platform(platform)
        
        # 순수 도메인 로직(알고리즘) 실행
        return a_star_search(start_node_id, end_node_id, edges)
```

### 3.3. 프레젠테이션 계층의 제한
Streamlit 화면 파일(`app.py`) 안에서는 **절대 SQL 쿼리나 DB 통신 코드를 직접 작성하지 않습니다.** UI 계층은 오직 `Application` 계층의 Service 클래스만 호출해야 합니다.

---

## 4. 모듈 간 의존성 규칙 (Dependency Rule)

이 아키텍처를 유지하기 위해 다음 규칙을 엄격히 준수해야 합니다.
> [!IMPORTANT]
> **절대 금지 사항 (Anti-Patterns)**
> 1. `domain` 폴더 안의 파일이 `infrastructure`나 `presentation` 폴더의 파일을 `import` 하는 행위.
> 2. `domain/algorithms` 코드 내에 `.csv` 파일을 읽거나 API 통신을 하는 `requests` 라이브러리가 포함되는 행위. (입출력은 모두 `application` 계층에서 인자로 넘겨주어야 함)
> 3. Streamlit UI 코드에서 `supabase` 클라이언트를 직접 초기화하여 쿼리를 날리는 행위.

## 5. 결론 및 기대 효과
이러한 클린 아키텍처 구조를 잡고 가면 초기 클래스 설계 및 파일 분리 작업에 시간이 조금 더 소요될 수 있습니다. 
하지만 개발 중반 이후 DB 스키마가 변경되거나, 시뮬레이터가 변경되거나, UI 프레임워크가 변경되더라도 **오직 해당 인프라 어댑터 계층의 코드만 수정하면 되기 때문에** 시스템의 핵심 로직(A* 등)은 절대 망가지지 않는 견고한 프로젝트가 완성됩니다.
