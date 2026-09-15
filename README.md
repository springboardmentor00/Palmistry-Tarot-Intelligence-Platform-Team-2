# Aetheria — Palmistry & Tarot Intelligence Platform

Aetheria is a full-stack platform for symbolic self-reflection using **palm-image computer vision** and **Tarot reading workflows**. Milestone 4 adds executive/user analytics, reporting and exports, validation, containerization, production configuration, and monitoring while retaining the Milestone 1–3 application structure and UI.

## Scope

- Secure registration/login with JWT authentication and RBAC.
- User profile, goals, interests, notifications, recommendations, and isolated reading history.
- Palm image preprocessing, hand landmark detection when MediaPipe is available, edge/contour analysis, and persisted palm metrics.
- 78-card Tarot reference deck, supported spreads, server-authoritative draws, and persisted orientations.
- AI-assisted interpretation through an optional server-configured OpenAI provider. When no provider is configured, the application uses a deterministic symbolic interpretation based **only on the user's actual reading data**; it does not create users, readings, scores, or sample activity.
- Personality and life-trend analysis from actual profile/reading context.
- Weighted guidance scoring based on the documented model: palm confidence 30%, Tarot relevance 25%, personality alignment 20%, user context 15%, and reading consistency 10%.
- User, Tarot Reader, Spiritual Consultant, and Administrator dashboards.
- Executive analytics, 30-day reading/score series, recommendation completion, role breakdown, request telemetry, and specialist analytics.
- PDF and Excel report exports generated from persisted reading/interpretation data.
- Liveness/readiness health checks, request telemetry, structured application logging, Docker/Compose, and a production-oriented Nginx frontend.


## Repository layout

```text
palmistry-tarot-platform/
├── backend/
│   ├── app/
│   │   ├── api/              # authentication, business, admin, analytics
│   │   ├── config/           # environment configuration
│   │   ├── database/         # PostgreSQL + optional Mongo adapter
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic contracts
│   │   ├── services/         # CV, Tarot, scoring, AI, recommendations
│   │   └── utils/            # PDF/Excel reporting
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── index.html            # existing Milestone 1–3 UI, API-connected
│   ├── api-bridge.js         # backend integration layer
│   ├── Dockerfile
│   └── nginx.conf
├── index.html                # standalone copy of the preserved UI
├── docker-compose.yml
├── .env.example
└── .gitignore
```

## Local backend

Python 3.11 is recommended.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env
```

Set a real `JWT_SECRET` (at least 32 characters) and a PostgreSQL `DATABASE_URL`. `OPENAI_API_KEY` may remain empty if you want the deterministic symbolic interpretation engine.

Start from the repository root:

```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

API docs: `http://localhost:8000/docs`

## Frontend

```bash
cd frontend
npm ci
npm run build
npm run preview
```

The frontend build is Vite-based and retains the existing static UI. The production container serves it through Nginx and proxies `/api/*` and `/static/*` to FastAPI.

## Docker Compose

Create a local `.env` from `.env.example`, set at minimum:

```text
POSTGRES_PASSWORD=<strong-password>
JWT_SECRET=<random-secret-at-least-32-characters>
```

Then:

```bash
docker compose up --build
```

The browser application is served on port 80 and FastAPI on port 8000. PostgreSQL and MongoDB are internal Compose services with persistent named volumes.

## API highlights

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET/PUT /api/v1/users/me`
- `POST /api/v1/palm/analyze`
- `GET /api/v1/palm/readings`
- `GET /api/v1/tarot/cards`
- `POST /api/v1/tarot/readings`
- `GET /api/v1/tarot/readings`
- `POST /api/v1/combined/analyze`
- `GET /api/v1/insights/comprehensive`
- `GET /api/v1/insights/personality`
- `GET /api/v1/insights/life-trend`
- `GET /api/v1/analytics/user`
- `GET /api/v1/analytics/executive` (administrator)
- `GET /api/v1/analytics/reader` (reader/admin)
- `GET /api/v1/analytics/consultant` (consultant/admin)
- `GET /api/v1/reports/pdf/{reading_type}/{reading_id}`
- `GET /api/v1/reports/excel/{reading_type}/{reading_id}`
- `GET /api/v1/reports/pdf/personality`
- `GET /api/v1/reports/excel/personality`
- `GET /api/v1/reports/pdf/spiritual-guidance`
- `GET /api/v1/reports/excel/spiritual-guidance`
- `GET /api/v1/reports/pdf/insight-trend`
- `GET /api/v1/reports/excel/insight-trend`
- `GET /api/v1/admin/users` (administrator)
- `GET /health/live`
- `GET /health/ready`
- `GET /metrics`

## Security and data isolation

- Passwords are hashed with bcrypt; plaintext passwords are not persisted.
- JWTs are signed with an environment-provided secret.
- Public registration can only create the `USER` role. Elevated roles are assigned through an administrator-only endpoint.
- User reading, recommendation, and notification queries always filter by the authenticated user ID.
- Report exports validate ownership before reading report data.
- CORS is configured explicitly rather than using wildcard origins with credentials.
- No repository `.env`, database file, virtual environment, `node_modules`, generated cache, or sample user activity is included.

## Monitoring

FastAPI records per-process request count, 4xx/5xx counts, average latency, and uptime. Each request is logged with a generated request ID, method, path, status, and latency without logging credentials or request bodies. `/metrics` exposes a small Prometheus-compatible text surface; `/health/live` checks process liveness and `/health/ready` verifies the configured SQL database. Set `LOG_LEVEL` (for example, `INFO` or `WARNING`) through the environment to control application log verbosity.

## Validation status

Recommended target-environment validation:

```bash
python -m compileall backend/app
pytest -q
cd frontend && npm ci && npm run build && npm run lint
cd .. && docker compose config
```

In this delivery environment, Python syntax compilation and the dependency-free frontend build/lint checks were executed successfully. The backend pytest suite could not be executed because the runtime did not have the required Python packages installed and outbound package installation was unavailable. Docker Compose validation and container startup could not be executed because Docker is not installed in the validation environment. External cloud deployment, live OpenAI generation, and browser interaction require credentials/services that are intentionally not included in the repository.
