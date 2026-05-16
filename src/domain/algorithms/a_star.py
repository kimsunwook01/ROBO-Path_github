import math
import heapq
import itertools
from typing import List, Dict, Optional
from uuid import UUID

from src.domain.models.node import Node
from src.domain.models.edge import Edge, PlatformStat
from src.domain.models.robot import Robot
from src.domain.algorithms.cost_calculator import calculate_edge_cost

def heuristic(node_a: Node, node_b: Node) -> float:
    """두 노드 간의 3차원 유클리디안 거리를 활용한 휴리스틱 함수"""
    return math.sqrt((node_a.x - node_b.x)**2 + (node_a.y - node_b.y)**2 + (node_a.z - node_b.z)**2)

def build_graph(nodes: List[Node], edges: List[Edge], robot: Robot) -> Dict[UUID, Dict[UUID, float]]:
    """
    Node와 Edge 리스트를 기반으로 A* 탐색을 위한 인접 리스트 형태의 그래프(dict)를 빌드합니다.
    """
    graph: Dict[UUID, Dict[UUID, float]] = {node.id: {} for node in nodes}
    
    platform = robot.platform
    weights = robot.weight_profile
    
    for edge in edges:
        # edge에 연결된 노드가 node 리스트에 없는 경우 예외 처리
        if edge.from_node_id not in graph or edge.to_node_id not in graph:
            continue
            
        # 해당 플랫폼에 대한 통계가 있는지 확인
        raw_stats = edge.platform_stats.get(platform)
        
        # 방어적 프로그래밍: Pydantic이 자동 파싱을 못하고 dict로 남겨두었을 경우를 대비
        if isinstance(raw_stats, dict):
            stats = PlatformStat(**raw_stats)
        else:
            stats = raw_stats
        
        # 비용 산출
        cost = calculate_edge_cost(edge.distance_m, stats, weights)
        
        # 양방향 주행 가능 그래프로 구성
        graph[edge.from_node_id][edge.to_node_id] = cost
        graph[edge.to_node_id][edge.from_node_id] = cost
        
    return graph

def a_star_search(start_node: Node, goal_node: Node, nodes: List[Node], edges: List[Edge], robot: Robot) -> List[UUID]:
    """
    순수 도메인 모델 기반 A* 최적 경로 탐색 알고리즘
    
    Args:
        start_node: 출발지 노드 객체
        goal_node: 목적지 노드 객체
        nodes: 전체 노드 리스트 (탐색 공간)
        edges: 전체 엣지 리스트 (탐색 공간)
        robot: 경로를 주행할 로봇 모델 (플랫폼 특성 및 가중치 참조용)
        
    Returns:
        List[UUID]: 시작점부터 도착점까지 거쳐가는 순서대로 나열된 Node ID의 리스트. 경로가 없을 경우 빈 리스트 반환.
    """
    node_map = {node.id: node for node in nodes}
    
    # 출발지나 목적지가 노드 리스트에 존재하지 않으면 실패
    if start_node.id not in node_map or goal_node.id not in node_map:
        return []
        
    # 노드와 엣지, 로봇 속성을 이용해 이동 가능 그래프 빌드
    graph = build_graph(nodes, edges, robot)
    
    open_set = []
    counter = itertools.count()
    # (f_score, count, node_id) 형태로 우선순위 큐에 삽입하여 UUID 대소 비교 차단 및 안정적 정렬 보장
    heapq.heappush(open_set, (0.0, next(counter), start_node.id))
    
    # 경로 재구성을 위한 딕셔너리 (자신이 어디서 왔는지 추적)
    came_from: Dict[UUID, UUID] = {}
    
    # 출발점으로부터 특정 노드까지 도달하는 데 걸린 실제 비용의 합
    g_score: Dict[UUID, float] = {node.id: float('inf') for node in nodes}
    g_score[start_node.id] = 0.0
    
    # f_score = g_score + heuristic. 시작점 초기화
    f_score: Dict[UUID, float] = {node.id: float('inf') for node in nodes}
    f_score[start_node.id] = heuristic(start_node, goal_node)
    
    while open_set:
        # 가장 비용(f_score)이 낮은 노드를 꺼냄
        current_f, _, current_id = heapq.heappop(open_set)
        
        # 목적지에 도달한 경우
        if current_id == goal_node.id:
            path = [current_id]
            while current_id in came_from:
                current_id = came_from[current_id]
                path.append(current_id)
            return path[::-1]  # 역순으로 추적했으므로 다시 뒤집어서 반환
            
        current_node = node_map[current_id]
        
        # 인접 노드 탐색
        for neighbor_id, cost in graph[current_id].items():
            tentative_g_score = g_score[current_id] + cost
            
            # 더 나은(비용이 적은) 경로를 발견한 경우
            if tentative_g_score < g_score[neighbor_id]:
                came_from[neighbor_id] = current_id
                g_score[neighbor_id] = tentative_g_score
                
                neighbor_node = node_map[neighbor_id]
                f_score[neighbor_id] = tentative_g_score + heuristic(neighbor_node, goal_node)
                
                # 우선순위 큐에 새로운 비용과 함께 삽입 (counter를 통해 f_score가 같을 경우 삽입 순서로 안정적 정렬)
                heapq.heappush(open_set, (f_score[neighbor_id], next(counter), neighbor_id))
                
    # 도착 가능한 경로를 찾지 못한 경우
    return []
