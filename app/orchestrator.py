import pandas as pd
import time
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import asyncio
import math
import httpx
import logging

# Set up logging for better visibility
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

# In-memory store for robot and task state
robot_state = {}
task_queue = asyncio.Queue()
completed_tasks = []

# Pydantic models for API data validation
class Heartbeat(BaseModel):
    robot_id: str
    x: int
    y: int
    battery_pct: int
    state: str
    port: int

class Assignment(BaseModel):
    task_id: str
    pickup_x: int
    pickup_y: int

# --- API Endpoints ---

@app.post("/api/v1/heartbeat")
async def receive_heartbeat(heartbeat: Heartbeat):
    """
    Ingests a heartbeat from a robot worker and updates the in-memory state.
    """
    robot_state[heartbeat.robot_id] = heartbeat.dict()
    logger.info(f"Heartbeat received from {heartbeat.robot_id}: {heartbeat.state}")
    return {"message": "Heartbeat received"}

@app.get("/api/v1/dashboard")
async def get_dashboard():
    """
    Returns a JSON snapshot of the system's state for the dashboard.
    Metrics are computed on-the-fly to ensure they are current.
    """
    idle_robots = sum(1 for r in robot_state.values() if r['state'] == 'idle')
    busy_robots = sum(1 for r in robot_state.values() if r['state'] == 'busy')
    charging_robots = sum(1 for r in robot_state.values() if r['state'] == 'charging')
    
    avg_latency = 0
    if completed_tasks:
        total_latency = sum(t['end_ts'] - t['start_ts'] for t in completed_tasks)
        avg_latency = total_latency / len(completed_tasks)
        
    total_robots = len(robot_state)
    utilization = (busy_robots / total_robots) * 100 if total_robots > 0 else 0
    
    return {
        "robots_idle": idle_robots,
        "robots_busy": busy_robots,
        "robots_charging": charging_robots,
        "tasks_in_queue": task_queue.qsize(),
        "avg_task_latency_s": round(avg_latency, 2),
        "robot_utilisation_pct": round(utilization, 2)
    }

# --- Background Task for Task Ingestion and Assignment ---

async def task_ingester():
    """
    Reads tasks from tasks.csv and pushes them to the queue over time.
    """
    df = pd.read_csv('data/tasks.csv', parse_dates=['start_ts'])
    last_ts = df.iloc[0]['start_ts']
    
    for _, row in df.iterrows():
        sleep_duration = (row['start_ts'] - last_ts).total_seconds()
        await asyncio.sleep(sleep_duration)
        await task_queue.put(row.to_dict())
        last_ts = row['start_ts']
        logger.info(f"New task added to queue: {row['task_id']}")

async def task_assigner():
    """
    Periodically checks for new tasks and assigns them to the best robot.
    """
    while True:
        if task_queue.empty() or not any(r['state'] == 'idle' for r in robot_state.values()):
            await asyncio.sleep(1)
            continue
        
        task = await task_queue.get()
        best_robot = find_best_robot(task)
        
        if best_robot:
            logger.info(f"Assigning task {task['task_id']} to robot {best_robot['robot_id']}")
            try:
                async with httpx.AsyncClient() as client:
                    robot_assignment_url = f"http://localhost:{best_robot['port']}/api/v1/assign"
                    response = await client.post(robot_assignment_url, json={
                        "task_id": task['task_id'],
                        "pickup_x": task['x'],
                        "pickup_y": task['y']
                    })
                    response.raise_for_status()
                    
                robot_state[best_robot['robot_id']]['state'] = 'busy'
                robot_state[best_robot['robot_id']]['current_task'] = task
                
            except httpx.RequestError as e:
                logger.error(f"Failed to assign task to robot {best_robot['robot_id']}: {e}")
                await task_queue.put(task)
        else:
            logger.warning(f"No feasible robot found for task {task['task_id']}. Re-queuing.")
            await task_queue.put(task)
            
        await asyncio.sleep(2)

def find_best_robot(task):
    """
    Finds the best robot for a task based on the business rules.
    """
    feasible_robots = []
    task_pickup = (task['x'], task['y'])
    task_delivery = (100, 100)
    
    for robot in robot_state.values():
        if robot['state'] == 'idle' and robot['battery_pct'] >= 20:
            current_pos = (robot['x'], robot['y'])
            dist_to_pickup = math.sqrt((current_pos[0] - task_pickup[0])**2 + (current_pos[1] - task_pickup[1])**2)
            dist_to_dropoff = math.sqrt((task_pickup[0] - task_delivery[0])**2 + (task_pickup[1] - task_delivery[1])**2)
            total_distance = dist_to_pickup + dist_to_dropoff
            
            estimated_drain = total_distance / 10
            
            if robot['battery_pct'] - estimated_drain >= 10:
                robot['estimated_travel_time_s'] = (total_distance / 1) * 5
                robot['total_distance'] = total_distance
                feasible_robots.append(robot)

    if not feasible_robots:
        return None
    
    feasible_robots.sort(key=lambda r: r['total_distance'])
    return feasible_robots[0]

@app.on_event("startup")
async def startup_event():
    """
    Starts the background tasks when the application begins.
    """
    logger.info("Orchestration Service starting up...")
    asyncio.create_task(task_ingester())
    asyncio.create_task(task_assigner())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.orchestrator:app", host="0.0.0.0", port=8000, reload=True)