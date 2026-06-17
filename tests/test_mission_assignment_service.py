import pytest
from unittest.mock import MagicMock
from uuid import uuid4
from src.domain.models.mission import Mission
from src.domain.models.metadata import Robot
from src.domain.models.node import BaseLocation
from src.application.services.mission_assignment_service import MissionAssignmentService

@pytest.fixture
def mock_node_repo():
    return MagicMock()

@pytest.fixture
def mock_mission_repo():
    return MagicMock()

@pytest.fixture
def mock_robot_repo():
    return MagicMock()

@pytest.fixture
def service(mock_node_repo, mock_mission_repo, mock_robot_repo):
    return MissionAssignmentService(mock_node_repo, mock_mission_repo, mock_robot_repo)

def test_assign_next_mission_success(service, mock_node_repo, mock_mission_repo, mock_robot_repo):
    robot_id = uuid4()
    mock_robot = Robot(id=robot_id, name="Wheeled-01", platform="wheeled", status="Idle")
    mock_robot_repo.get_robot_by_name.return_value = mock_robot
    
    target_node = BaseLocation(id=uuid4(), x=0, y=0, z=0, node_type="BASE", name="Dest1", location_usage="Destination")
    mock_node_repo.get_all_nodes.return_value = [target_node]
    
    expected_mission = Mission(id=uuid4(), robot_id=robot_id, mission_type="Delivery", status="Active", to_node_id=target_node.id)
    mock_mission_repo.create_mission.return_value = expected_mission
    
    mission = service.assign_next_mission("Wheeled-01")
    
    assert mission is not None
    assert mission.id == expected_mission.id
    mock_mission_repo.create_mission.assert_called_once()
    mock_robot_repo.update_robot_status.assert_called_once_with(robot_id, "Delivery")

def test_assign_next_mission_not_idle(service, mock_robot_repo, mock_mission_repo):
    robot_id = uuid4()
    mock_robot = Robot(id=robot_id, name="Wheeled-01", platform="wheeled", status="Delivery")
    mock_robot_repo.get_robot_by_name.return_value = mock_robot
    
    mission = service.assign_next_mission("Wheeled-01")
    
    assert mission is None
    mock_mission_repo.create_mission.assert_not_called()
