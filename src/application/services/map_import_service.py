import json
import math
import logging
from typing import Dict, List, Tuple
from uuid import UUID
from src.domain.models import Node, BaseLocation, Edge
from src.application.interfaces import NodeRepository, EdgeRepository
from src.domain.algorithms.cost_calculator import is_traversable

logger = logging.getLogger(__name__)

class MapImportService:
    def __init__(self, node_repo: NodeRepository, edge_repo: EdgeRepository):
        self.node_repo = node_repo
        self.edge_repo = edge_repo

    def import_from_json(self, filepath: str) -> Tuple[int, int]:
        """
        scene_dump.json 파일을 파싱하여 DB에 노드와 엣지를 Upsert 한다.
        반환값: (삽입/갱신된 노드 수, 삽입/갱신된 엣지 수)
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load JSON file {filepath}: {e}")
            raise

        nodes_data = data.get("nodes", [])
        tiles_data = data.get("tiles", [])
        adjacency_data = data.get("adjacency", [])

        # 1. 노드 생성
        node_models: List[Node] = []
        node_dict: Dict[str, Node] = {} # ID를 키로 저장 (거리 계산용)

        # 1-1. 거점(STATION) 파싱 -> BaseLocation
        for n in nodes_data:
            node_id = str(n["id"]) # 원본 문자열 ID 보존 또는 UUID 변환 필요?
            # 현재 UUID가 모델의 id 타입이므로, 문자열이 유효한 UUID 형식이어야 함.
            # scene_dump.json의 ID가 UUID 형식이 아니라면, UUID를 새로 발급하고 매핑을 관리해야 하지만,
            # 프로젝트 명세상 scene_dump 개편 시 고유 UUID 체계(또는 매핑 가능한 형태)를 도입했다고 가정.
            # 여기서는 편의상 UUID()로 변환 시도. 실패 시 스킵(추후 구조에 맞춰 수정 가능).
            try:
                uid = UUID(node_id)
            except ValueError:
                # UUID가 아니라면 임의로 매핑할 수도 있으나, 여기서는 uuid.uuid5 등을 쓰거나 무시
                import uuid
                uid = uuid.uuid5(uuid.NAMESPACE_OID, node_id)

            pos = n["position"]
            base_loc = BaseLocation(
                id=uid,
                x=pos["x"],
                y=pos["y"],
                z=pos["z"],
                name=f"Station_{node_id[:8]}",
                location_usage=n.get("location_usage", "Station"),
                terrain_tag=n.get("tag", "Node_Destination")
            )
            node_models.append(base_loc)
            node_dict[node_id] = base_loc

        # 1-2. 타일 파싱 -> 기본 Node
        for t in tiles_data:
            tile_id = str(t["id"])
            try:
                uid = UUID(tile_id)
            except ValueError:
                import uuid
                uid = uuid.uuid5(uuid.NAMESPACE_OID, tile_id)

            pos = t["position"]
            node = Node(
                id=uid,
                x=pos["x"],
                y=pos["y"],
                z=pos["z"],
                node_type="BASE",
                terrain_tag=t.get("terrain_type", "Terrain_Flat")
            )
            node_models.append(node)
            node_dict[tile_id] = node

        # 2. 엣지 생성
        edge_models: List[Edge] = []
        edge_set = set() # 양방향 중복 방지 방어코드

        for adj in adjacency_data:
            from_id = str(adj["id"])
            if from_id not in node_dict:
                continue
                
            from_node = node_dict[from_id]
            
            for to_id in adj.get("adjacent_to", []):
                to_id = str(to_id)
                if to_id not in node_dict:
                    continue
                    
                # 중복 검사
                if (from_id, to_id) in edge_set:
                    continue
                edge_set.add((from_id, to_id))
                    
                to_node = node_dict[to_id]
                
                # 거리 계산
                dx = from_node.x - to_node.x
                dy = from_node.y - to_node.y
                dz = from_node.z - to_node.z
                dist = math.sqrt(dx*dx + dy*dy + dz*dz)
                if dist <= 0.0:
                    dist = 0.1 # 최소 거리 보장
                    
                edge_models.append(Edge(
                    from_node_id=from_node.id,
                    to_node_id=to_node.id,
                    distance_m=dist,
                    platform_stats={}
                ))

        # 2-1. 고립된 거점(STATION) 연결 로직
        # 거점은 10m 단위 그리드 위에 존재하므로, 같은 셀 (dx<=5, dz<=5) 내의 통행 가능한(평지) 타일과 양방향 연결한다.
        # 같은 셀 내에 통행 가능 타일이 없으면 가장 가까운 통행 가능 타일과 연결한다.
        station_nodes = [n for n in node_models if isinstance(n, BaseLocation)]
        tile_nodes = [n for n in node_models if not isinstance(n, BaseLocation)]

        for station in station_nodes:
            station_id_str = str(station.id)
            # 통과 가능한 타일들
            traversable_tiles = [t for t in tile_nodes if is_traversable(t.terrain_tag, None, {})]
            if not traversable_tiles:
                continue
            
            # 같은 셀 내의 타일 탐색 (dx <= 5, dz <= 5)
            # 타일의 중심과 거점의 중심이 같은 셀에 있으면 dx, dz가 5 이하임 (10m 그리드)
            nearby_tiles = []
            min_dist = float('inf')
            closest_tile = None

            for t in traversable_tiles:
                dx = t.x - station.x
                dy = t.y - station.y
                dz = t.z - station.z
                dist = math.sqrt(dx*dx + dy*dy + dz*dz)

                if dist < min_dist:
                    min_dist = dist
                    closest_tile = t

                if abs(dx) <= 5.1 and abs(dz) <= 5.1:
                    nearby_tiles.append((t, dist))

            # 같은 셀에 있는 타일들에 모두 연결, 없으면 가장 가까운 하나의 타일에 연결
            tiles_to_connect = nearby_tiles if nearby_tiles else [(closest_tile, min_dist)]

            for t, dist in tiles_to_connect:
                t_id_str = str(t.id)
                if dist <= 0.0:
                    dist = 0.1
                
                # 거점 -> 타일
                if (station_id_str, t_id_str) not in edge_set:
                    edge_set.add((station_id_str, t_id_str))
                    edge_models.append(Edge(
                        from_node_id=station.id,
                        to_node_id=t.id,
                        distance_m=dist,
                        platform_stats={}
                    ))
                # 타일 -> 거점
                if (t_id_str, station_id_str) not in edge_set:
                    edge_set.add((t_id_str, station_id_str))
                    edge_models.append(Edge(
                        from_node_id=t.id,
                        to_node_id=station.id,
                        distance_m=dist,
                        platform_stats={}
                    ))

        # 3. DB Upsert
        if node_models:
            success = self.node_repo.upsert_nodes(node_models)
            if not success:
                logger.error("Failed to upsert nodes.")
        
        if edge_models:
            success = self.edge_repo.upsert_edges(edge_models)
            if not success:
                logger.error("Failed to upsert edges.")

        return len(node_models), len(edge_models)
