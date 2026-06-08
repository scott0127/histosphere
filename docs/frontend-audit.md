# Frontend Audit Notes

Updated: 2026-06-08

## Research Goal Alignment

Current frontend should serve the combination of Error-Based Learning (EBL) and AI historical persona role-play.

The UI should foreground:

- task before chat.
- learner misconceptions as productive errors.
- historical thinking.
- source interpretation.
- evidence-based argumentation.
- AI literacy.

It should not drift back into a purely immersive historical role-play showcase.

## Current Frontend Structure

### Pages

| File | Summary | Status |
|---|---|---|
| `pages/index.vue` | Starts a session: 2x2 condition selection, event input, existing event list. | Current V1 entry point. |
| `pages/task.vue` | Required task gate before conversation. Shows display text, story text, answer textarea, submit flow. | Current V1 learning gate. |
| `pages/chat.vue` | Loads conversation and sends messages using new `speaker_type/speaker_name/sequence_index` message shape. | Current V1 chat wrapper. |
| `pages/admin.vue` | Simple admin-key dashboard for conditions, tasks, personas, prompt_profile, research logs. | Current V1 teacher/researcher control surface. |
| `pages/tutorial.vue` | Legacy tutorial/demo. | Candidate for rewrite into experiment onboarding. |
| `pages/profile.vue`, `pages/auth/*.vue` | Supabase auth pages. | Keep only if participant accounts are required. |

### Components

| File | Summary | Status |
|---|---|---|
| `components/PersonaInputForm.vue` | Minimal historical event input form. | Current. |
| `components/EventListClassic.vue` | Minimal event list showing canonical name, time fallback, persona count, task state. | Current. |
| `components/ChatScreen.vue` | Generic/persona-aware chat UI; persona selector appears only for role-play conditions. | Current. |
| `components/AnnotatedText.vue` | Tooltip-style annotation rendering. | Keep. |
| `components/Typewriter.vue` | Typewriter display for latest assistant/persona message. | Keep for now; may affect reading-time measurement. |
| `components/AuthButton.vue` | Auth navigation. | Optional, currently not part of V1 flow. |
| `components/ImmersiveLoading.vue` | Legacy immersive loading. | Candidate for removal; V1 pages no longer use it. |
| `components/modals/DeleteConfirmationModal.vue` | Event delete confirmation. | Keep. |
| `components/modals/LegendConfirmationModal.vue` | Legacy legend warning. | Candidate for removal or rewrite as source/fiction warning. |

### Removed Prototype Components

- `components/BookInputForm.vue`
- `components/EventList.vue`
- `components/HistoricalMap.vue`
- `components/PersonaCardModal.vue`
- `components/HistoricalFiguresList.vue`
- `components/CinematicEventList.vue`
- `components/modals/FeedbackModal.vue`
- `pages/EventListOrigin.vue`

## Current API Usage

| Surface | API |
|---|---|
| `pages/index.vue` | `GET /api/conditions`, `GET /api/events`, `POST /api/event/initialize`, `DELETE /api/event/{event_id}` |
| `pages/task.vue` | `POST /api/tasks/{task_id}/submit` |
| `pages/chat.vue` | `GET /api/conversations/{conversation_id}`, `POST /api/chat` |
| `pages/admin.vue` | `GET /api/admin/snapshot`, `PATCH /api/admin/tasks/{task_id}`, `PATCH /api/admin/personas/{persona_id}`, `PATCH /api/admin/conditions/{condition_id}` |

## Design Notes

- The current UI intentionally uses a quiet research-tool layout rather than parchment/book imagery.
- Cards are simple 8-12px radius panels for grouped controls, not decorative nested card stacks.
- The palette is mostly slate/white with teal state highlights to avoid the old one-note parchment theme.
- Persona controls are hidden for no-role-play conditions.
- Task state is explicit before chat unlock.

## Remaining Risks

1. `/task` relies on `useState('taskData')`; reloading that route loses context. A future endpoint should reload task/session state.
2. `Typewriter` animation may affect reading-time measures. Consider disabling for experiment sessions.
3. Admin dashboard uses raw JSON textareas for `prompt_profile` and `evaluation_payload`; add validation feedback and schema hints later.
4. Auth pages still exist but are not connected to participant/session assignment.
5. `tutorial.vue` still demonstrates the old product style and should be rewritten or removed.
6. API orchestration still lives in pages. A future refactor should add `useExperimentSession`, `useTaskGate`, `useConversation`, and `useAdminSnapshot`.

## Suggested Next Refactors

1. Add backend reload endpoint for task/session and make `/task` refresh-safe.
2. Move `$fetch` calls into composables.
3. Add explicit participant/session ID handling.
4. Replace stub LLM output with Gemini provider and structured schemas.
5. Add save status/toasts to admin edits.
6. Rewrite tutorial as formal experiment instructions.
