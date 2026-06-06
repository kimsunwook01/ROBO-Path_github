# 애플리케이션 서비스 계층 설계 및 명세서

이 문서는 ROBO-Path 프로젝트의 핵심 도메인 로직(A* 경로 탐색, 피드백 통계)을 데이터 영속성 계층(DB Repository)과 연결하는 애플리케이션 서비스 계층(Application Service Layer)에 대한 상세 명세입니다.

## 1. 개요 (Overview)
`src/application/services` 모듈은 클린 아키텍처 원칙에 따라 순수 도메인 로직과 외부 인프라(DB, UI 등)를 분리하는 중재자 역할을 합니다. 
도메인 모델과 알고리즘은 외부 라이브러리(DB 클라이언트 등)를 알지 못하며, 서비스 클래스가 의존성 주입(DI)된 인터페이스(Protocol)를 통해 데이터를 가져와 도메인에 전달하고 그 결과를 다시 DB에 반영합니다.

## 2. 주요 서비스 클래스

### 2.1 PathPlanningService
**목적:** 주어진 출발지와 목적지 간의 플랫폼 맞춤형 최적 경로 탐색.
- **의존성:** `NodeRepository`, `EdgeRepository`
- **주요 기능 (`find_path`):**
  1. `start_node_id`와 `goal_node_id`를 기반으로 유효한 출발지 및 도착지 노드 객체를 데이터베이스에서 로드합니다.
  2. 전체 탐색 공간(노드, 엣지 그래프)을 가져옵니다. 
  3. 로봇 기종(`Robot`) 객체와 함께 순수 도메인 함수인 `a_star_search`를 호출합니다.
  4. 도메인 알고리즘은 휴리스틱(유클리디안 3D 직선거리)과 기종별 엣지 통계를 기반으로 비용을 산출해 최단 경로 UUID 리스트를 반환합니다.

### 2.2 FeedbackAggregationService
**목적:** 주행 종료 후 수집된 로그(Log)를 기반으로 해당 엣지(Edge)의 기종별(Platform) 통계 데이터를 갱신.
- **의존성:** `EdgeRepository`
- **주요 기능 (`process_new_log`):**
  1. `edge_id`에 해당하는 엣지 객체를 DB에서 로드합니다.
  2. 엣지 내부의 `platform_stats` 속성에서 현재 주행을 수행한 기종(`robot.platform`)의 기존 통계를 가져옵니다.
  3. 도메인 함수인 `update_platform_stats`를 호출하여 새 주행 로그(`MissionLog`)와 기존 통계를 O(1) 이동 평균(Cumulative Moving Average)으로 병합합니다.
  4. 갱신된 통계를 엣지 객체에 재할당하고 `edge_repo.update_edge(edge)`를 호출하여 영속화합니다.

## 3. Repository 인터페이스 확장 내역
서비스 계층이 원활히 동작하기 위해 `src/application/interfaces/edge_repository.py` 프로토콜에 다음 메서드가 정의되었습니다.
- `get_all_edges(self) -> List[Edge]`: A* 알고리즘 구동 전, 전체 탐색 가능한 그래프를 생성하기 위해 모든 엣지를 메모리로 가져옵니다.
- `update_edge(self, edge: Edge) -> Edge`: `FeedbackAggregationService`에서 통계가 변경된 엣지를 DB에 저장하고 최신화된 객체를 반환합니다.

## 4. 향후 고려사항 (Future Works)
- 현재 `PathPlanningService`는 탐색 전 모든 노드와 엣지를 메모리에 로드하는 방식(`get_all_nodes`, `get_all_edges`)을 취하고 있습니다. 차후 맵의 규모(수만 개의 노드/엣지)가 커지거나 다중 로봇 탐색이 빈번해질 경우, DB 쿼리를 최적화하여 Bounding Box(탐색 영역) 내부의 엣지만 동적으로 가져오도록 쿼리 로직을 개선할 수 있습니다.
