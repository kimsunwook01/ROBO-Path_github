import json
import math
import logging
from typing import Dict, List, Tuple
from uuid import UUID
from src.domain.models import Node, BaseLocation, Edge
from src.application.interfaces import NodeRepository, EdgeRepository

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
                location_usage=n.get("location_usage", "Station")
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
                node_type="BASE"
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
                    
                to_node = node_dict[to_id]
                
                # 거리 계산
                dx = from_node.x - to_node.x
                dy = from_node.y - to_node.y
                dz = from_node.z - to_node.z
                dist = math.sqrt(dx*dx + dy*dy + dz*dz)
                if dist <= 0.0:
                    dist = 0.1 # 최소 거리 보장
                    
                # Edge 중복 검사
                # from-to 방향 쌍이 중복되지 않도록 방어 코드 추가 가능하지만, 
                # 방향성이 있는 그래프라면 그대로 추가
                edge_models.append(Edge(
                    from_node_id=from_node.id,
                    to_node_id=to_node.id,
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
