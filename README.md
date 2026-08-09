# Traffic Violation Detection Dashboard

A professional smart traffic monitoring platform that combines AI-based object detection, violation monitoring, evidence capture, and a React-based dashboard.

## Overview

This repository contains two main components:

- `backend/` — FastAPI service for camera management, violation detection, evidence storage, and analytics.
- `frontend/` — React + Vite dashboard for live monitoring, search, and reporting.
- `docker-compose.yml` — Local environment orchestration with PostgreSQL, Redis, backend, and frontend.

## Key Features

- Vehicle and object detection from live or synthetic camera streams
- Violation event generation, evidence capture, and metadata storage
- REST API for cameras, violations, dashboards, and search
- Front-end dashboard for real-time monitoring and historical review
- Quantum-inspired signal control for traffic phase optimisation
- Demo mode for local testing without model weights

## Technology Stack

- Backend: Python, FastAPI, SQLAlchemy
- Database: PostgreSQL (Docker), SQLite fallback
- Cache / streaming: Redis
- AI / CV: OpenCV, Ultralytics YOLO, PaddleOCR
- Frontend: React, Vite, Recharts
- Deployment: Docker, Docker Compose

## Project Structure

```text
quantum computing project in traffic/
├── backend/
│   ├── app/
│   │   ├── ai/               # detection, tracking, OCR, violation logic
│   │   ├── api/              # FastAPI routes and endpoints
│   │   ├── core/             # configuration and security helpers
│   │   ├── db/               # ORM models and database sessions
│   │   ├── schemas/          # Pydantic request/response models
│   │   ├── scripts/          # data seeding and demo tools
│   │   ├── services/         # evidence and notification services
│   │   ├── stream/           # stream processing pipeline
│   │   └── main.py           # FastAPI application entry point
│   └── requirements.txt
├── frontend/                 # React dashboard application
├── docker-compose.yml        # container orchestration
└── README.md                 # project documentation
```

## Getting Started

### Option 1: Docker Compose

```bash
cp .env.example .env
docker-compose up --build
```

Open the application in your browser:

- Backend API docs: `http://localhost:8000/docs`
- Frontend dashboard: `http://localhost:3000`

### Option 2: Local Development

#### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m app.scripts.seed_data
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Environment Configuration

Configure the backend using environment variables. Common settings include:

- `DATABASE_URL` — database connection string
- `REDIS_URL` — Redis connection string
- `AI_MODE` — `demo` or `live`
- `EVIDENCE_DIR` — evidence storage directory
- `VITE_API_URL` — frontend API base URL

## API Reference

The backend exposes endpoints under `/api/v1`.

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| POST | `/api/v1/auth/login` | Authenticate and obtain a JWT token |
| GET | `/api/v1/cameras` | List registered cameras |
| POST | `/api/v1/cameras` | Register a new camera |
| GET | `/api/v1/violations` | Retrieve violation records |
| POST | `/api/v1/violations` | Create a violation event |
| GET | `/api/v1/violations/{id}` | Retrieve violation details and evidence |
| GET | `/api/v1/dashboard/stats` | Retrieve dashboard analytics data |
| GET | `/api/v1/dashboard/heatmap` | Retrieve hot-spot data |
| GET | `/api/v1/search/plates/{plate}` | Search violations by license plate |
| GET | `/api/v1/detections/live` | Live detection stream |
| GET | `/api/v1/quantum/overview` | Retrieve quantum signal-control network overview |
| POST | `/api/v1/quantum/intersections/{id}/optimise` | Optimise a signal phase at an intersection |
| POST | `/api/v1/quantum/intersections/{id}/phase/{phase}` | Manually set a phase (`all_red` / `pedestrian`) |

> Use the built-in OpenAPI docs at `/docs` for request examples and API exploration.

## Quantum Signal Control

The dashboard includes a **Quantum Signal Control** page (`/quantum-control`) featuring a quantum-inspired simulation for traffic phase optimisation.

- **Network overview** — aggregated queue, estimated delay, active camera inputs, and pending safety alerts.
- **Per-intersection controls** — optimise the current phase (chooses the highest-demand safe phase with a green duration of 20–60 s) or force an `all_red` / `pedestrian` phase.
- **Auto-refresh** every 10 seconds.
- **RBAC** — overview is available to `admin`/`officer`/`analyst`; control actions require `admin`/`officer` and are audit-logged.
- **Disclaimer** — this is a simulation; field signals must remain subject to certified controllers and operator approval.

## Demo Mode

Run the platform in demo mode when real detection model weights are unavailable.

- Set `AI_MODE=demo`
- Start the backend and use the demo environment for testing

## Dependencies

- Backend dependencies: `backend/requirements.txt`
- Frontend dependencies: `frontend/package.json`

## Notes

- Backend implementation: FastAPI with SQLAlchemy and Redis support.
- Frontend implementation: React and Vite.
- Deployment: Docker Compose connects PostgreSQL, Redis, backend, and frontend.

## Security

- Password hashing via bcrypt
- JWT authentication with role-based access control
- Audit logging for sensitive operations
- Optional evidence encryption via AES-256 (`ENCRYPT_EVIDENCE=true`)
- Evidence retention controlled via `EVIDENCE_RETENTION_DAYS`

## License

This repository is intended for development and evaluation. Review applicable privacy, data protection, and regulatory requirements before using in production.

## Default Access

The login form uses **usernames** (not emails):

| Username | Password | Role |
| -------- | -------- | ---- |
| `admin` | `admin123` | Admin |
| `officer` | `officer123` | Officer |
| `analyst` | `analyst123` | Analyst |

> Note: The backend `/auth/login` endpoint expects a **JSON** body (`{"username": "...", "password": "..."}`). It does not accept `application/x-www-form-urlencoded`.

