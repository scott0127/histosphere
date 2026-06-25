# Test Layout

This project keeps frontend and backend tests separated by runtime.

## Frontend

- `tests/frontend/unit/`: Node-based frontend unit tests.
- `tests/frontend/fixtures/`: reusable frontend sample data.
- Runner: `pnpm test:frontend:unit`.

Current frontend unit tests focus on stable contracts that do not require booting Nuxt:

- API endpoint/method/body/query/header contracts in `utils/histosphereApi.ts`.
- Pure student-task logic in `composables/useStudentTask.ts`.

DOM-level component tests should be added later with a Vue/Nuxt test runner if the project adopts one.

## Backend

- `backend/tests/api/`: FastAPI API contract tests.
- `backend/tests/`: existing backend fixtures and provider tests.
- Runner: `cd backend && python -m pytest -q`.

Backend API tests use the in-memory repository and fake LLM provider from `backend/tests/conftest.py` so they do not call Supabase or external model providers.
