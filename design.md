# Adaptive Robot Exchange — Design Document

### 1. Architectural Overview

The system is designed as a **decentralized, service-oriented architecture**. A single, central `Orchestration Service` manages a fleet of independent `Robot Worker` services. Communication between services is handled via a **RESTful API over HTTP**, providing a simple, standardized, and language-agnostic interface. This approach ensures each component is self-contained and scalable.



### 2. Data Flow

#### Heartbeat
- **Flow:** `Robot Worker` → `Orchestration Service`
- **Purpose:** Workers periodically send their status (location, battery, state) to the orchestrator.
- **Protocol:** HTTP POST to `/api/v1/heartbeat`. This is a one-way communication for state synchronization.

#### Task Assignment
- **Flow:** `Orchestration Service` → `Robot Worker`
- **Purpose:** The orchestrator assigns a task to the most suitable idle robot.
- **Protocol:** HTTP POST to `/api/v1/assign` on the worker's specific port. This is a crucial request-response pattern that requires error handling.

#### Observability Dashboard
- **Flow:** `UI Client` → `Orchestration Service`
- **Purpose:** A separate front-end client fetches system metrics to display a live dashboard.
- **Protocol:** HTTP GET to `/api/v1/dashboard`. This endpoint is read-only and provides a snapshot of the entire system's health.

***

### 3. Scaling and Reliability

- **Scalability:** The architecture is horizontally scalable. To add more robots, a new worker service can be spun up without modifying the orchestrator. To handle more tasks, the orchestrator can process them asynchronously.
- **Reliability:** The system is built with resilience in mind. The orchestrator's state is in-memory for speed, but the `tasks.csv` stream can be re-ingested if the service restarts. Failed task assignments are re-queued to prevent lost work.

***

### 4. Trade-offs and Rationale

- **Protocol Choice (RESTful HTTP):**
    - **Rationale:** A RESTful API was chosen for its simplicity, widespread tooling, and ease of debugging.
    - **Trade-off:** For a high-throughput, real-time system with thousands of robots, a more performant protocol like gRPC or a message-bus system (e.g., RabbitMQ, Kafka) would be more efficient, but would also add complexity to the project setup.

- **Containerization (Optional):**
    - **Rationale:** Dockerizing the services would ensure a consistent, isolated environment for deployment, preventing "it works on my machine" issues.
    - **Trade-off:** For this demo, I opted for a local Python environment and a shell script (`run_demo.sh`) for simplicity and quick iteration. The code is structured to be easily containerized later if needed.

***

### 5. Optional Deliverable: Observability Dashboard

I developed a simple, real-time dashboard using **Streamlit** to enhance system observability. This was designed as a separate, decoupled client application rather than a feature of the orchestrator service itself.

- **Design Philosophy:** By treating the dashboard as an external consumer of the API, I maintained a **clean separation of concerns**. The core orchestrator service remains focused solely on business logic (state management and task assignment) and is not burdened with rendering a UI.
- **Benefits:** This approach allows for independent development, deployment, and scaling of the dashboard. It also showcases a more robust, production-ready architecture where different parts of the system can evolve independently.