import pytest
import json
import os
from src.domain.algorithms.cost_calculator import calculate_edge_cost, resolve_cost_multiplier
from src.domain.models.edge import PlatformStat

# Mock Stats & Profiles
@pytest.fixture
def mock_stats():
    return PlatformStat(
        platform="wheeled",
        traversal_count=5,
        average_load_factor=0.5,
        average_stability=0.8,
        average_efficiency=0.9
    )

@pytest.fixture
def mock_weight_profile():
    return {"W_L": 0.3, "W_S": 0.5, "W_E": 0.2}

@pytest.fixture
def sample_profile():
    return {
        "terrains": {
            "Road_Sidewalk": {"cost_multiplier": 1},
            "Road_Vehicle": {"cost_multiplier": 20}
        },
        "tiles": {
            "Crosswalk": {"cost_multiplier": 1}
        }
    }

# --- calculate_edge_cost Tests ---

def test_calculate_cost_default_same_as_explicit_one(mock_stats, mock_weight_profile):
    cost_implicit = calculate_edge_cost(10.0, mock_stats, mock_weight_profile)
    cost_explicit = calculate_edge_cost(10.0, mock_stats, mock_weight_profile, cost_multiplier=1.0)
    assert cost_implicit == pytest.approx(cost_explicit)

def test_calculate_cost_linear_scaling(mock_stats, mock_weight_profile):
    cost_base = calculate_edge_cost(10.0, mock_stats, mock_weight_profile, cost_multiplier=1.0)
    cost_scaled = calculate_edge_cost(10.0, mock_stats, mock_weight_profile, cost_multiplier=2.0)
    assert cost_scaled == pytest.approx(cost_base * 2.0)

def test_calculate_cost_no_stats_multiplier():
    # 미주행(stats=None)에도 적용: cost_multiplier=20이면 결과 == distance × 20
    cost = calculate_edge_cost(10.0, None, {}, cost_multiplier=20.0)
    assert cost == pytest.approx(10.0 * 20.0)

def test_calculate_cost_zero_traversal_multiplier():
    # 미주행(traversal_count=0)에도 적용: cost_multiplier=20이면 결과 == distance × 20
    stats_zero = PlatformStat(platform="wheeled", traversal_count=0, average_load_factor=0, average_stability=0, average_efficiency=0)
    cost = calculate_edge_cost(10.0, stats_zero, {}, cost_multiplier=20.0)
    assert cost == pytest.approx(10.0 * 20.0)

def test_calculate_cost_no_stats_backward_compatible():
    # 하위 호환: stats=None이고 cost_multiplier 미지정이면 결과 == distance 그대로
    cost = calculate_edge_cost(10.0, None, {})
    assert cost == pytest.approx(10.0)


# --- resolve_cost_multiplier Tests ---

def test_resolve_terrain_only(sample_profile):
    # 타일 없으면 terrain 값 사용
    assert resolve_cost_multiplier("Road_Vehicle", None, sample_profile) == pytest.approx(20.0)
    assert resolve_cost_multiplier("Road_Sidewalk", None, sample_profile) == pytest.approx(1.0)

def test_resolve_tile_overrides_terrain(sample_profile):
    # 타일이 terrain을 덮어씀: Road_Vehicle + Crosswalk -> 1
    assert resolve_cost_multiplier("Road_Vehicle", "Crosswalk", sample_profile) == pytest.approx(1.0)

def test_resolve_tile_list_overrides_terrain(sample_profile):
    # tile_tags를 리스트로 줘도 동일하게 1
    assert resolve_cost_multiplier("Road_Vehicle", ["Crosswalk"], sample_profile) == pytest.approx(1.0)

def test_resolve_unknown_tile_fallback(sample_profile):
    # 프로파일에 없는 타일이면 무시하고 terrain으로 폴백 -> 20
    assert resolve_cost_multiplier("Road_Vehicle", "UnknownTile", sample_profile) == pytest.approx(20.0)

def test_resolve_unknown_terrain(sample_profile):
    # 프로파일에 없는 terrain이면 1.0
    assert resolve_cost_multiplier("UnknownTerrain", None, sample_profile) == pytest.approx(1.0)

def test_resolve_both_none(sample_profile):
    # terrain/tile 둘 다 None이면 1.0
    assert resolve_cost_multiplier(None, None, sample_profile) == pytest.approx(1.0)

def test_resolve_empty_profile():
    # 빈 프로파일({})이어도 1.0
    assert resolve_cost_multiplier("Road_Vehicle", "Crosswalk", {}) == pytest.approx(1.0)

def test_resolve_multiple_tiles_first_match(sample_profile):
    # 여러 타일을 줄 때 프로파일에 정의된 첫 매칭 타일이 적용됨
    assert resolve_cost_multiplier("Road_Vehicle", ["UnknownTile", "Crosswalk", "AnotherTile"], sample_profile) == pytest.approx(1.0)


# --- Actual Configuration Validation ---

@pytest.fixture
def real_config():
    # 저장소 루트의 config/cost_profiles.json 읽기
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", "cost_profiles.json")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

def test_real_config_wheeled(real_config):
    profile = real_config["platforms"]["wheeled"]
    assert resolve_cost_multiplier("Road_Vehicle", None, profile) == pytest.approx(20.0)
    assert resolve_cost_multiplier("Road_Vehicle", "Crosswalk", profile) == pytest.approx(1.0)
    assert resolve_cost_multiplier("Terrain_Flat", None, profile) == pytest.approx(1.0)

def test_real_config_legged(real_config):
    profile = real_config["platforms"]["legged"]
    assert resolve_cost_multiplier("Road_Vehicle", None, profile) == pytest.approx(3.0)
    assert resolve_cost_multiplier("Road_Vehicle", "Crosswalk", profile) == pytest.approx(1.0)


# --- Composition (Resolver + Calculator) Tests ---

def test_composition_vehicle_vs_sidewalk(mock_stats, mock_weight_profile, sample_profile):
    # 동일 stats에서, 차도(multiplier 20) 비용 > 인도(multiplier 1) 비용.
    mult_vehicle = resolve_cost_multiplier("Road_Vehicle", None, sample_profile)
    cost_vehicle = calculate_edge_cost(10.0, mock_stats, mock_weight_profile, cost_multiplier=mult_vehicle)

    mult_sidewalk = resolve_cost_multiplier("Road_Sidewalk", None, sample_profile)
    cost_sidewalk = calculate_edge_cost(10.0, mock_stats, mock_weight_profile, cost_multiplier=mult_sidewalk)

    assert cost_vehicle > cost_sidewalk

def test_composition_crosswalk_equals_sidewalk(mock_stats, mock_weight_profile, sample_profile):
    # 차도 위 횡단보도(덮어쓰기로 1) 비용은 차도보다 훨씬 낮고, 인도 비용과 같다(근사 비교).
    mult_vehicle = resolve_cost_multiplier("Road_Vehicle", None, sample_profile)
    cost_vehicle = calculate_edge_cost(10.0, mock_stats, mock_weight_profile, cost_multiplier=mult_vehicle)

    mult_crosswalk = resolve_cost_multiplier("Road_Vehicle", "Crosswalk", sample_profile)
    cost_crosswalk = calculate_edge_cost(10.0, mock_stats, mock_weight_profile, cost_multiplier=mult_crosswalk)

    mult_sidewalk = resolve_cost_multiplier("Road_Sidewalk", None, sample_profile)
    cost_sidewalk = calculate_edge_cost(10.0, mock_stats, mock_weight_profile, cost_multiplier=mult_sidewalk)

    assert cost_crosswalk < cost_vehicle
    assert cost_crosswalk == pytest.approx(cost_sidewalk)
