import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.orchestrator import app, find_best_robot, robot_state, task_queue, completed_tasks

client = TestClient(app)

# Helper function to clear state between tests
@pytest.fixture(autouse=True)
def cleanup_state():
    robot_state.clear()
    while not task_queue.empty():
        task_queue.get_nowait()
    completed_tasks.clear()

def test_heartbeat_reception():
    """
    Test that the orchestrator correctly receives and stores a heartbeat.
    """
    heartbeat_data = {
        "robot_id": "R001",
        "x": 10,
        "y": 20,
        "battery_pct": 75,
        "state": "idle"
    }
    response = client.post("/api/v1/heartbeat", json=heartbeat_data)
    assert response.status_code == 200
    assert robot_state["R001"]['state'] == "idle"

def test_dashboard_metrics():
    """
    Test that the dashboard returns the correct metrics.
    """
    robot_state["R001"] = {"robot_id": "R001", "x": 10, "y": 20, "battery_pct": 75, "state": "idle"}
    robot_state["R002"] = {"robot_id": "R002", "x": 30, "y": 40, "battery_pct": 50, "state": "busy"}
    robot_state["R003"] = {"robot_id": "R003", "x": 5, "y": 5, "battery_pct": 15, "state": "charging"}
    
    response = client.get("/api/v1/dashboard")
    data = response.json()
    
    assert response.status_code == 200
    assert data["robots_idle"] == 1
    assert data["robots_busy"] == 1
    assert data["robots_charging"] == 1
    assert data["tasks_in_queue"] == 0
    assert data["robot_utilisation_pct"] == (1/3) * 100

def test_find_best_robot_no_feasible():
    """
    Test that find_best_robot returns None when no robot is available or feasible.
    """
    robot_state["R001"] = {"robot_id": "R001", "x": 10, "y": 20, "battery_pct": 5, "state": "idle"} # Low battery
    robot_state["R002"] = {"robot_id": "R002", "x": 30, "y": 40, "battery_pct": 50, "state": "busy"}
    
    task = {"pickup_x": 50, "pickup_y": 50}
    best_robot = find_best_robot(task)
    assert best_robot is None

def test_find_best_robot_selects_closest():
    """
    Test that find_best_robot selects the closest feasible robot.
    """
    robot_state["R001"] = {"robot_id": "R001", "x": 10, "y": 20, "battery_pct": 80, "state": "idle"}
    robot_state["R002"] = {"robot_id": "R002", "x": 80, "y": 90, "battery_pct": 90, "state": "idle"}
    
    task = {"pickup_x": 15, "pickup_y": 25}
    best_robot = find_best_robot(task)
    
    assert best_robot is not None
    assert best_robot["robot_id"] == "R001"