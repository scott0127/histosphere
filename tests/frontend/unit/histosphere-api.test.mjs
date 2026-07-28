import assert from 'node:assert/strict';
import {
  sampleCondition,
  sampleEvent,
  samplePersona,
  sampleTask,
} from '../fixtures/histosphereFixtures.mjs';

const createMemoryStorage = () => {
  const values = new Map();
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, String(value)),
    removeItem: (key) => values.delete(key),
    clear: () => values.clear(),
  };
};

globalThis.window = {
  localStorage: createMemoryStorage(),
  sessionStorage: createMemoryStorage(),
};

const authSession = await globalThis.loadTsModule('utils/authSession.ts');
const adminSession = await globalThis.loadTsModule('utils/adminSession.ts');
const api = await globalThis.loadTsModule('utils/histosphereApi.ts');
authSession.setCurrentAccessToken('participant-jwt');

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
    'GET /api/admin/prompt-preview': {
      event: sampleEvent,
      condition: sampleCondition,
      persona: samplePersona,
      sample_user_message: '請說明重要性。',
      modules: [{ name: 'event_context', content: '法國大革命' }],
      prompt: '[event_context]\n法國大革命',
    },
    'POST /api/admin/prompt-dry-run': {
      event: sampleEvent,
      condition: sampleCondition,
      persona: samplePersona,
      sample_user_message: '請說明重要性。',
      modules: [{ name: 'event_context', content: '法國大革命' }],
      prompt: '[event_context]\n法國大革命',
      response: '測試回應',
      annotations: [],
      related_events: [],
      dynamic_context: '',
      rag_sources: [],
    },
    'PATCH /api/admin/events/event-1': sampleEvent,
    'PATCH /api/admin/tasks/task-1': sampleTask,
    'PATCH /api/admin/personas/persona-1': samplePersona,
    'PATCH /api/admin/conditions/condition-1': sampleCondition,
  });

  await api.fetchAdminSnapshot('test-admin', fetcher);
  await api.fetchAdminPromptPreview('test-admin', {
    eventId: 'event-1',
    conditionKey: 'ebl_roleplay',
    personaId: 'persona-1',
    sampleUserMessage: '請說明重要性。',
  }, fetcher);
  await api.runAdminPromptDryRun('test-admin', {
    eventId: 'event-1',
    conditionKey: 'ebl_roleplay',
    personaId: 'persona-1',
    sampleUserMessage: '請說明重要性。',
  }, fetcher);
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

  assert.equal(calls.length, 7);
  for (const call of calls) {
    assert.deepEqual(call.options.headers, { 'x-admin-key': 'test-admin' });
  }
  assert.deepEqual(calls[1].options.query, {
    event_id: 'event-1',
    condition_key: 'ebl_roleplay',
    persona_id: 'persona-1',
    sample_user_message: '請說明重要性。',
  });
  assert.deepEqual(calls[2], {
    url: '/api/admin/prompt-dry-run',
    options: {
      method: 'POST',
      headers: { 'x-admin-key': 'test-admin' },
      body: {
        event_id: 'event-1',
        condition_key: 'ebl_roleplay',
        persona_id: 'persona-1',
        sample_user_message: '請說明重要性。',
      },
    },
  });
  assert.equal(calls[3].options.method, 'PATCH');
  assert.equal(calls[4].options.body.revision_state, 'teacher_modified');
});

test('frontend api client archives and restores events through protected admin endpoints', async () => {
  const archivedEvent = { ...sampleEvent, archived_at: '2026-07-11T00:00:00Z' };
  const restoredEvent = { ...sampleEvent, archived_at: null };
  const { calls, fetcher } = createFetchRecorder({
    'POST /api/admin/events/event-1/archive': archivedEvent,
    'POST /api/admin/events/event-1/restore': restoredEvent,
  });

  assert.deepEqual(await api.archiveAdminEvent('test-admin', 'event-1', fetcher), archivedEvent);
  assert.deepEqual(await api.restoreAdminEvent('test-admin', 'event-1', fetcher), restoredEvent);
  assert.deepEqual(calls, [
    {
      url: '/api/admin/events/event-1/archive',
      options: { method: 'POST', headers: { 'x-admin-key': 'test-admin' } },
    },
    {
      url: '/api/admin/events/event-1/restore',
      options: { method: 'POST', headers: { 'x-admin-key': 'test-admin' } },
    },
  ]);
});

test('frontend api client creates, archives, and restores participants through admin endpoints', async () => {
  const participant = {
    id: 'participant-6',
    code: 'P006',
    auth_user_id: 'auth-6',
    condition_list: ['01', '04'],
    status: 'active',
  };
  const { calls, fetcher } = createFetchRecorder({
    'POST /api/admin/participants': participant,
    'POST /api/admin/participants/participant-6/archive': { ...participant, status: 'archived' },
    'POST /api/admin/participants/participant-6/restore': participant,
  });

  await api.createAdminParticipant('test-admin', {
    code: 'P006',
    auth_user_id: 'auth-6',
    condition_list: ['01', '04'],
  }, fetcher);
  await api.archiveAdminParticipant('test-admin', 'participant-6', fetcher);
  await api.restoreAdminParticipant('test-admin', 'participant-6', fetcher);

  assert.deepEqual(calls, [
    {
      url: '/api/admin/participants',
      options: {
        method: 'POST',
        headers: { 'x-admin-key': 'test-admin' },
        body: {
          code: 'P006',
          auth_user_id: 'auth-6',
          condition_list: ['01', '04'],
        },
      },
    },
    {
      url: '/api/admin/participants/participant-6/archive',
      options: { method: 'POST', headers: { 'x-admin-key': 'test-admin' } },
    },
    {
      url: '/api/admin/participants/participant-6/restore',
      options: { method: 'POST', headers: { 'x-admin-key': 'test-admin' } },
    },
  ]);
});

test('prompt dry-run uses a deterministic sample message when none is supplied', async () => {
  const { calls, fetcher } = createFetchRecorder();

  await api.runAdminPromptDryRun('test-admin', {
    eventId: 'event-1',
    conditionKey: 'no_ebl_no_roleplay',
  }, fetcher);

  assert.deepEqual(calls[0].options.body, {
    event_id: 'event-1',
    condition_key: 'no_ebl_no_roleplay',
    persona_id: null,
    sample_user_message: '請說明這個事件的重要性。',
  });
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
      headers: { Authorization: 'Bearer participant-jwt' },
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
    options: {
      headers: { Authorization: 'Bearer participant-jwt' },
      query: { user_id: 'participant-uuid' },
    },
  });
});

test('frontend api client preserves task draft, asynchronous submit polling, conversation, and chat contracts', async () => {
  const accepted = {
    attempt_id: 'attempt-1',
    status: 'processing',
    poll_url: '/api/tasks/attempts/attempt-1',
  };
  const processing = {
    attempt: {
      id: 'attempt-1',
      status: 'processing',
      response_payload: { answer_text: '回答' },
    },
    result: null,
    error: null,
  };
  const { calls, fetcher } = createFetchRecorder({
    'GET /api/sessions/session-1/state': { session: { id: 'session-1' } },
    'PATCH /api/tasks/task-1/draft': { attempt: { id: 'attempt-1' } },
    'POST /api/tasks/task-1/submit': accepted,
    'GET /api/tasks/attempts/attempt-1': processing,
    'GET /api/conversations/conversation-1': { conversation_id: 'conversation-1', messages: [] },
    'POST /api/chat': { response: 'ok' },
  });

  await api.fetchSessionState('session-1', fetcher);
  await api.saveTaskDraft('task-1', {
    sessionId: 'session-1',
    userId: 'participant-uuid',
    responsePayload: { answers: [] },
  }, fetcher);
  assert.deepEqual(await api.submitTaskAnswers('task-1', {
    sessionId: 'session-1',
    userId: 'participant-uuid',
    responsePayload: { answer_text: '回答' },
  }, fetcher), accepted);
  assert.deepEqual(await api.fetchTaskSubmissionStatus('attempt-1', fetcher), processing);
  await api.fetchConversation('conversation-1', fetcher);
  await api.sendChatMessage({
    conversationId: 'conversation-1',
    userMessage: '你好',
    history: [],
    targetPersonaId: null,
  }, fetcher);

  assert.deepEqual(calls.map((call) => [call.url, call.options?.method || 'GET']), [
    ['/api/sessions/session-1/state', 'GET'],
    ['/api/tasks/task-1/draft', 'PATCH'],
    ['/api/tasks/task-1/submit', 'POST'],
    ['/api/tasks/attempts/attempt-1', 'GET'],
    ['/api/conversations/conversation-1', 'GET'],
    ['/api/chat', 'POST'],
  ]);
  for (const call of calls) {
    assert.deepEqual(call.options.headers, { Authorization: 'Bearer participant-jwt' });
  }
  assert.equal(calls[1].options.body.session_id, 'session-1');
  assert.deepEqual(calls[2].options.body, {
    session_id: 'session-1',
    user_id: 'participant-uuid',
    response_payload: { answer_text: '回答' },
  });
  assert.equal(calls[5].options.body.user_message, '你好');
});

test('admin test mode uses the tab-scoped admin key instead of a learner JWT', async () => {
  adminSession.setAdminSessionKey('test-admin');
  const { calls, fetcher } = createFetchRecorder();

  await api.fetchSessionState('session-admin-test', fetcher);

  assert.deepEqual(calls[0], {
    url: '/api/sessions/session-admin-test/state',
    options: { headers: { 'x-admin-key': 'test-admin' } },
  });
  adminSession.clearAdminSession();
});

test('frontend api client resets the fixed five-minute session timer', async () => {
  const runningSession = {
    id: 'session-1',
    timer_started_at: '2026-07-11T00:00:00Z',
    timer_ends_at: '2026-07-11T00:05:00Z',
  };
  const { calls, fetcher } = createFetchRecorder({
    'POST /api/admin/sessions/session-1/timer': runningSession,
  });

  assert.deepEqual(await api.resetAdminSessionTimer('test-admin', 'session-1', fetcher), runningSession);
  assert.deepEqual(calls, [
    {
      url: '/api/admin/sessions/session-1/timer',
      options: {
        method: 'POST',
        headers: { 'x-admin-key': 'test-admin' },
        body: { duration_minutes: 5 },
      },
    },
  ]);
});

test('frontend api client restarts a session through the protected admin endpoint', async () => {
  const response = {
    archived_sessions: [{ id: 'session-old', status: 'archived' }],
    new_session: { id: 'session-new', status: 'initialized' },
  };
  const { calls, fetcher } = createFetchRecorder({
    'POST /api/admin/sessions/session-old/restart': response,
  });

  assert.deepEqual(
    await api.restartAdminSession('test-admin', 'session-old', fetcher),
    response,
  );
  assert.deepEqual(calls, [
    {
      url: '/api/admin/sessions/session-old/restart',
      options: {
        method: 'POST',
        headers: { 'x-admin-key': 'test-admin' },
      },
    },
  ]);
});

test('frontend chat stream parses split SSE frames and keeps learner authentication', async () => {
  const completeResponse = {
    response: '這是一段已驗證的回覆。',
    assistant_name: 'AI Assistant',
    message: {
      id: 'message-ai',
      conversation_id: 'conversation-1',
      speaker_type: 'assistant',
      speaker_name: 'AI Assistant',
      sequence_index: 2,
      content: '這是一段已驗證的回覆。',
      metadata: { generation_status: 'completed', delivery_mode: 'validated_stream' },
    },
  };
  const sse = [
    `event: user_message\ndata: ${JSON.stringify({
      type: 'user_message',
      message: {
        id: 'message-user',
        speaker_type: 'learner',
        speaker_name: 'learner',
        sequence_index: 1,
        content: '請回答。',
      },
    })}\n\n`,
    `event: status\ndata: ${JSON.stringify({
      type: 'status',
      stage: 'generating',
      message: '正在整理史料與回覆…',
    })}\n\n`,
    `event: delta\ndata: ${JSON.stringify({ type: 'delta', content: '這是一段' })}\n\n`,
    `event: delta\ndata: ${JSON.stringify({ type: 'delta', content: '已驗證的回覆。' })}\n\n`,
    `event: complete\ndata: ${JSON.stringify({ type: 'complete', response: completeResponse })}\n\n`,
  ].join('');
  const encoded = new TextEncoder().encode(sse);
  const splitAt = Math.floor(encoded.length / 2);
  const calls = [];
  const fetcher = async (url, options) => {
    calls.push({ url, options });
    return new Response(
      new ReadableStream({
        start(controller) {
          controller.enqueue(encoded.slice(0, splitAt));
          controller.enqueue(encoded.slice(splitAt));
          controller.close();
        },
      }),
      { status: 200, headers: { 'Content-Type': 'text/event-stream' } },
    );
  };
  const eventTypes = [];

  const result = await api.sendChatMessageStream(
    {
      conversationId: 'conversation-1',
      userMessage: '請回答。',
      history: [],
    },
    (event) => eventTypes.push(event.type),
    fetcher,
  );

  assert.deepEqual(result, completeResponse);
  assert.deepEqual(eventTypes, ['user_message', 'status', 'delta', 'delta', 'complete']);
  assert.equal(calls[0].url, '/api/chat/stream');
  assert.equal(calls[0].options.headers.Authorization, 'Bearer participant-jwt');
  assert.equal(calls[0].options.headers.Accept, 'text/event-stream');
  assert.deepEqual(JSON.parse(calls[0].options.body), {
    conversation_id: 'conversation-1',
    user_message: '請回答。',
    history: [],
    target_persona_id: null,
  });
});
