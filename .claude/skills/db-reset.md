---
name: db-reset
description: Reset the development database — delete and recreate all tables
user_invocable: true
---

Reset the VectorForge development database:

1. Stop any running backend server
2. Delete the SQLite database: `rm -f data/vectorforge.db`
3. Optionally clear uploaded files: `rm -rf data/uploads/* data/results/*`
4. Start the backend to auto-create fresh tables: `cd backend && python -c "import asyncio; from app.database import init_db; asyncio.run(init_db())"`
5. Confirm tables were created
6. Report completion

WARNING: This destroys all data. Only use in development.
