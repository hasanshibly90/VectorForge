---
name: wrap
description: End-of-session wrap-up — runs all tests, updates memory/skills/agents, verifies project health
user_invocable: true
---

# Wrap-Up Checklist

Run this at the end of every work session to ensure the project is clean and all knowledge is persisted.

## 1. Run All Tests

```bash
# Backend tests
cd backend && python -m pytest tests/ -v --tb=short

# Frontend type check
cd frontend && npx tsc --noEmit

# Frontend build
cd frontend && npm run build
```

Report pass/fail counts. If any fail, fix them before proceeding.

## 2. Verify Backend Starts

```bash
cd backend && python -c "from app.main import app; print('Backend OK')"
```

Check all routes are registered:
```bash
python -c "
from app.main import app
routes = [r.path for r in app.routes if hasattr(r, 'path')]
print(f'{len(routes)} routes registered')
"
```

## 3. Run E2E Smoke Test

If the backend is running on :8000:
- POST /api/conversions with a test image
- Poll until completed or failed
- Verify SVG output is valid XML
- Verify ZIP download contains all files
- Report: engine used, layers found, output formats available

## 4. Update Memory

Check each memory file in `~/.claude/projects/.../memory/` and update if:
- Any architecture decisions changed during this session
- Any new bugs were discovered and fixed (add to feedback memories)
- Any new external references were found
- Any project goals or timelines changed

Specifically check:
- `project_vectorforge.md` — still accurate?
- `project_potrace_pipeline.md` — any pipeline changes?
- `feedback_bcrypt.md` — still relevant?
- `feedback_vtracer_params.md` — still relevant?
- `feedback_datetime.md` — still relevant?
- `reference_api_docs.md` — any new endpoints to document?

Create NEW memory files for any significant discoveries from this session.

## 5. Update CLAUDE.md

Read `CLAUDE.md` at project root. Update if:
- New commands were added
- New API endpoints were added
- Architecture changed
- New dependencies were added
- New file structure was created

## 6. Update Skills

Check each skill in `.claude/skills/` — update if:
- Test commands changed
- New endpoints need to be tested in `test-e2e.md`
- New components need to be scaffolded in `add-component.md`
- New formats need to be covered in `add-endpoint.md`

## 7. Update Agents

Check each agent in `.claude/agents/` — update if:
- Tech stack changed (new libraries, removed libraries)
- Architecture patterns changed
- New file locations or conventions

## 8. Git Status

```bash
git status
git log --oneline -5
```

Report:
- Any uncommitted changes
- Last commit message
- Whether a push is needed

## 9. Summary

Output a concise summary:
- Tests: X/X passed
- Routes: N registered
- Memory files: updated/unchanged
- Skills: updated/unchanged
- Agents: updated/unchanged
- Git: clean/dirty, last commit
- Issues found: list any
