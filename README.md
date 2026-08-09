# Traffic Violation Detection Dashboard

A professional smart-traffic platform that combines AI-based object detection, violation monitoring, evidence capture, **mobile camera streaming** and a React dashboard with quantum-inspired signal control.

> **Companion repository:** the [Traffic-Violation-Detection-mobile](https://github.com/SumanthBandla/Traffic-Violation-Detection-mobile) app turns any smartphone into a **remote traffic camera** that streams live video into this platform.

## Overview

This repository contains the backend and web dashboard:

- `backend/` — FastAPI service for camera management (fixed + mobile), live stream ingest, AI detection, violation generation, evidence storage, analytics, and quantum signal-control simulation.
- `frontend/` — React + Vite dashboard for live monitoring, cameras, violations, search, and quantum control.
- `docker-compose.yml` — local orchestration with PostgreSQL, Redis, backend, and frontend.

## System Architecture

```text
   SMARTPHONE (mobile repo)                      DASHBOARD (this repo)
 ┌─────────────────────────┐        ┌───────────────────────────────────────┐
 │  Mobile Camera PWA      │        │  FastAPI Backend                      │
 │  · Camera capture       │  WS    │  · /api/v1/stream/{id}/ingest  ◀──────┘
 │  · GPS / location       │ frames │  · AI Detection (YOLO / demo)          │
 │  · Health heartbeat ────┼──────▶ │  · Tracking + Violation Engine         │
 │  · Registration ────────┼──────▶ │  · Evidence + Detection Logs           │
 │                         │  REST  │  · Quantum Signal Control (sim)        │
 └─────────────────────────┘        └──────┬────────────┬──────────┬─────────┘
                                           │  WS live   │  REST    │
                                           ▼            ▼          ▼
                                    ┌───────────┐  ┌──────────┐  ┌─────────┐
                                    │ PostgreSQL│  │  Redis   │  │ Evidence│
                                    │ / SQLite  │  │ (stream) │  │ storage │
                                    └───────────┘  └──────────┘  └─────────┘
                                           ▲
                                           │  /api/v1 (REST + WebSocket)
                                           ▼
                                   React Dashboard
                              Live Monitoring · Cameras ·
                              Violations · Analytics · Quantum Control
```

**Key integration flows**

1. **Phone → Backend:** the mobile PWA pushes JPEG frames over a WebSocket (`/api/v1/stream/{camera_id}/ingest`). The backend runs the detection pipeline on each frame.
2. **Backend → Dashboard:** the dashboard subscribes to `/api/v1/detections/live` and receives annotated frames, detections, violations and camera status in real time — no page refresh needed.
3. **Violations:** when the violation engine fires, the backend stores the event **and** evidence image (via the existing evidence system) and broadcasts it to the dashboard.
4. **Quantum control:** mobile camera detections contribute vehicle counts to intersection demand, feeding the quantum-inspired optimisation simulation.

## Getting Started

### Option 1: Docker Compose

```bash
cp .env.example .env
docker-compose up --build
```

- Backend API docs: `http://localhost:8000/docs`
- Dashboard: `http://localhost:3000`

### Option 2: Local Development

#### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate      # macOS / Linux
pip install -r requirements.txt
python -m app.scripts.seed_data
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

> Run with `--host 0.0.0.0` so phones on the same Wi-Fi can reach the API.

#### Frontend

```bash
cd frontend
npm install
npm run dev                     # http://localhost:5173
```

The Vite dev server proxies `/api` and WebSocket traffic to `http://localhost:8000`, so no extra CORS configuration is needed locally.

## Environment Variables (backend)

| Variable | Description | Default |
| -------- | ----------- | ------- |
| `DATABASE_URL` | SQLAlchemy connection string | `sqlite:///./traffic.db` |
| `REDIS_URL` | Optional Redis (falls back to in-memory) | *(empty)* |
| `SECRET_KEY` | JWT signing key — **change in production** | demo value |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT lifetime | `1440` |
| `AI_MODE` | `demo` (no weights) or `live` (YOLO) | `demo` |
| `YOLO_MODEL_PATH` | Path to YOLO weights (live mode) | `weights/yolov11n.pt` |
| `CONFIDENCE_THRESHOLD` | Detection confidence cutoff | `0.35` |
| `STREAM_MAX_WIDTH` | Ingest frames downscaled to this width | `960` |
| `STREAM_QUALITY` | JPEG quality for broadcast frames | `80` |
| `STREAM_MAX_FPS` | Target ingest frame rate | `15` |
| `HEALTH_STALE_AFTER_SECONDS` | Camera offline threshold | `30` |
| `EVIDENCE_DIR` | Evidence storage directory | `storage/evidence` |
| `ENCRYPT_EVIDENCE` | AES-256 encrypt evidence files | `false` |
| `EVIDENCE_RETENTION_DAYS` | Retention window | `180` |
| `CORS_ORIGINS` | Allowed browser origins (JSON array or CSV) | local dev origins |

Frontend: `VITE_API_URL` (build-time) or the Vite proxy (default).

## API Reference

Base URL: `/api/v1`

### Authentication
| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| POST | `/auth/login` | Login (`{"username","password"}`) → JWT + user |

### Cameras (fixed + mobile)
| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| GET | `/cameras` | List cameras (`?camera_type=fixed\|mobile`) |
| POST | `/cameras` | Register camera (mobile clients include `device_id`) |
| GET | `/cameras/{id}` | Camera detail |
| PATCH | `/cameras/{id}` | Update camera |
| POST | `/cameras/{id}/heartbeat` | Health/GPS update from mobile client |
| POST | `/cameras/{id}/status` | Set streaming status on/off |

### Streaming (mobile integration)
| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| WS | `/stream/{camera_id}/ingest?token=…` | Phone pushes JPEG frames; AI runs server-side |
| GET | `/stream/{camera_id}/snapshot` | Latest annotated frame (JPEG) |
| GET | `/stream/{camera_id}/status` | Stream status for a camera |
| WS | `/detections/live?token=…` | Dashboard live channel (frames, violations, status) |

Live channel control messages: `{"type":"subscribe","camera_id":5}` / `{"type":"unsubscribe","camera_id":5}` / `{"type":"ping"}`.

### Violations & Evidence
| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| GET | `/violations` | List violations (`?camera_id&violation_type&status`) |
| GET | `/violations/{id}` | Violation detail with evidence |
| POST | `/violations` | Create a violation |
| GET | `/evidence/{id}/content` | Serve evidence image (`?token=…` or bearer) |

### Dashboard & Analytics
| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| GET | `/dashboard/stats` | Stats, by-type/by-status breakdowns |
| GET | `/dashboard/heatmap` | Location heatmap data |
| GET | `/search/plates/{plate}` | Plate lookup |
| GET | `/search/violations?q=…` | Violation search |

### Quantum Signal Control (simulation)
| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| GET | `/quantum/overview` | Network + per-intersection overview |
| POST | `/quantum/intersections/{id}/optimise` | Optimise phase (admin/officer, audit-logged) |
| POST | `/quantum/intersections/{id}/phase/{phase}` | Force phase (`all_red`/`pedestrian`/…) |

> **Safety disclaimer:** the quantum component is a **simulation/decision-support system**. It must never be connected directly to real-world traffic lights; recommendations require operator approval.

## AI Mode

- `AI_MODE=demo` — deterministic synthetic detections. The full streaming → detection → tracking → violation → evidence → dashboard pipeline works with **no model weights** (default).
- `AI_MODE=live` — real Ultralytics YOLO. Install `ultralytics` and place weights at `YOLO_MODEL_PATH`.

## Mobile Camera Integration

The phone registers as a `mobile` camera with a persistent `device_id`. Re-registration returns the same camera (idempotent). While streaming:

- The phone sends **only frames** — no AI happens on the device.
- The backend annotates frames with detections and broadcasts them to the dashboard's Live Monitoring page.
- Violations are stored with evidence and appear automatically in the dashboard.
- The phone sends periodic heartbeats (status, GPS, battery) via `/cameras/{id}/heartbeat`.

## Security

- Password hashing via bcrypt (legacy seed hashes also supported)
- JWT authentication with role-based access control (`admin`, `officer`, `analyst`, mobile clients authenticate as `officer`)
- Audit logging for sensitive operations (login, camera registration, quantum control)
- Optional evidence encryption via AES-256 (`ENCRYPT_EVIDENCE=true`)
- No hard-coded secrets — configure `SECRET_KEY` and URLs via environment variables
- Camera ingestion requires a valid JWT; only authorized devices (`device_id` + valid token) can stream

## Default Access

| Username | Password | Role |
| -------- | -------- | ---- |
| `admin` | `admin123` | Admin |
| `officer` | `officer123` | Officer |
| `analyst` | `analyst123` | Analyst |

## Mobile Camera Local-Network Testing

1. Start the backend with `--host 0.0.0.0`.
2. Find your laptop's LAN IP (`ipconfig` on Windows / `ipconfig getifaddr en0` on macOS).
3. Start the mobile app with `VITE_API_URL=http://<LAN_IP>:8000` (or set it in the mobile repo's `public/config.js`).
4. Open the mobile app on the phone, log in, register the camera, grant camera + location permissions, and press **START STREAM**.
5. Open the dashboard → **Live Monitoring**, select the mobile camera, and watch the AI-annotated stream and violations appear in real time.
6. Check **Quantum Control** — the mobile camera now contributes to intersection traffic demand.

## Notes

- Backend: FastAPI, SQLAlchemy, OpenCV (demo/live), optional YOLO.
- Frontend: React + Vite + Recharts.
- Deployment: Docker Compose (PostgreSQL + Redis + backend + frontend), or Vite static build + FastAPI behind a reverse proxy.
