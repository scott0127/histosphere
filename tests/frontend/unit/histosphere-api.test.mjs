import assert from 'node:assert/strict';
import {
  sampleCondition,
  sampleEvent,
  samplePersona,
  sampleTask,
} from '../fixtures/histosphereFixtures.mjs';

const api = await globalThis.loadTsModule('utils/histosphereApi.ts');

const createFetchRecorder = (responses = {}) => {
  const calls = [];
  const fetcher = async (url, options) => {
    const method = options?.method || 'GET';
    calls.push({ url, options });
    return responses[`${method} ${url}`] ?? responses[url] ?? {};
  };
  return { calls, fetcher };
};

test('frontend api client fetches public event data from backend endpoints', async () => {
  const { calls, fetcher } = createFetchRecorder({
    'GET /api/conditions': [sampleCondition],
    'GET /api/events': [sampleEvent],
  });

  assert.deepEqual(await api.fetchConditions(fetcher), [sampleCondition]);
  assert.deepEqual(await api.fetchEvents(fetcher), [sampleEvent]);

  assert.deepEqual(
    calls.map((call) => [call.url, call.options]),
    [
      ['/api/conditions', undefined],
      ['/api/events', undefined],
    ],
  );
});

test('frontend api client sends admin key only to admin endpoints', async () => {
  const { calls, fetcher } = createFetchRecorder({
    'GET /api/admin/snapshot': {
      events: [sampleEvent],
      conditions: [sampleCondition],
      sessions: [],
      research_logs: [],
    },
    'PATCH /api/admin/events/event-1': sampleEvent,
    'PATCH /api/admin/tasks/task-1': sampleTask,
    'PATCH /api/admin/personas/persona-1': samplePersona,
    'PATCH /api/admin/conditions/condition-1': sampleCondition,
  });

  await api.fetchAdminSnapshot('test-admin', fetcher);
  await api.updateAdminEvent('test-admin', 'event-1', {
    canonical_name: '法國大革命',
    description: '新版介紹',
    century: 18,
    start_year: 1789,
    end_year: 1799,
    context: '新版脈絡',
    source_summary: {},
  }, fetcher);
  await api.updateAdminTask('test-admin', 'task-1', {
    title: sampleTask.title,
    story_text: sampleTask.story_text,
    display_text: sampleTask.display_text,
    evaluation_payload: sampleTask.evaluation_payload,
    revision_state: 'teacher_modified',
  }, fetcher);
  await api.updateAdminPersona('test-admin', 'persona-1', {
    name: samplePersona.name,
    role: samplePersona.role,
    biography: samplePersona.biography,
    prompt_profile: samplePersona.prompt_profile,
    active: true,
    revision_state: 'teacher_modified',
  }, fetcher);
  await api.updateAdminCondition('test-admin', 'condition-1', {
    label: sampleCondition.label,
    ebl_enabled: true,
    roleplay_enabled: true,
    agent_mode: 'persona',
    response_policy: 'scaffold',
    description: sampleCondition.description,
    active: true,
  }, fetcher);

  assert.equal(calls.length, 5);
  for (const call of calls) {
    assert.deepEqual(call.options.headers, { 'x-admin-key': 'test-admin' });
  }
  assert.equal(calls[1].options.method, 'PATCH');
  assert.equal(calls[2].options.body.revision_state, 'teacher_modified');
});

test('frontend api client initializes events and loads user progress with stable payload names', async () => {
  const { calls, fetcher } = createFetchRecorder({
    'POST /api/event/initialize': {
      event_id: 'event-1',
      session_id: 'session-1',
      event: sampleEvent,
      task: sampleTask,
      personas: [samplePersona],
      condition: sampleCondition,
    },
    'GET /api/sessions/progress': {
      progress: [
        {
          event_id: 'event-1',
          condition_key: 'ebl_roleplay',
          session_id: 'session-1',
          task_id: 'task-1',
          attempt_id: null,
          conversation_id: null,
          status: 'task_started',
          updated_at: '2026-01-01T00:00:00Z',
        },
      ],
    },
  });

  await api.initializeEventMaterial({
    eventName: '法國大革命',
    conditionKey: 'ebl_roleplay',
    rebuild: false,
    userId: 'participant-uuid',
  }, fetcher);
  await api.fetchUserProgress('participant-uuid', fetcher);

  assert.deepEqual(calls[0], {
    url: '/api/event/initialize',
    options: {
      method: 'POST',
      body: {
        event_name: '法國大革命',
        condition_key: 'ebl_roleplay',
        rebuild: false,
        user_id: 'participant-uuid',
      },
    },
  });
  assert.deepEqual(calls[1], {
    url: '/api/sessions/progress',
    options: { query: { user_id: 'participant-uuid' } },
  });
});

test('frontend api client preserves task draft, submit, conversation, and chat contracts', async () => {
  const { calls, fetcher } = createFetchRecorder({
    'GET /api/sessions/session-1/state': { session: { id: 'session-1' } },
    'PATCH /api/tasks/task-1/draft': { attempt: { id: 'attempt-1' } },
    'POST /api/tasks/task-1/submit': { conversation_id: 'conversation-1' },
    'GET /api/conversations/conversation-1': { conversation_id: 'conversation-1', messages: [] },
    'POST /api/chat': { response: 'ok' },
    'DELETE /api/event/event-1': { success: true },
  });

  await api.fetchSessionState('session-1', fetcher);
  await api.saveTaskDraft('task-1', {
    sessionId: 'session-1',
    userId: 'participant-uuid',
    responsePayload: { answers: [] },
  }, fetcher);
  await api.submitTaskAnswers('task-1', {
    sessionId: 'session-1',
    userId: 'participant-uuid',
    responsePayload: { answer_text: '回答' },
  }, fetcher);
  await api.fetchConversation('conversation-1', fetcher);
  await api.sendChatMessage({
    conversationId: 'conversation-1',
    userMessage: '你好',
    history: [],
    targetPersonaId: null,
  }, fetcher);
  await api.deleteEventMaterial('event-1', fetcher);

  assert.deepEqual(calls.map((call) => [call.url, call.options?.method || 'GET']), [
    ['/api/sessions/session-1/state', 'GET'],
    ['/api/tasks/task-1/draft', 'PATCH'],
    ['/api/tasks/task-1/submit', 'POST'],
    ['/api/conversations/conversation-1', 'GET'],
    ['/api/chat', 'POST'],
    ['/api/event/event-1', 'DELETE'],
  ]);
  assert.equal(calls[1].options.body.session_id, 'session-1');
  assert.equal(calls[2].options.body.response_payload.answer_text, '回答');
  assert.equal(calls[4].options.body.user_message, '你好');
});
