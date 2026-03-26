---
name: test-frontend
description: Type-check and build the frontend, report any errors
user_invocable: true
---

Run VectorForge frontend checks:

1. Change to the frontend directory: `cd frontend`
2. Run `npx tsc --noEmit` to type-check
3. Run `npm run build` to verify production build
4. Report any TypeScript errors or build warnings
5. If there are errors, fix them and re-run until clean
