from typing import Dict, Any, Optional
from src.domain.models.edge import PlatformStat

def calculate_edge_cost(distance_m: float, stats: Optional[PlatformStat], weight_profile: Dict[str, Any]) -> float:
    """
    플랫폼(기종)의 가중치 프로필과 엣지의 주행 통계 지표를 결합하여 A* 알고리즘용 비용(Cost)을 산출합니다.
    
    Args:
        distance_m: 엣지의 물리적 거리(미터)
        stats: 특정 기종이 해당 엣지에서 기록한 평균 물리 지표 (없을 수 있음)
        weight_profile: 로봇 모델에 정의된 가중치 프로필 (W_L, W_S, W_E 등)
        
    Returns:
        float: 최종 산출된 주행 비용 스칼라 값
    """
    # 기본 가중치 설정 (설정되지 않았을 경우 1.0 적용)
    w_l = weight_profile.get("W_L", 1.0)
    w_s = weight_profile.get("W_S", 1.0)
    w_e = weight_profile.get("W_E", 1.0)
    
    if not stats or stats.traversal_count == 0:
        # 주행 데이터가 없는 엣지의 경우 순수 물리적 거리만 비용으로 산출
        return distance_m
        
    l = stats.average_load_factor
    s = stats.average_stability
    e = stats.average_efficiency
    
    # 안정성과 효율성은 1에 가까울수록 좋은 수치이므로 (1 - 값)을 통해 페널티로 역산
    penalty = (w_l * l) + (w_s * (1.0 - s)) + (w_e * (1.0 - e))
    
    # 거리에 (1 + 페널티)를 곱하여 최종 비용을 산출
    cost = distance_m * (1.0 + penalty)
    
    return cost
