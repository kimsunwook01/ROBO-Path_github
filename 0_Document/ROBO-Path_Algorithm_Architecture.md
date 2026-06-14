# ROBO-Path 알고리즘 아키텍처 및 상세 명세 (Algorithm Architecture)

이 문서는 ROBO-Path 프로젝트의 핵심 비즈니스 로직인 **순수 도메인 알고리즘**의 구조, 연산식, 그리고 클린 아키텍처 관점에서의 구현 방침을 정의합니다.

모든 도메인 알고리즘은 `src/domain/algorithms/` 경로에 위치하며, 외부 라이브러리(Supabase, Streamlit, ROS2 등)에 대한 의존성을 전혀 가지지 않는 순수한 Python 함수 및 클래스로 작성됩니다.

---

## 1. 플랫폼 기반 비용 산출 알고리즘 (Platform-Aware Cost Calculation)

로봇 기종(Platform)의 물리적 특성(Weight Profile)과 엣지의 주행 누적 통계(Platform Stats)를 결합하여 최종적인 **주행 비용(Cost)**을 스칼라 값으로 반환합니다. 

### 1.1 입력 데이터 (Input Models)
- `distance_m`: 엣지의 물리적 길이 (미터)
- `platform_stats`: 특정 기종(Wheeled, Legged 등)이 해당 엣지에서 기록한 평균 물리 지표.
  - $L$ (Load Factor): 부하율 ($0.0 \sim 1.0$)
  - $S$ (Stability Index): 안정성 지수 ($0.0 \sim 1.0$, 1에 가까울수록 안정적)
  - $E$ (Efficiency Index): 효율성 지수 ($0.0 \sim 1.0$, 1에 가까울수록 고효율)
- `weight_profile`: 로봇 객체가 가지고 있는 기종별 지표 민감도 (가중치).
  - $W_L$: 부하 민감도
  - $W_S$: 안정성 민감도
  - $W_E$: 효율성 민감도

### 1.2 비용 산출 수식 (Cost Formula)
경로 탐색 시 물리적 거리(`distance_m`)를 기본 비용으로 하되, 통행 정책 계수(`cost_multiplier`)와 하드웨어 피드백 페널티를 곱하여 거리가 짧아도 주행이 험난하거나 정책상 억제된 경로의 가중치를 높입니다.

$$
Cost = distance\_m \times cost\_multiplier \times \left[ 1 + \left( W_L \times L \right) + \left( W_S \times (1 - S) \right) + \left( W_E \times (1 - E) \right) \right]
$$

- $S$와 $E$는 1에 가까울수록 좋은 지표이므로, $(1 - S)$와 $(1 - E)$로 역산하여 페널티로 변환합니다.
- 지표 데이터가 존재하지 않는 미탐험 엣지의 경우, 페널티 항을 0으로 간주하여 순수 물리적 거리($distance\_m$)만으로 비용을 계산합니다.

### 1.3 구현 위치
- `src/domain/algorithms/cost_calculator.py`
- 함수 시그니처: `calculate_edge_cost(distance_m: float, stats: PlatformStats, weights: WeightProfile) -> float`

---

## 2. A* 최적 경로 탐색 알고리즘 (A* Pathfinding Algorithm)

도메인 모델의 Node와 Edge 리스트를 기반으로, 출발지 노드에서 목적지 노드까지의 최적 경로를 탐색하는 순수 그래프 탐색 로직입니다.

### 2.1 알고리즘 구성요소
- **그래프 빌더 (Graph Builder):** 
  플랫한 형태의 `Edge` 리스트를 입력받아 각 `Node` ID를 키로 하는 인접 리스트(Adjacency List) 형태의 사전(dict)으로 변환합니다. 변환 과정에서 1.2의 비용 산출 알고리즘을 호출하여 각 간선의 $Cost$를 확정합니다.
- **휴리스틱 함수 (Heuristic Function - $h(n)$):**
  현재 노드 $n$과 목적지 노드 사이의 유클리디안 거리(Euclidean Distance)를 사용합니다.
  $$h(n) = \sqrt{(x_{goal} - x_n)^2 + (y_{goal} - y_n)^2 + (z_{goal} - z_n)^2}$$
- **평가 함수 (Evaluation Function - $f(n)$):**
  $$f(n) = g(n) + h(n)$$
  (단, $g(n)$은 시작 노드부터 현재 노드 $n$까지 누적된 실제 주행 비용(Cost))

### 2.2 구현 위치
- `src/domain/algorithms/a_star.py`
- 함수 시그니처: `a_star_search(start_node: Node, goal_node: Node, nodes: List[Node], edges: List[Edge], robot: Robot) -> List[UUID]`
- 반환값: 시작점부터 도착점까지 연결된 Node들의 ID 리스트. (경로가 없을 경우 빈 리스트 반환)

---

## 3. 통계 지표 누적 연산 알고리즘 (Statistics Aggregation Algorithm)

새로운 `MissionLog`가 수집될 때마다 해당 경로(Edge)의 평균 `platform_stats`를 동적으로 갱신합니다. 누적 이동 평균(Cumulative Moving Average) 방식을 사용하여 모든 과거 데이터를 조회하지 않고도 O(1) 시간 복잡도로 평균을 계산합니다.

### 3.1 갱신 수식 (Update Formula)
현재 엣지의 누적 방문 횟수를 $N$, 기존 평균값을 $M_{old}$, 새로 수집된 지표를 $x_{new}$라고 할 때:

$$
M_{new} = \frac{M_{old} \times N + x_{new}}{N + 1}
$$

부하율($L$), 안정성($S$), 효율성($E$) 각각에 대해 위 수식을 적용하여 독립적으로 업데이트합니다.

### 3.2 구현 위치
- `src/domain/algorithms/statistics.py`
- 함수 시그니처: `update_platform_stats(current_stats: PlatformStats, visit_count: int, new_log: MissionLog) -> PlatformStats`

---

## 4. 의존성 (Dependencies) 및 제약 사항

> [!WARNING]  
> 본 알고리즘들은 `src/domain/models/` 에 정의된 Pydantic 모델과 순수 내장 자료구조(`dict`, `list`, `heapq` 등)만을 사용해야 합니다.
> DB 연결 객체나 네트워크 요청 객체가 알고리즘의 인자로 전달되어서는 **절대** 안 됩니다.

- 데이터 조회 및 저장은 Application 계층(`src/application/services/`)이 담당합니다.
- Service 계층이 DB에서 Node와 Edge 리스트를 가져와 Pydantic 모델로 변환한 뒤, 이 알고리즘 함수들에 인자로 주입(Inject)하는 방식으로 동작합니다.
