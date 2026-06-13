import pytest
import uuid
from src.domain.algorithms.statistics import update_platform_stats
from src.domain.models.edge import PlatformStat
from src.domain.models.log import MissionLog

def test_cumulative_moving_average():
    """피드백 지표 누적 평균 계산이 올바른지 검증"""
    old_stats = PlatformStat(
        average_load_factor=0.5,
        average_stability=0.5,
        average_efficiency=0.5,
        traversal_count=1
    )
    
    new_log = MissionLog(
        id=uuid.uuid4(),
        robot_id=uuid.uuid4(),
        operating_mode="Task",
        load_factor=1.0,
        stability_index=1.0,
        efficiency_index=1.0,
        log_file_url="http://test.com"
    )
    
    new_stats = update_platform_stats(old_stats, new_log)
    
    # (0.5 * 1 + 1.0) / 2 = 0.75
    assert new_stats.average_load_factor == 0.75
    assert new_stats.average_stability == 0.75
    assert new_stats.average_efficiency == 0.75
    assert new_stats.traversal_count == 2

def test_traversal_count_increment():
    """기존 통계와 신규 값 결합 시 traversal_count가 정확히 증가하는지 검증"""
    old_stats = PlatformStat(
        average_load_factor=0.2,
        average_stability=0.8,
        average_efficiency=0.9,
        traversal_count=5
    )
    
    # 일부 필드만 있는 로그 (예를 들어 하나만 업데이트 되는 경우)
    # Pydantic 필드 검증 제약 상 None이 가능하다고 가정 (실제로는 MissionLog에 Optional 선언 필요할 수 있음)
    # 하지만 statistics 로직은 "값이 하나라도 None이 아니어서 업데이트가 일어나면" 증가한다고 되어 있음
    new_log = MissionLog(
        id=uuid.uuid4(),
        robot_id=uuid.uuid4(),
        operating_mode="Task",
        load_factor=0.5,
        stability_index=0.5,
        efficiency_index=0.5,
        log_file_url="http://test.com"
    )
    
    new_stats = update_platform_stats(old_stats, new_log)
    assert new_stats.traversal_count == 6
