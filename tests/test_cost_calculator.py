import pytest
from src.domain.algorithms.cost_calculator import calculate_edge_cost
from src.domain.models.edge import PlatformStat

def test_no_feedback_data():
    """피드백 데이터가 없는 엣지(stats=None)는 Cost == distance_m 인지 검증"""
    distance = 10.0
    cost = calculate_edge_cost(distance, None, {"W_L": 1.0, "W_S": 1.0, "W_E": 1.0})
    assert cost == distance

def test_traversal_count_zero():
    """피드백 데이터가 있으나 traversal_count가 0인 경우 Cost == distance_m 인지 검증"""
    distance = 10.0
    stats = PlatformStat(average_load_factor=0.5, average_stability=0.5, average_efficiency=0.5, traversal_count=0)
    cost = calculate_edge_cost(distance, stats, {"W_L": 1.0, "W_S": 1.0, "W_E": 1.0})
    assert cost == distance

def test_flat_vs_rough_cost():
    """평지 수준 지표가 험지 수준 지표보다 낮은 Cost를 산출하는지 검증"""
    distance = 10.0
    weight_profile = {"W_L": 1.0, "W_S": 1.0, "W_E": 1.0}
    
    # 평지 지표: 부하율 낮음(0.1), 안정성 높음(0.9), 효율성 높음(0.9)
    flat_stats = PlatformStat(average_load_factor=0.1, average_stability=0.9, average_efficiency=0.9, traversal_count=1)
    flat_cost = calculate_edge_cost(distance, flat_stats, weight_profile)
    
    # 험지 지표: 부하율 높음(0.8), 안정성 낮음(0.4), 효율성 낮음(0.3)
    rough_stats = PlatformStat(average_load_factor=0.8, average_stability=0.4, average_efficiency=0.3, traversal_count=1)
    rough_cost = calculate_edge_cost(distance, rough_stats, weight_profile)
    
    assert flat_cost < rough_cost

def test_efficiency_over_one():
    """efficiency가 1.0을 초과하는 경우 페널티가 감소하여 Cost가 낮아지는지 검증"""
    distance = 10.0
    weight_profile = {"W_L": 1.0, "W_S": 1.0, "W_E": 1.0}
    
    # 일반 지표: 효율성 1.0
    normal_stats = PlatformStat(average_load_factor=0.2, average_stability=0.9, average_efficiency=1.0, traversal_count=1)
    normal_cost = calculate_edge_cost(distance, normal_stats, weight_profile)
    
    # 내리막 지표: 효율성 1.5 (매우 빠름)
    downhill_stats = PlatformStat(average_load_factor=0.2, average_stability=0.9, average_efficiency=1.5, traversal_count=1)
    downhill_cost = calculate_edge_cost(distance, downhill_stats, weight_profile)
    
    assert downhill_cost < normal_cost

def test_weight_profile_impact():
    """가중치 프로필(W_L, W_S, W_E)이 비용에 올바르게 반영되는지 검증"""
    distance = 10.0
    stats = PlatformStat(average_load_factor=0.8, average_stability=0.9, average_efficiency=0.9, traversal_count=1)
    
    # 부하율에 민감한 로봇 (W_L 높음)
    load_sensitive_profile = {"W_L": 0.8, "W_S": 0.1, "W_E": 0.1}
    load_sensitive_cost = calculate_edge_cost(distance, stats, load_sensitive_profile)
    
    # 부하율에 둔감한 로봇 (W_L 낮음)
    load_insensitive_profile = {"W_L": 0.1, "W_S": 0.1, "W_E": 0.1}
    load_insensitive_cost = calculate_edge_cost(distance, stats, load_insensitive_profile)
    
    assert load_sensitive_cost > load_insensitive_cost

def test_admissibility_safety_net():
    """A* 휴리스틱의 Admissibility 보장을 위해 cost_multiplier나 효율성이 극단적일 때 
    최종 비용이 distance_m 미만으로 떨어지지 않는지 검증"""
    distance = 10.0
    weight_profile = {"W_L": 1.0, "W_S": 1.0, "W_E": 1.0}
    
    # 극단적으로 빠른 내리막 (효율성 3.0 -> penalty는 음수가 됨)
    # cost_multiplier도 0.5 (1.0 미만)으로 설정
    stats = PlatformStat(average_load_factor=0.0, average_stability=1.0, average_efficiency=3.0, traversal_count=1)
    
    cost = calculate_edge_cost(distance, stats, weight_profile, cost_multiplier=0.5)
    
    # distance * multiplier * (1 + penalty) < distance 가 되지만,
    # max(distance, cost) 방어 로직에 의해 최소 distance여야 함
    assert cost >= distance
    assert cost == distance

def test_admissibility_safety_net_no_stats():
    """stats가 없는 미주행 엣지에 대해 cost_multiplier가 1.0 미만일 때 
    단일 출구의 클램프가 작동하여 distance_m 미만으로 떨어지지 않는지 검증"""
    distance = 10.0
    weight_profile = {"W_L": 1.0, "W_S": 1.0, "W_E": 1.0}
    
    # 조기 반환 대상(stats=None)이지만 cost_multiplier 때문에 거리보다 비용이 싸지는 상황
    cost = calculate_edge_cost(distance, None, weight_profile, cost_multiplier=0.5)
    
    # distance * 0.5 < distance 가 되지만,
    # max(distance, cost) 방어 로직에 의해 최소 distance여야 함
    assert cost == distance
