# VectorForge — Raster to Vector Micro-SaaS

## Project Overview
VectorForge is a standalone micro-SaaS that converts raster images (PNG, JPG, BMP, TIFF) to vector formats (SVG, DXF). It features a client-facing upload portal, shareable URLs, batch API, webhook integration, and per-conversion billing.

## Tech Stack
- **Backend:** Python 3.12+, FastAPI, SQLAlchemy (async), SQLite (MVP) / PostgreSQL (prod), vtracer (Rust-based conversion engine)
- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS, React Router, TanStack Query, Recharts
- **Auth:** JWT tokens (web portal) + API keys (`X-API-Key` header) for programmatic access
- **Infrastructure:** Docker Compose, nginx reverse proxy, Alembic migrations

## Project Structure
```
backend/           FastAPI application
  app/
    api/           Route modules (auth, conversions, share, webhooks, billing)
    core/          Security, dependencies, exceptions
    models/        SQLAlchemy ORM models (User, ApiKey, Conversion, Webhook)
    schemas/       Pydantic request/response schemas
    services/      Business logic (converter, storage, queue, webhook_sender, billing, share)
    workers/       Background task implementations
  tests/           Pytest test suite
  alembic/         Database migrations

frontend/          React SPA
  src/
    api/           Axios API client with auth interceptors
    components/    Reusable UI (DropZone, ConversionSettings, SVGPreview, FileList, etc.)
    hooks/         Custom hooks (useAuth, useConversion)
    pages/         Route pages (Upload, Batch, Dashboard, Login, SharedView)
    types/         TypeScript interfaces
```

## Key Commands
```bash
# Backend
cd backend && pip install -e ".[dev]"
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
python -m pytest tests/ -v

# Frontend
cd frontend && npm install
npm run dev          # Dev server on :5173
npm run build        # Production build
npx tsc --noEmit     # Type check

# Docker
docker compose up --build         # Production
docker compose -f docker-compose.dev.yml up  # Development
```

## API Endpoints
- `POST /api/auth/register` — Register user
- `POST /api/auth/login` — Login, get JWT
- `POST /api/auth/api-keys` — Create API key
- `POST /api/conversions` — Upload & convert single file
- `POST /api/conversions/batch` — Batch upload
- `GET /api/conversions/{id}` — Poll status
- `GET /api/conversions/{id}/download` — Download result
- `POST /api/conversions/{id}/share` — Create shareable link
- `GET /api/s/{token}` — Public shared view
- `POST /api/webhooks` — Register webhook
- `GET /api/usage` — Usage stats

## Conversion Engine
- Uses `vtracer` (Rust bindings via pip) — supports both `color` and `binary` modes
- User-facing settings map to vtracer params:
  - `detail_level` (1-10) → `filter_speckle`, `color_precision`
  - `smoothing` (1-10) → `corner_threshold`, `length_threshold`, `splice_threshold`
- DXF output via `svgpathtools` + `ezdxf` post-processing

## Architecture Decisions
- **No passlib** — uses `bcrypt` directly (passlib has Python 3.13 compatibility issues)
- **Background tasks** — FastAPI `BackgroundTasks` for MVP; swap to ARQ when Redis available
- **Storage abstraction** — `LocalStorageBackend` with protocol interface for S3 swap
- **Timezone-aware** — All datetimes use `datetime.now(UTC)`, never `utcnow()`
- **Dual auth** — Every authenticated endpoint accepts both JWT Bearer and X-API-Key

## Testing
- Backend: `pytest` with async fixtures, in-memory SQLite
- Always run `python -m pytest tests/ -v` after backend changes
- Always run `npx tsc --noEmit` after frontend changes
