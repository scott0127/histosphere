# Development Gaps

Updated: 2026-07-11

This document separates locally verified behavior from remaining or explicitly deferred work. The current runtime was verified on 2026-07-11 with backend tests, frontend contract tests, Nuxt typecheck/build, real local Supabase reads, and browser smoke tests.

## Current Working Tree

### Runtime And Data Safety

- Local development keeps the standard Supabase `54320-54329` port block. `pnpm dev:full` releases `3000`/`8000`, reuses a healthy Supabase stack, waits for readiness, and reports startup duration.
- A one-time elevated Windows repair command prevents WinNAT from dynamically excluding the official Supabase port block; normal startup does not repeatedly stop WinNAT.
- Events are archived and restored through Admin endpoints. Public event listing excludes archived materials; Admin snapshot includes them for recovery.
- Learners can only start an existing active event. Creating new historical event materials requires an Admin override.
- Learner session initialization requires a bound, active participant and verifies that the requested condition code is present in `participants.condition_list`.
- Admin test flow can explicitly bypass participant assignment so researchers can test every condition without changing learner semantics.
- Session timers are opt-in. Admin can start or cancel a timer; elapsed sessions are completed by both a background worker and lazy runtime checks at task/chat boundaries.

### Task And Conversation Runtime

- Task drafts persist in `task_attempts.response_payload`.
- Task submit returns `202 Accepted`, persists a `processing` attempt, runs LLM judgement/conversation/greeting work in a background task, and exposes a polling endpoint.
- Attempt state is `in_progress -> processing -> submitted`, with `failed` retained as a retryable error state.
- Frontend polling resumes a persisted processing attempt after page reload and re-schedules orphaned work after a backend restart.
- Chat loads authoritative multi-turn history from DB `messages`, not from client-submitted history.
- Prompt context is bounded to the latest 12 messages and 1600 characters per message.
- Generated message metadata records prompt/profile hashes, module names, history message ids, provider and model.

### Prompt And Persona

- Condition-level prompt logic remains backend-managed rather than stored in Supabase.
- Canonical modules are `general_prompt`, `independent_1_prompt`, `independent_2_prompt`, `event_context`, `learner_task`, `conversation_history`, `persona_context`, `source_context`, `runtime_policy`, and `user_message`.
- `persona_prompt_v1` validates speaking style, social position, temporal/geographic/knowledge boundaries, stance, source policy, forbidden claims and researcher notes.
- Admin prompt preview renders the exact runtime modules without calling the LLM.
- Admin prompt dry-run calls the same provider/modules without saving messages or research logs.
- RAG is explicitly disabled in `source_context`; runtime must not imply that sources were retrieved.

## Gap Summary

| Area | Current State | Remaining |
| --- | --- | --- |
| Task authoring | Story-first UI, token/question validation, whole-payload save, draft autosave | Structured CRUD API, durable operation history, publish/readiness state |
| Task answers | Full answer bundle and async judgement state in `task_attempts` | Per-question normalized scoring, accepted-answer policy, answer-key audit trail |
| Event materials | Edit, archive and restore are available | Version history, before/after audit diff, publish snapshot/readiness |
| Prompt runtime | Versioned persona contract, canonical modules, DB history, preview/dry-run and hashes | Retry/fallback contract, stable provider errors, usage/latency metrics, content version registry |
| Participant/session | Auth mapping and condition assignment enforced; progress recovery and opt-in timer exist | Cross-device/re-login policy, stronger endpoint ownership checks, formal session close/debrief flow |
| RAG/source | Source/chunk schema exists; runtime reports RAG disabled | Deferred ingestion, chunking, embedding, retrieval and citation UI |
| Admin auth/audit | `x-admin-key` protects `/api/admin/*`; key plus Supabase Auth used by frontend | Key rotation, multi-admin roles, per-field audit diff, secret-management policy |
| Tests | Backend API tests and frontend contract/pure-function tests exist | Supabase integration tests, migration smoke test, DOM-level Vue tests, provider failure/concurrency tests |

## Required Next Work

### Provider Reliability And Observability

- Define primary/fallback provider and model allowlist.
- Classify timeout, rate limit, authentication, content-filter and provider 5xx errors.
- Use bounded retry only for retryable failures.
- Guarantee one learner turn creates at most one formal model message, even after retry or duplicate request.
- Optional production hardening: replace client-driven orphan recovery with startup reconciliation or a durable queue if the experiment is ever deployed with multiple backend instances.
- Persist correlation id, latency, token usage, fallback reason and provider attempt count.
- Add a per-conversation concurrency guard.
- Give task judgement, greeting, chat and persona generation separate runtime policies.

### Experiment Reproducibility

- Add event/task/persona/answer-key version history.
- Design draft, readiness and publish semantics.
- Make stored prompt hashes resolvable to reviewed prompt content.
- Add export format for thesis analysis.
- Decide whether animation/typewriter behavior should be disabled during measured sessions.

### Authorization And Ownership

- Audit all non-Admin write endpoints, including legacy persona endpoints, for learner-access semantics.
- Confirm task/chat/session reads and writes enforce the authenticated user's session ownership where required.
- Replace generic errors with stable field/error codes where the frontend needs actionable states.
- Add before/after payload diff to Admin write logs.

### Test Coverage

- Add Supabase repository integration tests without resetting or deleting real local research data.
- Add migration-up smoke tests against an isolated disposable database.
- Add DOM-level component tests for archive/restore, Admin-only create, async polling, timer banner and expired-session controls.
- Add prompt regression tests for all four condition cells and persona boundary violations.
- Add async idempotency, failure recovery and duplicate-submit tests.

## Explicitly Deferred

- **Material version lock:** deferred until snapshot schema, publish semantics and migration strategy are approved. Message-level hashes are not a substitute for a locked material snapshot.
- **RAG:** deferred. `knowledge_chunks` and `messages.rag_sources` remain preparatory schema only.
- **Requirement item 6:** deferred because no concrete behavior or acceptance criteria were specified.
- **Requirement item 8:** deferred; if it refers to RAG, the RAG decision above applies. If it means another feature, requirements must be supplied first.
- **Controlled deliberate historical errors:** disabled until a reviewed error contract, exposure log and debrief policy exist.

## Suggested Order

1. Implement provider reliability, idempotency and observability.
2. Audit endpoint ownership and add missing automated Supabase/DOM tests.
3. Design material publish/version semantics with the researcher before writing schema.
4. Keep RAG out of scope until source and citation policy are finalized.
