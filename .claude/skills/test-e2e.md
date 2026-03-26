---
name: test-e2e
description: Full end-to-end test — upload, convert, verify all 8 formats, validate SVG, check ZIP
user_invocable: true
---

Run a full end-to-end test of the VectorForge API:

1. Check if backend is running at http://127.0.0.1:8000/health
2. If not running, start it: `cd backend && uvicorn app.main:app --host 127.0.0.1 --port 8000`
3. Execute these steps, reporting pass/fail:
   - Upload `References/Outputs/Sample/owl_v8_transparent.png`
   - Poll until completed or failed (max 60s)
   - Report: engine used, layers found, processing time
   - Validate SVG is well-formed XML with 2 layers
   - Download all 8 formats and verify each is > 100 bytes: svg, pdf, eps, png, bmp, gcode, json, original
   - Download ZIP and verify size
   - Test color analysis endpoint
4. Report summary table of all results
