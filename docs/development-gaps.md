# Development Gaps

Updated: 2026-06-24

This document tracks what has been completed, what is still missing, and what frontend/backend gaps remain. It consolidates the former `admin-backend-todo.md`, `backend-implementation-audit.md`, and risk sections from `frontend-audit.md`.

## Recent Completions

- Admin event update API `PATCH /api/admin/events/{event_id}` — admin UI "save event" now writes back to `events` and logs `research_logs.event_updated`.
- `supabase/seed.sql` seeds sample events, personas, and tasks. Seed does not specify fixed UUIDs.
- Backend tests use fake LLM provider to avoid calling external models during pytest.
- `docs/supabase-schema.md` exports local Supabase `public` schema.
- Condition-level LLM prompt no longer stored in Supabase; `experiment_conditions` only saves research condition fields, prompts managed by backend code.
- Session progress endpoint `GET /api/sessions/progress` implemented.
- Session state reload endpoint `GET /api/sessions/{session_id}/state` implemented.
- Task draft save endpoint `PATCH /api/tasks/{task_id}/draft` implemented.
- Frontend event library now reads condition progress from the session progress API, with localStorage only as a fallback.
- Frontend task gate now reloads from `sessionId` and autosaves draft answers through the task draft API.
- Task UI moved to `/sessions/[sessionId]/task`; `/task?sessionId=...` remains only as a legacy redirect.
- Task API orchestration moved from page code into `useTaskGate`.
- Conversation UI moved to `/conversations/[conversationId]`; `/chat?conversationId=...` remains only as a legacy redirect.
- Conversation API orchestration moved from page code into `useConversationSession`.
- Legacy frontend components deleted: `AuthButtonLegacy`, `EventListClassicLegacy`, `ImmersiveLoadingLegacy`, `PersonaInputFormLegacy`, `LegendConfirmationModalLegacy`.
- Development-only page `frontend-test.vue` and mock data `data/mockFrontend.ts` deleted.
- One-time scripts (`test-gsap.mjs`, `process-image.mjs`) and broken font file deleted.

## Gap Summary

| Area | Current State | Missing |
|---|---|---|
| Task authoring | Admin UI patches `display_text` + `evaluation_payload` as a whole; task draft save exists | Structured question CRUD, server-side token validation, publish snapshot, answer version history |
| Task answers | `task_attempts.response_payload` stores full answer bundle | `task_answers` table exists but unused; missing per-question scoring, answer key audit trail |
| Event materials | Events can be PATCH-updated from admin UI; sample materials via seed.sql | Missing version history, material readiness check, archive strategy |
| Prompt management | Condition-level prompt managed in backend code; `personas.prompt_profile` editable | Missing prompt preview/dry-run endpoint, prompt hash/audit |
| Participant/session | `experiment_sessions` has user_id; session progress/state endpoints exist; event library and task gate use them | Missing formal participant account mapping, participant roster/admin import, cross-device identity policy |
| RAG/source | `wiki_sources` and `knowledge_chunks` tables exist; RAG retrieve is empty implementation | Missing ingestion, chunking, embedding/vector retrieval, source citation |
| Admin auth | All `/api/admin/*` check `x-admin-key`; frontend uses Supabase Auth + admin key | Missing role-based admin policy, multi-user management, fine-grained audit diff |
| Tests | API tests use in-memory repository + fake LLM provider | Missing Supabase repository integration tests, migration/seed SQL smoke test |

## Task Authoring Gaps

- Build formal task question CRUD API instead of whole-JSON PATCH.
- Define backend validation rules for question schema: types, IDs, blank IDs, options, correct answers, required fields, explanations.
- Support question ordering, duplication, deactivation, and deletion records.
- Support durable undo/redo history for task authoring edits.
- Support answer key version history so research data collected under previous answer keys remains traceable.
- Support story-first token audit: record `display_text` token ↔ question mapping.
- Build structured story segments to replace raw `display_text` string manipulation.
- Build token-level operation APIs (insert, remove, move question tokens).
- Backend should validate raw token corruption before save: duplicate blank IDs, orphan tokens, question without token, inline type missing token, MC answer not in options.
- Support version diff for inline question insert/delete/type-change, including replaced `source_text`.
- Backend judgement should read structured questions explicitly, not rely on LLM interpreting raw payload.
- Build task publish/draft state so researchers can edit drafts before applying to learner flow.
- Build formal experiment material snapshot: event, task, questions, personas, condition prompts locked at publish time.
- Add task material readiness endpoint: check if four condition prompts, question answers, event context, and token↔question mapping are all complete.

## Event Management Gaps

- Event update should be versioned to prevent research material overwrite.
- Add controlled event re-generation (task/persona) with old version preservation.
- Build event data version history: who modified, when, before/after diff.
- Add event delete/archive strategy to prevent accidental deletion of events bound to research sessions.
- Build event material completeness check endpoint.

## Prompt & Persona Gaps

- Build prompt preview endpoint for researchers to see assembled prompt modules.
- Build prompt dry-run endpoint for test responses with fixed input.
- 2x2 condition EBL/role-play/response-policy should be treated as research design constants; admin UI should not freely toggle them without stricter permission.
- Persona `prompt_profile` is still raw JSON; consider splitting into speaking style, knowledge boundary, teacher notes, source policy fields.
- Prompt save API should return schema validation errors.

## Learning Flow & Conversation Gaps

- Keep `/chat?conversationId=...` as legacy redirect only; new links should use `/conversations/[conversationId]`.
- Keep `/task?sessionId=...` as legacy redirect only; new links should use `/sessions/[sessionId]/task`.
- Formalize participant ID ↔ Supabase user ID ↔ experiment session ID mapping.
- Keep localStorage progress only as a temporary fallback; production flow should depend on backend session APIs.
- Add UI/interaction audit log for formal experiment sessions.

## Auth & Audit Gaps

- Short-term: Supabase Auth login + admin key dual-layer. Multi-user role-based access for later.
- Frontend admin mode requires successful `/api/admin/snapshot` call; localStorage only remembers view preference.
- All admin write operations need audit log with payload diff.
- Backend should return validation errors per field, not generic failure.

## Frontend Remaining Risks

1. `Typewriter` animation may affect reading-time measures. Consider disabling for formal experiment sessions.
2. Admin dashboard still exposes advanced JSON for `prompt_profile` and `evaluation_payload`; structured task editing exists, but prompt editing still needs schema hints.
3. Auth pages exist but are not connected to participant/session assignment.
4. `tutorial.vue` still demonstrates old product style; should be rewritten as formal experiment instructions or removed.
5. Some API orchestration still lives in pages. Future refactor should add `useExperimentSession` and `useAdminSnapshot` composables.

## Suggested Next Milestones

1. Move remaining `$fetch` calls into composables.
2. Add explicit participant/session ID handling.
3. Harden LiteLLM structured outputs for task generation and judgement.
4. Add save status/toasts to admin edits.
5. Decide blank-level scoring and EBL coding with advisor.
6. Add export format for thesis analysis.
7. Rewrite tutorial as formal experiment instructions.
