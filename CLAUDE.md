# VectorForge — Raster to Vector Micro-SaaS

## Project Overview
VectorForge is a standalone micro-SaaS that converts raster images (PNG, JPG, BMP, TIFF, WEBP) to production-ready vector formats using a CNC-grade potrace pipeline. Outputs: SVG, PDF, EPS, PNG, BMP, G-code, with separated color layers. Features upload portal, shareable URLs, batch API, webhook integration, and per-conversion billing.

## Tech Stack
- **Backend:** Python 3.12+, FastAPI, SQLAlchemy (async), SQLite (MVP) / PostgreSQL (prod)
- **Conversion:** Potrace CNC pipeline (primary) + vtracer (fallback). 7-step: upscale, median filter, threshold, morph cleanup, gap-fill, Bezier trace, export
- **Export:** SVG, PDF (svglib+reportlab), EPS, PNG, BMP 300dpi, G-code (GRBL), JSON metadata, ZIP
- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS (dark mode), PWA
- **Auth:** JWT tokens (web) + API keys (`X-API-Key` header) for programmatic access
- **Infrastructure:** Docker Compose, nginx, Alembic, potrace binary

## Project Structure
```
backend/           FastAPI application
  app/
    api/           Route modules (auth, conversions, share, webhooks, billing)
    core/          Security, dependencies, exceptions
    models/        SQLAlchemy ORM (User, ApiKey, Conversion, Webhook)
    schemas/       Pydantic request/response
    services/      Business logic:
      converter.py       Auto-color detect + pipeline orchestration
      vectorize_cnc.py   7-step CNC potrace pipeline
      generate_viewer.py Interactive HTML layer viewer
      export_formats.py  PDF, EPS, G-code generators
      storage.py         Local storage (S3-swappable)
      webhook_sender.py  HMAC-signed webhook delivery
      billing.py         Usage tracking
    workers/       Background conversion tasks
  tests/           Pytest test suite (10 tests)
  alembic/         Database migrations
  potrace.exe      Windows potrace binary

frontend/          React SPA (dark mode PWA)
  src/
    api/client.ts          Axios API wrapper with auth
    components/            DropZone, ConversionSettings, SVGPreview, FileList, etc.
    hooks/                 useAuth, useConversion
    pages/                 Upload (staged flow), Batch, Dashboard, Login, SharedView

.claude/agents/    7 specialized agents
.claude/skills/    8 slash commands including /wrap
```

## Key Commands
```bash
# Backend
cd backend && pip install -e ".[dev]"
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
python -m pytest tests/ -v

# Frontend
cd frontend && npm install && npm run dev
npx tsc --noEmit     # type check
npm run build        # production build

# Both (Windows)
start.bat            # launches both in separate terminals

# Docker
docker compose up --build
```

## API (25 routes)
- `POST /api/auth/register|login` — Auth
- `POST /api/auth/api-keys` — Create API key
- `POST /api/conversions` — Upload + convert (anonymous or auth)
- `POST /api/conversions/batch` — Batch upload (auth required)
- `POST /api/conversions/analyze-colors` — Pre-conversion color analysis
- `GET /api/conversions/{id}` — Poll status
- `GET /api/conversions/{id}/download?format=svg|pdf|eps|png|bmp|gcode|json|original` — Download any format
- `GET /api/conversions/{id}/download-all` — ZIP of all files
- `GET /api/conversions/{id}/viewer` — Interactive HTML layer viewer
- `POST /api/conversions/{id}/share` — Shareable URL
- `GET /api/s/{token}` — Public shared view
- `CRUD /api/webhooks` — Webhook management
- `GET /api/usage` — Billing/usage stats

## Critical Rules
- **datetime:** Always `datetime.now(UTC)`, never `utcnow()`
- **bcrypt:** Use `bcrypt` directly, never `passlib`
- **SVG comments:** Never use `--` inside XML comments (breaks Illustrator)
- **Windows:** No Unicode in Python print() statements (use ASCII)
- **Colors:** Auto-detect merges clusters within 120 RGB distance, max 4 clusters
- **Potrace params:** Available via `potrace_bin` argument, not necessarily on PATH
- **vtracer params:** `length_threshold` not `segment_length`
- **Tailwind config:** Must use `.cjs` extension (package.json has "type": "module")

## Testing
- Backend: `python -m pytest tests/ -v` (10 tests)
- Frontend: `npx tsc --noEmit` (0 errors)
- E2E: Upload owl reference image, verify 2 layers (red + white), valid SVG, all 8 formats
