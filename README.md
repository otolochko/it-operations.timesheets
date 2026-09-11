<div align="center">

# Jira Timesheets

Internal reporting dashboard and background synchronization engine for Jira Cloud worklogs.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14.2-black.svg?style=flat&logo=next.js)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg?style=flat&logo=postgresql)](https://www.postgresql.org/)
[![Docker Compose](https://img.shields.io/badge/Docker_Compose-Ready-2496ED.svg?style=flat&logo=docker)](https://docs.docker.com/compose/)

[Features](#features) • [Architecture](#architecture) • [Quick Start](#quick-start) • [Configuration](#configuration) • [API Reference](#api-reference) • [Project Structure](#project-structure) • [Deployment](#deployment)

</div>

---

## Features

### Timesheet Reporting

- **Author Matrix Grid**: View total hours logged across all team members organized in a matrix by day or ISO week, with dynamic period totals.
- **Issue Drill-Down**: Click any cell in the grid to open a detailed breakdown of individual Jira issues, issue summaries, logged hours, and worklog counts.
- **Summary Metrics**: Review aggregate numbers across the selected date range, including total logged hours, active author count, unique issue count, and average hours per author.

### Synchronization and Operations

- **Automated Background Ingestion**: Synchronize worklog entries from Jira Cloud on a scheduled cron cadence without impacting interface responsiveness.
- **Manual Sync Execution**: Trigger synchronization on demand with live run status tracking and poller updates.
- **Dynamic Schedule Administration**: Adjust cron expressions and target project key filters directly from the management interface without restarting services.

---

## Architecture

```mermaid
flowchart TD
    subgraph Client["Browser Interface"]
        UI["Next.js Dashboard"]
    end

    subgraph Server["Application Services"]
        API["FastAPI Backend"]
        Worker["APScheduler & Background Worker"]
    end

    subgraph Storage["Data Store"]
        DB[("PostgreSQL 16")]
    end

    subgraph External["External Cloud"]
        Jira["Jira Cloud REST API v3"]
    end

    UI -->|"HTTP /api requests"| API
    API -->|"Read-only SQL aggregation"| DB
    Worker -->|"Periodic & on-demand sync"| Jira
    Worker -->|"Atomic upserts & cursor updates"| DB
```

The architecture strictly separates user-facing reporting from external synchronization:

- **Read Path**: The Next.js dashboard communicates exclusively with the FastAPI backend. All timesheet queries and summary calculations execute as optimized SQL aggregations against PostgreSQL, guaranteeing that user requests never wait on external Jira network latency.
- **Sync Path**: Ingestion operates asynchronously in the background via APScheduler or dedicated worker threads. Incremental synchronization ingests new, updated, and deleted worklogs using an atomic watermark cursor to ensure consistency and idempotency.

---

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/)
- Alternatively for local development: Python 3.12+ and Node.js 22+

### 1. Configure Environment

Copy the example environment configuration to `.env` and fill in your Jira technical credentials:

```bash
cp .env.example .env
```

### 2. Launch Full Stack with Docker Compose

Start the PostgreSQL database, backend service, and frontend web server:

```bash
docker compose up --build
```

Once running, navigate to:
- Frontend Dashboard: [http://localhost:3000](http://localhost:3000)
- Backend API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)

### 3. Local Development

To run backend and frontend services directly on the host machine:

```bash
# Start PostgreSQL container
docker compose up -d postgres

# Run backend migrations and server
cd backend
source .venv/bin/activate
alembic upgrade head
uvicorn app.main:app --reload

# Run frontend server in a separate terminal
cd frontend
npm install
npm run dev
```

---

## Configuration

All configuration is driven by environment variables defined in `.env`:

### Database Configuration

| Variable | Description | Example |
|---|---|---|
| `POSTGRES_USER` | PostgreSQL user account | `timesheets` |
| `POSTGRES_PASSWORD` | PostgreSQL user password | `strongpassword` |
| `POSTGRES_DB` | PostgreSQL database name | `timesheets` |
| `DATABASE_URL` | SQLAlchemy connection URI | `postgresql+psycopg://timesheets:strongpassword@localhost:5432/timesheets` |

### Jira Cloud Integration

| Variable | Description | Example |
|---|---|---|
| `JIRA_BASE_URL` | Organization Jira Cloud base URL | `https://your-domain.atlassian.net` |
| `JIRA_EMAIL` | Service account email for Basic Auth | `jira-technical-user@example.com` |
| `JIRA_API_TOKEN` | API token generated for the technical user | `your-api-token` |
| `JIRA_MAX_RETRIES` | Maximum retry attempts for rate-limited requests | `5` |
| `JIRA_RETRY_BASE_SECONDS` | Initial backoff sleep delay in seconds | `1` |
| `JIRA_PROJECT_KEYS` | Comma-separated Jira project keys to sync | `PROJ1,PROJ2` |
| `JIRA_WORKLOG_JQL` | Optional JQL filter clause (reserved) | `""` |

### Synchronization and CORS

| Variable | Description | Default |
|---|---|---|
| `SYNC_DEFAULT_CRON` | Default 5-field cron schedule for automatic sync | `0 * * * *` |
| `CORS_ALLOWED_ORIGINS` | Comma-separated list of allowed browser origins | `http://localhost:3000` |
| `NEXT_PUBLIC_API_BASE_URL` | Backend URL consumed by the frontend client | `http://localhost:8000` |

---

## API Reference

### Timesheets

- `GET /api/timesheets`
  - **Parameters**: `from` (date, YYYY-MM-DD), `to` (date, YYYY-MM-DD), `group` (`day` or `week`)
  - **Description**: Returns the author-by-period matrix of logged hours and organization-wide summary metrics.
- `GET /api/timesheets/issues`
  - **Parameters**: `author` (account ID string), `from` (date, YYYY-MM-DD), `to` (date, YYYY-MM-DD)
  - **Description**: Returns an issue-level breakdown of logged time and worklog counts for a specific author.

### Synchronization Management

- `POST /api/sync/worklogs`
  - **Description**: Triggers an on-demand synchronization run on a background thread. Returns the run ID and status.
- `GET /api/sync/status`
  - **Description**: Returns metadata for the most recent sync execution and whether a sync is currently in progress.
- `GET /api/sync/schedule`
  - **Description**: Returns the active cron expression, project key filters, and last modification timestamp.
- `PUT /api/sync/schedule`
  - **Payload**: `{"cron_expression": "0 * * * *", "project_keys": ["PROJ1", "PROJ2"]}`
  - **Description**: Updates the cron schedule and project filters, rescheduling the background worker immediately.

---

## Project Structure

```
.
├── docker-compose.yml        # Orchestration for postgres, backend, and frontend
├── .env.example              # Template environment configuration
├── backend/
│   ├── app/
│   │   ├── core/             # Configuration, database connection, Jira HTTP client
│   │   ├── models/           # SQLAlchemy database entities
│   │   ├── routers/          # FastAPI endpoint controllers
│   │   ├── schemas/          # Pydantic data schemas
│   │   ├── services/         # Timesheet queries, sync logic, and APScheduler
│   │   └── main.py           # FastAPI application entrypoint
│   ├── alembic/              # Database migration scripts
│   ├── tests/                # Pytest test suite
│   ├── Dockerfile            # Backend container definition
│   └── requirements.txt      # Pinned Python dependencies
├── frontend/
│   ├── src/
│   │   ├── app/              # Next.js pages, layouts, and globals.css (including *.test.tsx siblings)
│   │   ├── components/       # Reusable UI widgets, panels, and forms (including *.test.tsx siblings)
│   │   └── lib/              # Backend API client and theme tokens
│   ├── Dockerfile            # Frontend container definition
│   └── package.json          # Node.js dependencies and scripts
└── docs/
    ├── claude/               # Topic-specific developer documentation
    ├── deployment.md         # Production deployment and operations guide
    └── documentation-rules.md# Repository documentation standard
```

---

## Deployment

Production deployments are containerized using Docker Compose:

- **Isolated Build Contexts**: Container `.dockerignore` files prevent local environment files or development artifacts from leaking into image layers.
- **Network Boundaries**: The application has no user authentication and must be placed behind an internal VPN or private network ingress with reverse proxy TLS termination.

For step-by-step installation, reverse proxy configuration, and zero-downtime database upgrade instructions, see [`docs/deployment.md`](docs/deployment.md).
