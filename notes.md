### Robot Exchange Project Log

### 2025-08-26

#### Initial Plan

I started with a clear architectural plan:
-   **Orchestrator:** A central FastAPI service to track robot states and assign tasks.
-   **Workers:** Individual FastAPI services for each robot, sending heartbeats to the orchestrator.
-   **Communication:** A RESTful API over HTTP for simplicity.
-   **Concurrency:** Using Python's `asyncio` for the orchestrator to manage multiple tasks concurrently.
-   **Startup:** A shell script to launch all services from the command line.

***

### Debugging and Fixes

My initial implementation ran into several problems that required a step-by-step approach to fix.

#### Problem 1: `uvicorn` Argument Mismatch
-   **The Error:** `Error: Got unexpected extra arguments` when trying to launch the worker processes.
-   **My Mistake:** I was attempting to pass robot-specific configuration flags (`--robot-id`, `--x`, etc.) directly to the `uvicorn` command. `uvicorn` only accepts arguments related to the web server itself (like `--port`). It does not know what to do with custom application-specific arguments.
-   **The Fix:** I realized the correct approach was to pass these arguments to the `python` script itself, not to `uvicorn`. The `worker.py` script was then updated to use the `argparse` library to read these arguments, and the `run_demo.sh` script was changed to call `python app/worker.py ...` instead of `uvicorn ...`.

#### Problem 2: The Missing Event Loop
-   **The Error:** `RuntimeError: no running event loop` after fixing the previous issue.
-   **My Mistake:** I was creating an `asyncio` task (`asyncio.create_task(robot_loop())`) in the global scope of the worker script. An event loop must be running to create a task, but the `uvicorn` web server starts its event loop as part of its own startup process. My task was being created too early.
-   **The Fix:** I moved the `asyncio.create_task()` call into FastAPI's `@app.on_event("startup")` decorator. This ensured the task would only be created once the web server's event loop was ready, guaranteeing a stable start.

#### Problem 3: Data Mismatches (`KeyError`s)
-   **The Error:** I encountered two `KeyError` exceptions in a row: `KeyError: 'pickup_x'` and `KeyError: 'port'`.
-   **My Mistake:** These errors were caused by an incomplete data-flow design.
    1.  The `orchestrator.py` script was looking for `task['pickup_x']` and `task['pickup_y']`, but the `tasks.csv` file uses the simpler keys `x` and `y`.
    2.  The orchestrator needed to know the specific port to send an assignment request to each worker, but the workers' heartbeats were not including this information. As a result, when the orchestrator tried to call `best_robot['port']`, the key did not exist.
-   **The Fix:** I updated `orchestrator.py` to use the correct `x` and `y` keys from the task dictionary. I also updated the `worker.py` script to include its port number in the heartbeat payload. The `Heartbeat` Pydantic model in the orchestrator was also updated to accept this new field, completing the data flow. The `run_demo.sh` script, which sets the `WORKER_PORT` environment variable, was already providing this information, but the application code was not using it correctly until this change.

#### Problem 4: Visualizing System State

-   **The Problem:** The `run_demo.sh` script used `curl` to print a JSON object, which was hard to read and not visually intuitive for a team demo. The team needed a simple, live-updating dashboard to show the system's status.
-   **The Fix:** I decided to build a simple front-end using **Streamlit**. Instead of modifying the core services, I created a new `ui/dashboard.py` file that acts as a client. This client polls the existing `/api/v1/dashboard` endpoint and visualizes the metrics in real time. This approach kept the core API stable and demonstrated good separation of concerns.

***

### Conclusion: Final System State

After these fixes, the system now works as intended. The orchestrator and workers successfully start, heartbeats are received, the orchestrator correctly assigns a task to the most suitable robot, and the dashboard accurately reflects the real-time state change from idle to busy. The system is now operational.