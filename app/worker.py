import time
import requests
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sys
import logging
import os
import uvicorn

# Set up logging for better visibility
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

# Pydantic models for API data validation
class Assignment(BaseModel):
    task_id: str
    pickup_x: int
    pickup_y: int

# --- Global state for each worker ---
# Initialized when the script is run with specific arguments
robot_id = None
x = 0
y = 0
battery_pct = 100
state = "idle"
heartbeat_period_s = 2
current_task = None
is_charging = False
TASK_DROP_OFF_LOCATION = (100, 100)
ORCHESTRATOR_URL = "http://localhost:8000/api/v1/heartbeat"

# --- API Endpoints ---

@app.post("/api/v1/assign")
async def receive_assignment(assignment: Assignment):
    """
    Endpoint for the Orchestrator to assign a task to this robot.
    """
    global state, current_task
    if state == "idle":
        state = "busy"
        current_task = assignment.dict()
        logger.info(f"Robot {robot_id} received assignment for task {current_task['task_id']}")
        return {"message": "Assignment accepted"}
    else:
        raise HTTPException(status_code=400, detail="Robot is not available for a new assignment")

# --- Background Task for Heartbeats and State Management ---

async def robot_loop():
    """
    This is the main control loop for the robot.
    It handles heartbeats, movement, and state transitions.
    """
    global x, y, battery_pct, state, is_charging, current_task

    while True:
        # --- Check for state transitions ---
        if state == "idle":
            # Check if charging is needed
            if battery_pct < 20 and not is_charging:
                await start_charging() # Trigger charging
        
        elif state == "busy" and current_task:
            # Simulate a time-based task completion, which is a pragmatic
            # simplification of calculating travel time.
            logger.info(f"Robot {robot_id} is busy with task {current_task['task_id']}")
            time_to_complete = 60 # Arbitrary sim time
            await asyncio.sleep(time_to_complete) 
            state = "idle"
            current_task = None
            logger.info(f"Robot {robot_id} has completed task and is now idle.")

        elif state == "charging":
            logger.info(f"Robot {robot_id} is charging...")
            # Simulate a 5-minute charge time
            await asyncio.sleep(300) 
            battery_pct = 100
            state = "idle"
            is_charging = False
            logger.info(f"Robot {robot_id} is fully charged and ready.")

        # --- Send heartbeat to Orchestrator ---
        heartbeat_data = {
            "robot_id": robot_id,
            "x": x,
            "y": y,
            "battery_pct": battery_pct,
            "state": state,
            # Fix: Add the port to the heartbeat
            "port": int(os.environ.get("WORKER_PORT"))
        }
        try:
            # Using the synchronous `requests` library in a separate thread via asyncio.
            await asyncio.to_thread(
                requests.post,
                ORCHESTRATOR_URL,
                json=heartbeat_data, 
                timeout=1
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send heartbeat: {e}")

        # Wait for the next heartbeat cycle
        await asyncio.sleep(heartbeat_period_s)

async def start_charging():
    """
    Simulates the robot moving to a charging station.
    """
    global x, y, state, is_charging
    is_charging = True
    x, y = 0, 0 # Simulate instantaneous travel to charging station for the demo
    state = "charging"
    logger.info(f"Robot {robot_id} is heading to charging station at (0, 0)")

@app.on_event("startup")
async def startup_event():
    """
    Initializes the robot's state and starts the main loop after the event loop has started.
    """
    global robot_id, x, y, battery_pct, state
    
    # Read configuration from environment variables
    robot_id = os.environ.get("ROBOT_ID")
    x = int(os.environ.get("ROBOT_X"))
    y = int(os.environ.get("ROBOT_Y"))
    battery_pct = int(os.environ.get("ROBOT_BATTERY"))
    state = os.environ.get("ROBOT_STATE")
    
    logger.info(f"Robot {robot_id} started at ({x}, {y}) with {battery_pct}% battery.")
    asyncio.create_task(robot_loop())

# Main entry point for the worker
if __name__ == "__main__":
    uvicorn.run(
        "app.worker:app", 
        host="0.0.0.0", 
        port=int(os.environ.get("WORKER_PORT")), 
        reload=True
    )