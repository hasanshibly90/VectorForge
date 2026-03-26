---
name: start-dev
description: Start both backend and frontend development servers
user_invocable: true
---

Start the VectorForge development environment:

1. Kill any existing uvicorn or vite processes that might conflict
2. Start the backend: `cd backend && uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload`
3. Start the frontend: `cd frontend && npm run dev`
4. Verify both are running:
   - Backend: `curl http://127.0.0.1:8000/health`
   - Frontend: `curl -o /dev/null -w '%{http_code}' http://127.0.0.1:5173`
5. Report the URLs:
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - Swagger docs: http://localhost:8000/docs

Note: Run these in the user's terminal if background processes don't persist.
