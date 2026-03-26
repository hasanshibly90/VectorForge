---
name: test-e2e
description: Run a full end-to-end test of the API — register, upload, convert, download, share
user_invocable: true
---

Run a full end-to-end test of the VectorForge API:

1. Check if backend is running at http://127.0.0.1:8000/health
2. If not running, start it: `cd backend && uvicorn app.main:app --host 127.0.0.1 --port 8000`
3. Execute these steps in order, reporting pass/fail for each:
   - Register a user via POST /api/auth/register
   - Upload `References/owl_v8_transparent.png` via POST /api/conversions
   - Poll GET /api/conversions/{id} until status is "completed" or "failed"
   - Download the SVG via GET /api/conversions/{id}/download
   - Create a share link via POST /api/conversions/{id}/share
   - Verify the shared link works without auth via GET /api/s/{token}
   - Create an API key and upload `References/owl_v8_300dpi.bmp` using X-API-Key auth
   - Check usage stats via GET /api/usage
4. Report a summary table of all test results
