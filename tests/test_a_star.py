import pytest
import uuid
from src.domain.algorithms.a_star import a_star_search, build_graph
from src.domain.models.node import Node
from src.domain.models.edge import Edge, PlatformStat
from src.domain.models.metadata import Robot

def create_node(x, y, z, terrain_tag="Terrain_Flat"):
    return Node(id=uuid.uuid4(), x=x, y=y, z=z, node_type="DISCOVERED", terrain_tag=terrain_tag)

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

def test_hard_blocking_by_terrain():
    """지형 태그(terrain_tag) 기반 하드 차단(traversable: False)이 작동하는지 검증"""
    n1 = create_node(0, 0, 0, "Path_Flat")
    n2 = create_node(10, 0, 0, "Path_Stair") # 휠 로봇 통행 불가 타일
    n3 = create_node(20, 0, 0, "Path_Flat")
    
    nodes = [n1, n2, n3]
    
    e1 = Edge(id=uuid.uuid4(), from_node_id=n1.id, to_node_id=n2.id, distance_m=10.0, platform_stats={})
    e2 = Edge(id=uuid.uuid4(), from_node_id=n2.id, to_node_id=n3.id, distance_m=10.0, platform_stats={})
    
    edges = [e1, e2]
    
    # 휠 로봇 프로필: Path_Stair는 traversable: False
    wheeled_profile = {
        "W_L": 1.0, 
        "W_S": 1.0, 
        "W_E": 1.0,
        "cost_profiles": {
            "terrains": {
                "Path_Stair": {"traversable": False, "cost_multiplier": 5.0}
            }
        }
    }
    wheeled_robot = Robot(id=uuid.uuid4(), name="WheelBot", platform="wheeled", weight_profile=wheeled_profile)
    
    path_wheeled = a_star_search(n1, n3, nodes, edges, wheeled_robot)
    assert path_wheeled == [] # 차단되어 경로 없음
    
    # 보행형 로봇 프로필: Path_Stair는 traversable: True
    legged_profile = {
        "W_L": 1.0, 
        "W_S": 1.0, 
        "W_E": 1.0,
        "cost_profiles": {
            "terrains": {
                "Path_Stair": {"traversable": True, "cost_multiplier": 1.5}
            }
        }
    }
    legged_robot = Robot(id=uuid.uuid4(), name="LegBot", platform="legged", weight_profile=legged_profile)
    
    path_legged = a_star_search(n1, n3, nodes, edges, legged_robot)
    assert path_legged == [n1.id, n2.id, n3.id] # 보행형은 통과

def test_graph_directional_blocking():
    """역방향 엣지 생성 시 대칭으로 인한 차단 누수(재생성) 결함을 검증한다."""
    n1 = create_node(0, 0, 0, "Path_Flat")
    n2 = create_node(10, 0, 0, "Path_Stair") # 휠 로봇 진입 불가
    n3 = Node(id=uuid.uuid4(), x=0, y=0, z=0, node_type="BASE", terrain_tag="Node_Destination") # 거점 (항상 진입 가능)
    
    nodes = [n1, n2, n3]
    
    # 평지 <-> 계단, 평지 <-> 거점
    e1 = Edge(id=uuid.uuid4(), from_node_id=n1.id, to_node_id=n2.id, distance_m=10.0, platform_stats={})
    e2 = Edge(id=uuid.uuid4(), from_node_id=n1.id, to_node_id=n3.id, distance_m=10.0, platform_stats={})
    edges = [e1, e2]
    
    wheeled_profile = {
        "cost_profiles": {
            "terrains": {
                "Path_Stair": {"traversable": False, "cost_multiplier": 5.0}
            }
        }
    }
    wheeled_robot = Robot(id=uuid.uuid4(), name="WheelBot", platform="wheeled", weight_profile=wheeled_profile)
    
    legged_profile = {
        "cost_profiles": {
            "terrains": {
                "Path_Stair": {"traversable": True, "cost_multiplier": 1.5}
            }
        }
    }
    legged_robot = Robot(id=uuid.uuid4(), name="LegBot", platform="legged", weight_profile=legged_profile)
    
    graph_wheeled = build_graph(nodes, edges, wheeled_robot)
    graph_legged = build_graph(nodes, edges, legged_robot)
    
    # 휠 로봇: 계단(n2)으로 진입하는 엣지 수 == 0
    # 모든 노드에서 n2.id를 목적지로 하는 엣지를 찾는다
    entering_n2_wheeled = sum(1 for from_id, to_dict in graph_wheeled.items() if n2.id in to_dict)
    assert entering_n2_wheeled == 0
    
    # 반면 계단(n2)에서 평지(n1)로 나오는 엣지는 존재해야 함 (만약 로봇이 모종의 이유로 계단에 있다면 평지로는 탈출 가능해야 함)
    assert n1.id in graph_wheeled[n2.id]
    
    # 보행 로봇: 계단(n2)으로 진입 가능
    entering_n2_legged = sum(1 for from_id, to_dict in graph_legged.items() if n2.id in to_dict)
    assert entering_n2_legged > 0
    
    # 휠 로봇: 거점(n3)은 고립되지 않고 평지(n1)에서 진입 가능해야 함
    entering_n3_wheeled = sum(1 for from_id, to_dict in graph_wheeled.items() if n3.id in to_dict)
    assert entering_n3_wheeled > 0
