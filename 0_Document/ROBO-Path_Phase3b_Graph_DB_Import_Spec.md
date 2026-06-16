# Phase 3b: 맵 덤프 데이터 DB 적재 및 그래프 변환 명세서 (Map Import Specification)

> 작성일: 2026-06-17  
> 대상 파이프라인: `scene_dump.json` → Python Backend → Supabase DB (`nodes`, `base_locations`, `map_edges`)

---

## 1. 목적 및 개요

Unity 시뮬레이터에서 덤프된 `scene_dump.json` 파일을 파싱하여, 백엔드 A* 알고리즘 구동 및 통계 누적의 토대가 되는 Supabase 데이터베이스 테이블에 노드(Nodes)와 엣지(Edges) 데이터를 Upsert 처리하는 파이프라인을 구축한다.

---

## 2. 프로젝트 현황 대조 및 사전 검증

본 계획을 수립하기 위해 프로젝트의 현재 상태를 대조/검증한 결과입니다.

| 검증 항목 | 확인 결과 | 조치 필요 사항 |
|-----------|-----------|----------------|
| **DB 스키마** (`ROBO-Path_Supabase_DB_Architecture.md`) | `nodes`, `base_locations`, `map_edges` 테이블 정의 및 구조 확인됨. | 스키마 일치. |
| **덤프 포맷** (`ROBO-Path_Scene_Dump_Specification.md`) | `summary`, `nodes`, `tiles`, `overlay_tiles`, `obstacles`, `adjacency` 섹션 분리 확인됨. | Python 파싱 시 `nodes`, `tiles`를 `Node`로 변환, `adjacency`를 `Edge`로 변환 필요. |
| **도메인 모델** (`src/domain/models/`) | `Node`, `BaseLocation`, `Edge` Pydantic 모델 존재 확인됨. | 변환 후 이 모델들로 데이터 무결성 검증. |
| **DB 레포지토리** (`src/infrastructure/database/`) | `SupabaseNodeRepository`, `SupabaseEdgeRepository` 존재하나 `get` 계열 조회 메서드만 있음. | 대량 데이터 삽입을 위한 **`upsert_batch()` 메서드 신규 구현 필요**. |

---

## 3. 구현 단계 (작업 세분화)

총 4개의 세부 작업으로 나누어 진행합니다.

### STEP 1. DB Repository에 Upsert 기능 추가
**대상 파일:** 
- `src/application/interfaces.py` (인터페이스 확장)
- `src/infrastructure/database/supabase_node_repo.py`
- `src/infrastructure/database/supabase_edge_repo.py`

**작업 내용:**
- Supabase 클라이언트를 이용해 대량의 레코드를 한 번에 처리하는 `upsert_nodes(nodes: List[Node])`와 `upsert_edges(edges: List[Edge])` 메서드를 구현.
- `base_locations` 조인 로직 대응 (부모 `nodes` 먼저 Upsert 후 `base_locations` Upsert).

### STEP 2. `MapImportService` 구현 (도메인 변환 로직)
**대상 파일:** `src/application/services/map_import_service.py` (신규)

**작업 내용:**
- **노드 파싱:** `scene_dump.json`의 `tiles` 섹션을 읽어 3D 좌표($x, y, z$)와 고유 ID 확보. `node_type`은 `'BASE'`로 고정.
- **거점 파싱:** `nodes` 섹션을 읽어 `location_usage` 매핑 (충전소, 픽업지 등).
- **엣지 파싱:** `adjacency` 섹션을 순회하여 양방향 엣지 쌍 생성.
- **거리 계산:** $x, y, z$ 유클리드 거리를 계산하여 `distance_m`에 할당.
- **초기화:** `platform_stats`는 비어있는 초기 상태 `{"wheeled": {}, "legged": {}}`로 생성.

### STEP 3. CLI 실행 스크립트 작성
**대상 파일:** `src/scripts/import_map_dump.py` (신규)

**작업 내용:**
- `.env`에서 Supabase 자격 증명 로드.
- `scene_dump.json` 파일 경로를 인자로 받는 CLI 스크립트 작성.
- `MapImportService`를 호출하여 전체 파이프라인 트리거.
- 실행 결과(삽입된 노드 및 엣지 개수) 콘솔 출력 로깅.

### STEP 4. 검증 및 단위 테스트 (Unit Tests)
**대상 파일:** `tests/test_map_import_service.py` (신규)

**작업 내용:**
- 소규모 Mock JSON(노드 2개, 엣지 1개)을 사용하여 `MapImportService`의 파싱 및 유클리드 거리 계산 정확도 검증.
- DB Mocking을 통한 Upsert 호출 횟수 검증.

---

## 4. 제약 사항 및 고려 사항
- **멱등성(Idempotency):** 동일한 덤프 파일을 여러 번 임포트해도 DB 데이터가 중복 생성되지 않고 기존 ID를 기준으로 덮어쓰기(Upsert) 되어야 합니다.
- **성능:** 약 3000개 이상의 노드와 그에 상응하는 엣지가 발생하므로, Supabase REST API 호출 횟수를 줄이기 위해 반드시 **배치(Batch)** 형태로 묶어서 전송해야 합니다. (기본적으로 Supabase `.insert()`/`.upsert()`는 리스트 전송을 지원함)
