---
name: add-component
description: Create a new React component with TypeScript types and Tailwind styling
user_invocable: true
---

Create a new React component for VectorForge. The user will describe what the component should do.

Follow this checklist:

1. **Types** — Add any new TypeScript interfaces to `frontend/src/types/index.ts`
2. **Component** — Create the component file in `frontend/src/components/` or `frontend/src/pages/`
3. **API** — If the component needs data, add API functions to `frontend/src/api/client.ts`
4. **Hook** — If the component has complex state logic, create a hook in `frontend/src/hooks/`
5. **Route** — If it's a page, add the route to `frontend/src/App.tsx`
6. **Navigation** — If it's a page, add it to the nav links in `frontend/src/components/Layout.tsx`
7. **Type check** — Run `npx tsc --noEmit` to verify

Rules:
- Use TypeScript — no `any` types
- Functional components with hooks only
- Tailwind CSS for all styling — use the `brand-*` color palette
- Icons from `lucide-react`
- API calls via the `api/client.ts` axios wrapper
- Loading and error states must be handled
