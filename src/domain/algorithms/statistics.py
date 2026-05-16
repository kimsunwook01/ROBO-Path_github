from typing import Optional
from src.domain.models.edge import PlatformStat
from src.domain.models.log import MissionLog

def update_platform_stats(current_stats: PlatformStat, new_log: MissionLog) -> PlatformStat:
    """
    새로운 주행 로그(MissionLog)의 통계 데이터를 기존 엣지의 플랫폼 통계(PlatformStat)에 병합합니다.
    누적 이동 평균(Cumulative Moving Average) 알고리즘을 사용하여 O(1) 시간에 통계를 갱신합니다.
    
    Args:
        current_stats: 갱신 전 엣지의 특정 기종 통계 데이터
        new_log: 새롭게 수집된 개별 주행 결과 데이터
        
    Returns:
        PlatformStat: 병합되어 갱신된 새로운 통계 객체
    """
    n = current_stats.traversal_count
    
    # 누적 이동 평균을 구하는 내부 헬퍼 함수
    def get_new_average(old_avg: float, new_val: Optional[float]) -> float:
        if new_val is None:
            return old_avg
        return (old_avg * n + new_val) / (n + 1)
        
    new_load = get_new_average(current_stats.average_load_factor, new_log.load_factor)
    new_stability = get_new_average(current_stats.average_stability, new_log.stability_index)
    new_efficiency = get_new_average(current_stats.average_efficiency, new_log.efficiency_index)
    
    # 값이 하나라도 None이 아니어서 업데이트가 일어났을 때만 traversal_count를 증가시킴
    has_update = (new_log.load_factor is not None) or \
                 (new_log.stability_index is not None) or \
                 (new_log.efficiency_index is not None)
                 
    new_count = n + 1 if has_update else n
    
    return PlatformStat(
        average_load_factor=new_load,
        average_stability=new_stability,
        average_efficiency=new_efficiency,
        traversal_count=new_count
    )
