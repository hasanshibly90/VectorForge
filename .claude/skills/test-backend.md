---
name: test-backend
description: Run the full backend test suite and report results
user_invocable: true
---

Run the VectorForge backend test suite:

1. Change to the backend directory: `cd backend`
2. Run `python -m pytest tests/ -v --tb=short`
3. Report the results clearly — number passed, failed, and any warnings
4. If tests fail, read the failing test and the relevant source code to diagnose the issue
5. Fix the issue and re-run tests until all pass
