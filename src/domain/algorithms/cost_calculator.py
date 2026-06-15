from typing import Dict, Any, Optional, Union, Iterable
from src.domain.models.edge import PlatformStat

def calculate_edge_cost(distance_m: float, stats: Optional[PlatformStat], weight_profile: Dict[str, Any], cost_multiplier: float = 1.0) -> float:
    """
    플랫폼(기종)의 가중치 프로필과 엣지의 주행 통계 지표를 결합하여 A* 알고리즘용 비용(Cost)을 산출합니다.
    
    Args:
        distance_m: 엣지의 물리적 거리(미터)
        stats: 특정 기종이 해당 엣지에서 기록한 평균 물리 지표 (없을 수 있음)
        weight_profile: 로봇 모델에 정의된 가중치 프로필 (W_L, W_S, W_E 등)
        cost_multiplier: 통행 정책(억제) 계수이며 L/S/E와 분리된 개념. 기본 1.0이면 기존과 동일, 미주행 엣지에도 동일하게 적용됨.
        
    Returns:
        float: 최종 산출된 주행 비용 스칼라 값
    """
    # 기본 가중치 설정 (설정되지 않았을 경우 1.0 적용)
    w_l = weight_profile.get("W_L", 1.0)
    w_s = weight_profile.get("W_S", 1.0)
    w_e = weight_profile.get("W_E", 1.0)
    
    if not stats or stats.traversal_count == 0:
        # 주행 데이터가 없는 엣지의 경우 순수 물리적 거리에 억제 계수를 반영하여 산출
        return distance_m * cost_multiplier
        
    l = stats.average_load_factor
    s = stats.average_stability
    e = stats.average_efficiency
    
    # 안정성과 효율성은 1에 가까울수록 좋은 수치이므로 (1 - 값)을 통해 페널티로 역산
    penalty = (w_l * l) + (w_s * (1.0 - s)) + (w_e * (1.0 - e))
    
    # 거리에 억제 계수와 (1 + 페널티)를 곱하여 최종 비용을 산출
    cost = distance_m * cost_multiplier * (1.0 + penalty)
    
    # A* Admissibility (최적성) 보장을 위한 하한 안전판: 실제 물리적 거리보다 작아지지 않게 방어
    cost = max(distance_m, cost)
    
    return cost

def resolve_cost_multiplier(terrain_tag: Optional[str], tile_tags: Optional[Union[str, Iterable[str]]], platform_profile: dict) -> float:
    """
    지형(블록) 태그, 타일 태그들, 그리고 플랫폼 비용 프로파일로부터
    최종 적용할 cost_multiplier를 결정합니다.
    우선순위:
    1. tile_tags에 매칭되는 타일이 profiles의 tiles에 있으면 해당 cost_multiplier 반환
    2. terrain_tag가 profiles의 terrains에 매칭되면 해당 cost_multiplier 반환
    3. 매칭되는 항목이 없으면 1.0 반환
    """
    if tile_tags is not None:
        if isinstance(tile_tags, str):
            tiles_to_check = [tile_tags]
        else:
            tiles_to_check = tile_tags
            
        profile_tiles = platform_profile.get("tiles", {})
        if isinstance(profile_tiles, dict):
            for t_tag in tiles_to_check:
                if t_tag in profile_tiles and isinstance(profile_tiles[t_tag], dict):
                    if "cost_multiplier" in profile_tiles[t_tag]:
                        return float(profile_tiles[t_tag]["cost_multiplier"])
                        
    if terrain_tag is not None:
        profile_terrains = platform_profile.get("terrains", {})
        if isinstance(profile_terrains, dict) and terrain_tag in profile_terrains:
            t_data = profile_terrains[terrain_tag]
            if isinstance(t_data, dict) and "cost_multiplier" in t_data:
                return float(t_data["cost_multiplier"])
                
    return 1.0
