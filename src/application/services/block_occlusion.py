"""
블록 덮임(occlusion) 판정 유틸 — 명세 'Map_Design_Specification.md 2장' 구현.

명세 규칙:
- 블록(Block)은 물리적 지형 단위이고, 로봇은 '블록의 윗면 위'를 주행한다.
- 블록을 수직으로 쌓으면, 아래 블록의 윗면은 위 블록에 덮여 주행면이 될 수 없다.
- 따라서 A* 그래프 노드로는 '덮이지 않은(윗면이 노출된) 블록'만 채택해야 한다.

중요 — '가장 위 블록'으로 단순 판정하면 안 된다:
- 건물 지붕/처마/고가도로처럼 '허공에 떠서' 아래를 덮는 블록이 있다.
- 이 경우 위 블록과 아래 블록 사이에 빈 공간(gap)이 있으므로, 아래 블록은
  여전히 주행 가능하다(덮이지 않음).
- 따라서 '맞붙어 쌓였는가(아래 윗면 ≈ 위 아랫면)'를 기준으로 판정한다.

판정 기준:
- 블록 A가 덮였다 = 같은 (gx, gz) 그리드 칸에서, A의 윗면(top) 바로 위에
  다른 블록 B의 아랫면(bottom)이 맞닿아 있다 (0 근처의 작은 간격 이내).
- 맞닿음 허용 오차(STACK_GAP_TOLERANCE)보다 큰 간격이면 '떠 있는' 것이므로
  덮임이 아니다.
"""
from typing import List, Dict, Any
from collections import defaultdict

# 윗면-아랫면이 '맞붙었다'고 볼 최대 간격(미터).
# 타일(두께 0.5)이 블록 위에 얹히는 경우까지 고려해 약간의 여유를 둔다.
STACK_GAP_TOLERANCE = 0.6

# 같은 그리드 칸으로 묶을 때 XZ 좌표 반올림 단위(10m 그리드)
def _grid_key(x: float, z: float):
    return (round(x), round(z))


def _top(tile: Dict[str, Any]) -> float:
    """블록 윗면(주행면) 높이. elevation 이 있으면 그것을, 없으면 position.y 사용."""
    if "elevation" in tile and tile["elevation"] is not None:
        return float(tile["elevation"])
    return float(tile["position"]["y"])


def _bottom(tile: Dict[str, Any]) -> float:
    """블록 아랫면 높이 = 윗면 - 높이(size.y)."""
    size_y = float(tile.get("size", {}).get("y", 0.0))
    return _top(tile) - size_y


def compute_covered_tile_ids(tiles: List[Dict[str, Any]]) -> set:
    """
    tiles(scene_dump 의 tiles 섹션 원본 dict 리스트)를 받아,
    '덮여서 주행면이 될 수 없는' 블록의 id 집합을 반환한다.

    덮임 판정: 같은 그리드 칸에서 A.top 바로 위에 B.bottom 이 맞붙으면 A는 덮임.
    (B 가 공중에 떠 있으면(gap 큼) A 는 덮이지 않음 → 지붕/처마 케이스 보존)
    """
    # 그리드 칸별로 블록 묶기
    by_cell: Dict[tuple, List[Dict[str, Any]]] = defaultdict(list)
    for t in tiles:
        pos = t["position"]
        by_cell[_grid_key(pos["x"], pos["z"])].append(t)

    covered_ids = set()

    for cell, blocks in by_cell.items():
        if len(blocks) < 2:
            continue  # 단독 블록은 절대 덮이지 않음

        for a in blocks:
            a_top = _top(a)
            for b in blocks:
                if b is a:
                    continue
                # b 의 아랫면이 a 의 윗면 위에 맞붙어 있는가?
                gap = _bottom(b) - a_top
                # gap 이 0 근처(맞붙음)면 a 는 b 에 덮임.
                # 음수 약간(겹침)도 허용, 양수는 tolerance 까지만.
                if -STACK_GAP_TOLERANCE <= gap <= STACK_GAP_TOLERANCE:
                    covered_ids.add(str(a["id"]))
                    break

    return covered_ids
