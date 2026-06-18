"""
로봇에 cost_profiles(지형별 통행 가능 여부 + 비용 프로파일)를 주입하는 유틸.

문제 배경:
- A* 의 build_graph 는 robot.weight_profile["cost_profiles"] 를 읽어
  is_traversable(terrain_tag, ...) 로 계단 등 통행 불가 지형을 차단한다.
- 그런데 robots 테이블의 weight_profile 컬럼은 기본값이 '{}' 이고,
  시드/조회 어디에서도 cost_profiles 를 채우지 않았다.
- 결과: cost_profiles 가 빈 dict -> is_traversable 이 항상 True ->
  계단 엣지가 A* 그래프에 그대로 들어가 휠 로봇이 계단을 오른다.

해결:
- config/cost_profiles.json 을 읽어, 로봇 platform(wheeled/legged)에 맞는
  프로파일({terrains, tiles, weights})을 robot.weight_profile["cost_profiles"]
  및 W_L/W_S/W_E 가중치로 주입한다.
"""
import os
import json
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

# config/cost_profiles.json 의 절대 경로 (이 파일 기준 상위로 올라가 config 폴더)
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", "..", ".."))
_COST_PROFILES_PATH = os.path.join(_PROJECT_ROOT, "config", "cost_profiles.json")


@lru_cache(maxsize=1)
def _load_cost_profiles_file() -> dict:
    """cost_profiles.json 전체를 읽어 캐싱한다(파일 I/O 1회)."""
    try:
        with open(_COST_PROFILES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"cost_profiles.json 로드 실패 ({_COST_PROFILES_PATH}): {e}")
        return {}


def inject_cost_profiles(robot):
    """
    로봇 객체의 weight_profile 에 cost_profiles 와 가중치(W_L/W_S/W_E)를 주입한다.
    robot.platform (wheeled/legged)에 해당하는 프로파일만 넣는다.
    이미 주입돼 있으면(키 존재) 건드리지 않는다.

    Returns: 수정된 robot (in-place 수정이지만 반환도 함)
    """
    if robot is None:
        return robot

    platform = getattr(robot, "platform", None)
    if not platform:
        logger.warning("robot.platform 이 없어 cost_profiles 주입을 건너뜀")
        return robot

    full = _load_cost_profiles_file()
    platforms = full.get("platforms", {})
    platform_profile = platforms.get(platform)

    if not platform_profile:
        logger.warning(f"cost_profiles.json 에 platform '{platform}' 프로파일이 없음")
        return robot

    # weight_profile 이 dict 가 아니면 초기화
    if not isinstance(robot.weight_profile, dict):
        robot.weight_profile = {}

    # A* build_graph 가 기대하는 구조:
    #   robot.weight_profile["cost_profiles"]["terrains"][terrain_tag]["traversable"]
    #   robot.weight_profile["cost_profiles"]["tiles"][...]
    robot.weight_profile["cost_profiles"] = {
        "terrains": platform_profile.get("terrains", {}),
        "tiles": platform_profile.get("tiles", {}),
    }

    # 가중치(W_L/W_S/W_E)도 주입 (calculate_edge_cost 가 weight_profile.get("W_L") 등으로 읽음)
    weights = platform_profile.get("weights", {})
    for k in ("W_L", "W_S", "W_E"):
        if k in weights:
            robot.weight_profile[k] = weights[k]

    # noise_range 등 상위 레벨 값도 필요하면 함께
    if "noise_range" in full:
        robot.weight_profile.setdefault("noise_range", full["noise_range"])

    logger.info(
        f"cost_profiles 주입 완료: platform={platform}, "
        f"terrains={len(robot.weight_profile['cost_profiles']['terrains'])}개, "
        f"Path_Stair traversable="
        f"{robot.weight_profile['cost_profiles']['terrains'].get('Path_Stair', {}).get('traversable', 'N/A')}"
    )
    return robot
