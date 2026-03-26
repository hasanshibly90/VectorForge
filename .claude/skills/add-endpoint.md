---
name: add-endpoint
description: Scaffold a new API endpoint with route, schema, service, and test
user_invocable: true
---

Create a new API endpoint for VectorForge. The user will describe what the endpoint should do.

Follow this checklist:

1. **Schema** — Create or update Pydantic request/response models in `backend/app/schemas/`
2. **Service** — Create or update business logic in `backend/app/services/`
3. **Route** — Add the endpoint handler in the appropriate `backend/app/api/*.py` file
4. **Router** — Ensure the route is registered in `backend/app/api/router.py`
5. **Auth** — Apply `Depends(get_current_user)` or `Depends(get_optional_user)` as appropriate
6. **Test** — Add a test case in `backend/tests/`
7. **Frontend** — Add the API client function in `frontend/src/api/client.ts`
8. **Run tests** — Execute `python -m pytest tests/ -v` to verify

Rules:
- Use `datetime.now(UTC)`, never `utcnow()`
- Use proper HTTP status codes (201 for creation, 204 for deletion)
- Return Pydantic `response_model` on all endpoints
- Use `Query(pattern=...)` not `Query(regex=...)`
