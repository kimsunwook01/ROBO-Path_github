import pytest
from unittest.mock import MagicMock
from uuid import uuid4
from datetime import datetime, timezone
from src.domain.models import Mission
from src.infrastructure.database.supabase_mission_repo import SupabaseMissionRepository

@pytest.fixture
def mock_supabase():
    mock_client = MagicMock()
    return mock_client

@pytest.fixture
def repo(mock_supabase):
    return SupabaseMissionRepository(mock_supabase)

def test_create_mission(repo, mock_supabase):
    # Mocking the Supabase response
    mock_table = mock_supabase.table.return_value
    mock_insert = mock_table.insert.return_value
    mock_response = MagicMock()
    mock_response.data = [{
        "id": str(uuid4()),
        "robot_id": str(uuid4()),
        "mission_type": "Delivery",
        "status": "Pending",
        "accumulated_cost": 0.0,
        "acknowledged": False
    }]
    mock_insert.execute.return_value = mock_response

    # Test execution
    robot_id = uuid4()
    mission = Mission(
        robot_id=robot_id,
        mission_type="Delivery",
        status="Pending"
    )
    
    created_mission = repo.create_mission(mission)
    
    # Assertions
    assert created_mission is not None
    assert created_mission.mission_type == "Delivery"
    
    # Verify the payload sent to insert
    mock_supabase.table.assert_called_with("missions")
    insert_payload = mock_table.insert.call_args[0][0]  # This is the dict passed to .insert()
    
    assert "robot_id" in insert_payload
    assert insert_payload["robot_id"] == str(robot_id)
    assert insert_payload["mission_type"] == "Delivery"
    assert insert_payload["status"] == "Pending"
    assert "id" not in insert_payload  # We deleted None 'id'

def test_update_status(repo, mock_supabase):
    mock_table = mock_supabase.table.return_value
    mock_update = mock_table.update.return_value
    mock_eq = mock_update.eq.return_value
    mock_response = MagicMock()
    
    m_id = uuid4()
    
    mock_response.data = [{
        "id": str(m_id),
        "robot_id": str(uuid4()),
        "mission_type": "Delivery",
        "status": "Active"
    }]
    mock_eq.execute.return_value = mock_response
    
    updated_mission = repo.update_status(m_id, "Active")
    
    assert updated_mission is not None
    assert updated_mission.status == "Active"
    
    mock_supabase.table.assert_called_with("missions")
    mock_table.update.assert_called_with({"status": "Active"})
    mock_update.eq.assert_called_with("id", str(m_id))
