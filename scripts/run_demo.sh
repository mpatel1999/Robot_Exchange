#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "Starting Orchestration Service..."
# Start the orchestrator in the background on port 8000
uvicorn app.orchestrator:app --port 8000 --host 0.0.0.0 &
ORCH_PID=$! # Store the PID of the orchestrator process

# Give the orchestrator a moment to start up
sleep 3

echo "Starting Robot Workers from robots.csv..."
# Start a worker for each robot. This is a robust method that uses
# environment variables for configuration.

# Worker 1
WORKER_PORT=8001 ROBOT_ID=R001 ROBOT_X=4 ROBOT_Y=95 ROBOT_BATTERY=55 ROBOT_STATE=idle uvicorn app.worker:app --port 8001 --host 0.0.0.0 --reload &
WORKER1_PID=$!
sleep 1

# Worker 2
WORKER_PORT=8002 ROBOT_ID=R002 ROBOT_X=29 ROBOT_Y=18 ROBOT_BATTERY=33 ROBOT_STATE=idle uvicorn app.worker:app --port 8002 --host 0.0.0.0 --reload &
WORKER2_PID=$!
sleep 1

# Worker 3
WORKER_PORT=8003 ROBOT_ID=R003 ROBOT_X=76 ROBOT_Y=55 ROBOT_BATTERY=24 ROBOT_STATE=idle uvicorn app.worker:app --port 8003 --host 0.0.0.0 --reload &
WORKER3_PID=$!
sleep 1

echo "System is running. Monitoring dashboard every 10 seconds..."
# Periodically hit the dashboard API to show metrics
while true
do
    echo "--- Dashboard Snapshot ($(date)) ---"
    # Use curl to get a structured JSON response from the API
    curl -s http://localhost:8000/api/v1/dashboard
    echo ""
    echo "----------------------------------------"
    sleep 10
done

# Cleanup: This part is for when the script is manually terminated
trap "kill $ORCH_PID $WORKER1_PID $WORKER2_PID $WORKER3_PID" EXIT