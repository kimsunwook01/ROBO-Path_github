import pytest
import uuid
from src.domain.algorithms.a_star import a_star_search
from src.domain.models.node import Node
from src.domain.models.edge import Edge, PlatformStat
from src.domain.models.metadata import Robot

def create_node(x, y, z):
    return Node(id=uuid.uuid4(), x=x, y=y, z=z, node_type="DISCOVERED")

def test_simple_shortest_path():
    """단순 그래프(노드 3~4개)에서 최단 경로를 올바르게 반환하는지 검증"""
    n1 = create_node(0, 0, 0)
    n2 = create_node(10, 0, 0)
    n3 = create_node(20, 0, 0)
    
    nodes = [n1, n2, n3]
    
    # n1 -> n2 -> n3
    e1 = Edge(id=uuid.uuid4(), from_node_id=n1.id, to_node_id=n2.id, distance_m=10.0, platform_stats={})
    e2 = Edge(id=uuid.uuid4(), from_node_id=n2.id, to_node_id=n3.id, distance_m=10.0, platform_stats={})
    
    edges = [e1, e2]
    robot = Robot(id=uuid.uuid4(), name="TestBot", platform="wheeled", weight_profile={"W_L": 1.0, "W_S": 1.0, "W_E": 1.0})
    
    path = a_star_search(n1, n3, nodes, edges, robot)
    assert path == [n1.id, n2.id, n3.id]

def test_start_equals_goal():
    """출발지 == 도착지인 경우 처리 검증"""
    n1 = create_node(0, 0, 0)
    nodes = [n1]
    edges = []
    robot = Robot(id=uuid.uuid4(), name="TestBot", platform="wheeled", weight_profile={})
    
    path = a_star_search(n1, n1, nodes, edges, robot)
    assert path == [n1.id]

def test_no_path_exists():
    """경로가 존재하지 않는 경우 빈 리스트 반환 검증"""
    n1 = create_node(0, 0, 0)
    n2 = create_node(10, 0, 0)
    nodes = [n1, n2]
    edges = [] # 연결된 엣지가 없음
    robot = Robot(id=uuid.uuid4(), name="TestBot", platform="wheeled", weight_profile={})
    
    path = a_star_search(n1, n2, nodes, edges, robot)
    assert path == []

def test_nodes_not_in_list():
    """출발/도착 노드가 노드 리스트에 없을 때 빈 리스트 반환 검증"""
    n1 = create_node(0, 0, 0)
    n2 = create_node(10, 0, 0)
    n3 = create_node(20, 0, 0) # n3는 nodes 리스트에 안 들어감
    nodes = [n1, n2]
    edges = [Edge(id=uuid.uuid4(), from_node_id=n1.id, to_node_id=n3.id, distance_m=10.0, platform_stats={})]
    robot = Robot(id=uuid.uuid4(), name="TestBot", platform="wheeled", weight_profile={})
    
    path = a_star_search(n1, n3, nodes, edges, robot)
    assert path == []

def test_platform_aware_routing():
    """더 짧은 거리지만 비용이 높은 경로를 회피하고 우회 경로를 선택하는지 검증"""
    n1 = create_node(0, 0, 0)
    n2 = create_node(10, 0, 0)
    n3 = create_node(10, 10, 0)
    n4 = create_node(20, 0, 0)
    
    nodes = [n1, n2, n3, n4]
    
    # 직접 가는 경로: n1 -> n4 (거리는 짧으나 험지)
    rough_stats = PlatformStat(average_load_factor=0.9, average_stability=0.2, average_efficiency=0.2, traversal_count=5)
    e_direct = Edge(id=uuid.uuid4(), from_node_id=n1.id, to_node_id=n4.id, distance_m=20.0, platform_stats={"wheeled": rough_stats})
    
    # 우회하는 경로: n1 -> n2 -> n3 -> n4 (거리는 길지만 평지)
    flat_stats = PlatformStat(average_load_factor=0.1, average_stability=0.9, average_efficiency=0.9, traversal_count=5)
    e_detour1 = Edge(id=uuid.uuid4(), from_node_id=n1.id, to_node_id=n2.id, distance_m=10.0, platform_stats={"wheeled": flat_stats})
    e_detour2 = Edge(id=uuid.uuid4(), from_node_id=n2.id, to_node_id=n3.id, distance_m=10.0, platform_stats={"wheeled": flat_stats})
    e_detour3 = Edge(id=uuid.uuid4(), from_node_id=n3.id, to_node_id=n4.id, distance_m=14.14, platform_stats={"wheeled": flat_stats})
    
    edges = [e_direct, e_detour1, e_detour2, e_detour3]
    
    robot = Robot(id=uuid.uuid4(), name="TestBot", platform="wheeled", weight_profile={"W_L": 1.0, "W_S": 1.0, "W_E": 1.0})
    
    path = a_star_search(n1, n4, nodes, edges, robot)
    
    # 직항(n1->n4) 대신 우회로(n1->n2->n3->n4)를 선택해야 함
    assert path == [n1.id, n2.id, n3.id, n4.id]
