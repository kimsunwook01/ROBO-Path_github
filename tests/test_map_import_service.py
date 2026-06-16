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
                "type": "STATION",
                "position": {"x": 0.0, "y": 0.0, "z": 0.0},
                "location_usage": "TestStation"
            }
        ],
        "tiles": [
            {
                "id": "22222222-2222-2222-2222-222222222222",
                "type": "Path_Flat",
                "position": {"x": 3.0, "y": 0.0, "z": 4.0}
            }
        ],
        "adjacency": [
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "adjacent_to": ["22222222-2222-2222-2222-222222222222"]
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

        # 검증: 노드 2개(거점1+타일1), 엣지 1개
        assert nodes_count == 2
        assert edges_count == 1

        # Repository가 제대로 호출되었는지 확인
        mock_node_repo.upsert_nodes.assert_called_once()
        mock_edge_repo.upsert_edges.assert_called_once()

        # upsert_nodes에 전달된 객체 검증
        upserted_nodes = mock_node_repo.upsert_nodes.call_args[0][0]
        assert len(upserted_nodes) == 2
        
        station = next(n for n in upserted_nodes if isinstance(n, BaseLocation))
        assert station.location_usage == "TestStation"
        assert station.x == 0.0

        # upsert_edges에 전달된 객체 검증
        upserted_edges = mock_edge_repo.upsert_edges.call_args[0][0]
        assert len(upserted_edges) == 1
        edge = upserted_edges[0]
        
        # 3, 4, 0 -> 피타고라스 거리 5.0
        assert edge.distance_m == 5.0

    finally:
        os.remove(temp_path)
