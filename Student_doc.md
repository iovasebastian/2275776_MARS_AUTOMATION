# SYSTEM DESCRIPTION:

The Mars Habitat Automation Platform is a distributed, event-driven system. It allows operators to monitor and control the base's status via the system dashboard and console.
The system dashboard displays various environmental data received from sensors in real time. Operators may control base actuators via the console and edit base automation rules.

# USER STORIES:

1) As a Habitat Operator, I want to view all active sensors and their latest readings on a unified dashboard, so that I can monitor the overall habitat environment at a glance.
2) As a Habitat Operator, I want the sensor data on my dashboard to update automatically in real-time, so that I always have the most current telemetry without needing to refresh the page.
3) As a Habitat Operator, I want to see specific measurement units (e.g., C, kW, L/min) displayed alongside sensor values, so that I can interpret the data correctly.
4) As a Habitat Operator, I want data from both slow-polling sensors and high-speed telemetry streams to be displayed in the same consistent format, so that I don't have to use different tools for different devices.
5) As a Habitat Operator, I want new sensors to be automatically discovered and integrated into my monitoring view, so that I don't have to manually configure the system every time a new device is wired up.
6) As a Habitat Operator, I want to clearly see the current operational state (ON/OFF) of all habitat actuators (e.g., cooling fans, heaters), so that I know exactly what life-support equipment is currently running.
7) As a Habitat Operator, I want to manually toggle the state of any actuator directly from the dashboard, so that I can immediately intervene and override the system during an emergency.
8) As a Habitat Operator, I want my manual actuator changes to be instantly reflected on the UI, so that I have immediate visual feedback that my command was executed.
9) As a Habitat Operator, I want the system to automatically turn actuators ON or OFF based on environmental data, so that the habitat remains safe even while I am sleeping.
10) As a Habitat Operator, I want to create new automation rules through a visual interface on the dashboard, so that I can quickly instruct the system how to react to new environmental threats.
11) As a Habitat Operator, I want to configure rule conditions using standard mathematical comparisons (<, <=, =, >, >=), so that I can set precise safety thresholds (e.g., trigger fan if temp > 28C).
12) As a Habitat Operator, I want to view a list of all currently active automation rules, so that I know exactly how the system is programmed to behave.
13) As a Habitat Operator, I want to edit existing automation rules, so that I can adjust safety thresholds as the mission parameters or seasons change.
14) As a Habitat Operator, I want to delete obsolete automation rules, so that they don't trigger unwanted or conflicting system behaviors.
15) As a Habitat Operator, I want the automation service to log every time an automation rule automatically triggers an actuator to the console output, so that I can trace the system's autonomous decisions via container logs.
16) As a Platform Administrator, I want to deploy the entire habitat automation platform using a single startup command (docker compose up), so that recovery time is minimized during critical system failures.
17) As a Platform Administrator, I want the system's internal communication to use a resilient message broker, so that sudden spikes in sensor data do not overwhelm the processing engines.
18) As a Platform Administrator, I want the data ingestion, rule evaluation, and web interface to run as separate isolated microservices, so that a crash in the web UI does not stop the background automation engine from keeping the crew alive.
19) As a Platform Administrator, I want all defined automation rules to be saved to a persistent database, so that critical safety logic is immediately restored without manual data entry after a system reboot.
20) As a Platform Administrator, I want the platform to automatically normalize all heterogeneous device payloads into a single standard event format internally, so that future developers can add new features without worrying about device-specific dialects.


# CONTAINERS:

## CONTAINER_NAME: ingestion-service

### DESCRIPTION:
Discovers simulator sensors, polls REST sensor endpoints, consumes telemetry WebSocket streams, normalizes heterogeneous payloads, and publishes normalized events to RabbitMQ.

### USER STORIES:
2) As a Habitat Operator, I want the sensor data on my dashboard to update automatically in real-time, so that I always have the most current telemetry without needing to refresh the page.
4) As a Habitat Operator, I want data from both slow-polling sensors and high-speed telemetry streams to be displayed in the same consistent format, so that I don't have to use different tools for different devices.
5) As a Habitat Operator, I want new sensors to be automatically discovered and integrated into my monitoring view, so that I don't have to manually configure the system every time a new device is wired up.
20) As a Platform Administrator, I want the platform to automatically normalize all heterogeneous device payloads into a single standard event format internally, so that future developers can add new features without worrying about device-specific dialects.

### PORTS:
No external port mapping in `docker-compose.yml` (container exposes 8001 internally only).

### DESCRIPTION:
Ingestion service runs as a background producer: discovers sensors, polls REST endpoints, listens to telemetry WebSockets, normalizes payloads, and publishes events to RabbitMQ. It does not expose business APIs.

### PERSISTANCE EVALUATION
No persistence required. Service is stateless and forwards normalized events.

### EXTERNAL SERVICES CONNECTIONS
- Simulator: `http://simulator:8080`
- RabbitMQ: `amqp://guest:guest@broker:5672/`

### MICROSERVICES:

#### MICROSERVICE: ingestion-be
- TYPE: backend
- DESCRIPTION: Normalizes REST and WebSocket simulator payloads into `NormalizedEvent` and publishes to broker topics for `api-service` and `automation-service`.
- PORTS: 8001
- TECHNOLOGICAL SPECIFICATION:
  FastAPI + asyncio, `httpx` for REST polling, `websockets` for telemetry streams, and `aio-pika` for RabbitMQ publishing.
- SERVICE ARCHITECTURE:
  Lifespan-managed background workers: one periodic poll loop + multiple WebSocket listener tasks.

- ENDPOINTS:
	| HTTP METHOD | URL | Description | User Stories |
	| ----------- | --- | ----------- | ------------ |
	| N/A | N/A | Background producer service (no exposed business API endpoints). | 2, 4, 5, 20 |


## CONTAINER_NAME: rabbitmq_broker

### DESCRIPTION:
Provides asynchronous pub/sub communication through RabbitMQ topic exchange `normalized_events`.

### USER STORIES:
17) As a Platform Administrator, I want the system's internal communication to use a resilient message broker, so that sudden spikes in sensor data do not overwhelm the processing engines.

### PORTS:
5672:5672 (AMQP)
15672:15672 (Management UI)

### DESCRIPTION:
RabbitMQ broker provides resilient internal pub/sub messaging using a topic exchange and durable queues.

### PERSISTANCE EVALUATION
Configured for durable exchange/queues and persistent message delivery mode in publisher code.

### EXTERNAL SERVICES CONNECTIONS
No external dependencies.

### MICROSERVICES:

#### MICROSERVICE: rabbitmq-broker
- TYPE: middleware
- DESCRIPTION: Standard RabbitMQ broker used by ingestion/api/automation services.
- PORTS: 5672, 15672
- TECHNOLOGICAL SPECIFICATION:
  Official `rabbitmq:3-management-alpine` image.
- SERVICE ARCHITECTURE:
  Topic exchange with two durable queues and routing keys:
  - Queue `api_service_queue` bound to `normalized.api`
  - Queue `automation_service_queue` bound to `normalized.automation`


## CONTAINER_NAME: automation-service

### DESCRIPTION:
Consumes normalized events, loads automation rules from shared SQLite DB, evaluates thresholds, and triggers actuator changes in simulator.

### USER STORIES:
9) As a Habitat Operator, I want the system to automatically turn actuators ON or OFF based on environmental data, so that the habitat remains safe even while I am sleeping.
11) As a Habitat Operator, I want to configure rule conditions using standard mathematical comparisons (<, <=, =, >, >=), so that I can set precise safety thresholds (e.g., trigger fan if temp > 28C).
15) As a Habitat Operator, I want the automation service to log every time an automation rule automatically triggers an actuator to the console output, so that I can trace the system's autonomous decisions via container logs.
19) As a Platform Administrator, I want all defined automation rules to be saved to a persistent database, so that critical safety logic is immediately restored without manual data entry after a system reboot.

### PORTS:
No external port mapping in compose (container exposes 8002 internally only).

### DESCRIPTION:
Automation service consumes normalized events, evaluates rules from SQLite, and triggers simulator actuators when thresholds match.

### PERSISTANCE EVALUATION
Uses shared SQLite file `/app/data/rules.db` via Docker volume `shared_sqlite_data`.

### EXTERNAL SERVICES CONNECTIONS
- RabbitMQ broker for normalized event consumption.
- Simulator actuator REST API for state change operations.

### MICROSERVICES:

#### MICROSERVICE: automation-be
- TYPE: backend
- DESCRIPTION: Event-driven rule engine.
- PORTS: 8002
- TECHNOLOGICAL SPECIFICATION:
  FastAPI + `aio-pika` + SQLAlchemy + `httpx`.
- SERVICE ARCHITECTURE:
  Startup creates async RabbitMQ consumer task. For each event, metric values are compared with DB rules and actuator commands are sent when conditions are met.

- ENDPOINTS:
	| HTTP METHOD | URL | Description | User Stories |
	| ----------- | --- | ----------- | ------------ |
	| GET | /health | Runtime health (running flag and cached metric count). | 9 |

- DB STRUCTURE:
  **_rules_** : | **_id_** | sensor_name | operator | threshold_value | actuator_name | action_state |


## CONTAINER_NAME: api-service

### DESCRIPTION:
Backend-for-frontend service providing rule CRUD, actuator pass-through endpoints, latest data endpoint, DB schema endpoint, and WebSocket stream.

### USER STORIES:
1) As a Habitat Operator, I want to view all active sensors and their latest readings on a unified dashboard, so that I can monitor the overall habitat environment at a glance.
2) As a Habitat Operator, I want the sensor data on my dashboard to update automatically in real-time, so that I always have the most current telemetry without needing to refresh the page.
3) As a Habitat Operator, I want to see specific measurement units (e.g., C, kW, L/min) displayed alongside sensor values, so that I can interpret the data correctly.
6) As a Habitat Operator, I want to clearly see the current operational state (ON/OFF) of all habitat actuators (e.g., cooling fans, heaters), so that I know exactly what life-support equipment is currently running.
7) As a Habitat Operator, I want to manually toggle the state of any actuator directly from the dashboard, so that I can immediately intervene and override the system during an emergency.
10) As a Habitat Operator, I want to create new automation rules through a visual interface on the dashboard, so that I can quickly instruct the system how to react to new environmental threats.
12) As a Habitat Operator, I want to view a list of all currently active automation rules, so that I know exactly how the system is programmed to behave.
13) As a Habitat Operator, I want to edit existing automation rules, so that I can adjust safety thresholds as the mission parameters or seasons change.
14) As a Habitat Operator, I want to delete obsolete automation rules, so that they don't trigger unwanted or conflicting system behaviors.
19) As a Platform Administrator, I want all defined automation rules to be saved to a persistent database, so that critical safety logic is immediately restored without manual data entry after a system reboot.

### PORTS:
8003:8003

### DESCRIPTION:
API service exposes REST endpoints for latest sensor data, actuators, and rule CRUD, and a WebSocket stream for real-time updates.

### PERSISTANCE EVALUATION
Uses shared SQLite volume (`shared_sqlite_data`) and keeps latest events in in-memory cache.

### EXTERNAL SERVICES CONNECTIONS
- RabbitMQ for consuming normalized events.
- Simulator REST API for actuator querying/changing.

### MICROSERVICES:

#### MICROSERVICE: api-be
- TYPE: backend
- DESCRIPTION: REST + WebSocket APIs for frontend dashboard.
- PORTS: 8003
- TECHNOLOGICAL SPECIFICATION:
  FastAPI + SQLAlchemy + `aio-pika` + `httpx`.
- SERVICE ARCHITECTURE:
  Startup creates RabbitMQ consumer, updates in-memory `latest_events`, and broadcasts to connected WebSocket clients.

- ENDPOINTS:
	| HTTP METHOD | URL | Description | User Stories |
	| ----------- | --- | ----------- | ------------ |
	| GET | /latest | Returns latest cached sensor events. | 1, 3 |
	| POST | /new-rule | Create automation rule in SQLite. | 10 |
	| GET | /rules | List all rules. | 12 |
	| PUT | /update-rule | Update an existing rule. | 13 |
	| DELETE | /delete-rule/{id} | Delete rule by id. | 14 |
	| GET | /actuators | Fetch current actuator states from simulator. | 6 |
	| POST | /change-actuator/{actuator}/{state} | Manually set actuator state via simulator API. | 7 |
	| WS | /ws | WebSocket stream: snapshot + incremental events. | 2 |

- DB STRUCTURE:
  **_rules_** : | **_id_** | sensor_name | operator | threshold_value | actuator_name | action_state |


## CONTAINER_NAME: react_dashboard

### DESCRIPTION:
React dashboard for monitoring sensors/telemetry, controlling actuators, and managing automation rules.

### USER STORIES:
1) As a Habitat Operator, I want to view all active sensors and their latest readings on a unified dashboard, so that I can monitor the overall habitat environment at a glance.
2) As a Habitat Operator, I want the sensor data on my dashboard to update automatically in real-time, so that I always have the most current telemetry without needing to refresh the page.
3) As a Habitat Operator, I want to see specific measurement units (e.g., C, kW, L/min) displayed alongside sensor values, so that I can interpret the data correctly.
4) As a Habitat Operator, I want data from both slow-polling sensors and high-speed telemetry streams to be displayed in the same consistent format, so that I don't have to use different tools for different devices.
6) As a Habitat Operator, I want to clearly see the current operational state (ON/OFF) of all habitat actuators (e.g., cooling fans, heaters), so that I know exactly what life-support equipment is currently running.
7) As a Habitat Operator, I want to manually toggle the state of any actuator directly from the dashboard, so that I can immediately intervene and override the system during an emergency.
8) As a Habitat Operator, I want my manual actuator changes to be instantly reflected on the UI, so that I have immediate visual feedback that my command was executed.
10) As a Habitat Operator, I want to create new automation rules through a visual interface on the dashboard, so that I can quickly instruct the system how to react to new environmental threats.
11) As a Habitat Operator, I want to configure rule conditions using standard mathematical comparisons (<, <=, =, >, >=), so that I can set precise safety thresholds (e.g., trigger fan if temp > 28C).
12) As a Habitat Operator, I want to view a list of all currently active automation rules, so that I know exactly how the system is programmed to behave.
13) As a Habitat Operator, I want to edit existing automation rules, so that I can adjust safety thresholds as the mission parameters or seasons change.
14) As a Habitat Operator, I want to delete obsolete automation rules, so that they don't trigger unwanted or conflicting system behaviors.

### PORTS:
3000:3000

### DESCRIPTION:
Frontend is a React single-page dashboard served via Nginx for monitoring sensors, telemetry charts, actuators, and rule management.

### PERSISTANCE EVALUATION
No server-side DB in frontend. Uses browser `localStorage` as fallback rule cache when backend fails.

### EXTERNAL SERVICES CONNECTIONS
- Connects to `api-service` REST endpoints and WebSocket endpoint.

### MICROSERVICES:

#### MICROSERVICE: client-fe
- TYPE: frontend
- DESCRIPTION: Single-page React UI served by Nginx.
- PORTS: 3000
- TECHNOLOGICAL SPECIFICATION:
  React + Vite build; static assets served by Nginx.
- SERVICE ARCHITECTURE:
  Single-page application with two views: Operations Overview and Telemetry Charts.