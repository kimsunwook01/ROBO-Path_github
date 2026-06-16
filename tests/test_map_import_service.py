import os
import json
import tempfile
import pytest
from unittest.mock import MagicMock
from src.application.services.map_import_service import MapImportService
from src.domain.models import Node, BaseLocation, Edge

@pytest.fixture
def mock_node_repo():
    repo = MagicMock()
    repo.upsert_nodes.return_value = True
    return repo

@pytest.fixture
def mock_edge_repo():
    repo = MagicMock()
    repo.upsert_edges.return_value = True
    return repo

@pytest.fixture
def dummy_scene_dump():
    # 3D 유클리드 거리 테스트를 위한 간단한 데이터
    # node_1(0,0,0) -> tile_1(3,4,0) : 거리는 5
    data = {
        "nodes": [
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "tag": "Node_Destination",
                "position": {"x": 0.0, "y": 0.0, "z": 0.0},
                "location_usage": "TestStation"
            }
        ],
        "tiles": [
            {
                "id": "22222222-2222-2222-2222-222222222222",
                "terrain_type": "Path_Flat",
                "position": {"x": 3.0, "y": 0.0, "z": 4.0}
            },
            {
                "id": "33333333-3333-3333-3333-333333333333",
                "terrain_type": "Path_Stair",
                "position": {"x": -3.0, "y": 0.0, "z": -4.0}
            }
        ],
        "adjacency": [
            {
                "id": "22222222-2222-2222-2222-222222222222",
                "adjacent_to": ["33333333-3333-3333-3333-333333333333"]
            }
        ]
    }
    return data

def test_map_import_service_parsing(mock_node_repo, mock_edge_repo, dummy_scene_dump):
    # JSON 파일 생성 (임시)
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".json") as f:
        json.dump(dummy_scene_dump, f)
        temp_path = f.name

    try:
        service = MapImportService(mock_node_repo, mock_edge_repo)
        nodes_count, edges_count = service.import_from_json(temp_path)

        # 검증: 노드 3개(거점1 + 타일2)
        assert nodes_count == 3
        
        # 엣지 검증: 타일 간 단방향 연결 1개 (222->333) + 거점 연결(양방향).
        # 거점(0,0,0)은 222와 333 모두 거리가 5이므로, 같은 셀 (dx<=5, dz<=5)에 속해 둘 다 양방향 연결됨.
        # 따라서 거점->222, 거점->333, 222->거점, 333->거점 (총 4개)
        # 총 엣지 수: 1 + 4 = 5
        assert edges_count == 5

        # Repository가 제대로 호출되었는지 확인
        mock_node_repo.upsert_nodes.assert_called_once()
        mock_edge_repo.upsert_edges.assert_called_once()

        # upsert_nodes에 전달된 객체 검증
        upserted_nodes = mock_node_repo.upsert_nodes.call_args[0][0]
        assert len(upserted_nodes) == 3
        
        station = next(n for n in upserted_nodes if isinstance(n, BaseLocation))
        assert station.location_usage == "TestStation"
        assert station.terrain_tag == "Node_Destination"
        
        flat_tile = next(n for n in upserted_nodes if str(n.id) == "22222222-2222-2222-2222-222222222222")
        assert flat_tile.terrain_tag == "Path_Flat"

        stair_tile = next(n for n in upserted_nodes if str(n.id) == "33333333-3333-3333-3333-333333333333")
        assert stair_tile.terrain_tag == "Path_Stair"

        # upsert_edges에 전달된 객체 검증
        upserted_edges = mock_edge_repo.upsert_edges.call_args[0][0]
        assert len(upserted_edges) == 5
        
        # 거점발 엣지가 존재하는지 (고립 해제)
        station_edges = [e for e in upserted_edges if e.from_node_id == station.id]
        assert len(station_edges) == 2 # 222와 333으로 향하는 엣지 2개

    finally:
        os.remove(temp_path)
