import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.worker import app, robot_id, state, current_task

client = TestClient(app)

# Helper fixture to reset worker state
@pytest.fixture(autouse=True)
def cleanup_worker_state():
    global robot_id, state, current_task
    robot_id = "test-robot"
    state = "idle"
    current_task = None

def test_receive_assignment_success():
    """
    Test that an idle robot can receive an assignment.
    """
    assignment_data = {
        "task_id": "T001",
        "pickup_x": 10,
        "pickup_y": 20
    }
    with patch('app.worker.robot_id', new="test-robot"):
        response = client.post("/api/v1/assign/test-robot", json=assignment_data)
        assert response.status_code == 200
        assert response.json() == {"message": "Assignment accepted"}
        # Ensure state has changed
        assert state == "busy"
        assert current_task['task_id'] == "T001"

def test_receive_assignment_fail_busy():
    """
    Test that a busy robot cannot receive a new assignment.
    """
    global state
    state = "busy"
    assignment_data = {
        "task_id": "T002",
        "pickup_x": 10,
        "pickup_y": 20
    }
    with patch('app.worker.robot_id', new="test-robot"):
        response = client.post("/api/v1/assign/test-robot", json=assignment_data)
        assert response.status_code == 400
        assert response.json() == {"detail": "Robot is not available for a new assignment"}