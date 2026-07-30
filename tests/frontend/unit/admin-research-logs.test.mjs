const audit = await globalThis.loadTsModule('utils/adminResearchLogs.ts');

const logs = [
  {
    id: 'log-1',
    event_id: 'event-1',
    action_type: 'event_updated',
    created_at: '2026-07-28T10:00:00Z',
    payload: {
      event_name: '法國大革命',
      updated_fields: ['description'],
      changes: {
        description: {
          before: '舊介紹',
          after: '新版介紹，包含逗號',
        },
      },
    },
  },
  {
    id: 'log-2',
    event_id: 'event-2',
    action_type: 'persona_updated',
    created_at: '2026-07-29T10:00:00Z',
    payload: {
      persona_name: '莫那·魯道',
      updated_fields: ['biography'],
      changes: {
        biography: {
          before: null,
          after: '更新後人物生平',
        },
      },
    },
  },
  {
    id: 'log-3',
    action_type: 'participant_updated',
    created_at: '2026-07-30T10:00:00Z',
    payload: {
      participant_code: 'P001',
      updated_fields: [],
      changes: {},
    },
  },
];

const filters = (overrides = {}) => ({
  search: '',
  actionType: '',
  eventId: '',
  dateFrom: '',
  dateTo: '',
  ...overrides,
});

test('admin research logs filter by action, event, date, and payload text', () => {
  assert.deepEqual(
    audit.filterResearchLogs(logs, filters({ actionType: 'persona_updated' })).map((log) => log.id),
    ['log-2'],
  );
  assert.deepEqual(
    audit.filterResearchLogs(logs, filters({ eventId: 'event-1' })).map((log) => log.id),
    ['log-1'],
  );
  assert.deepEqual(
    audit.filterResearchLogs(logs, filters({
      dateFrom: '2026-07-29',
      dateTo: '2026-07-30',
    })).map((log) => log.id),
    ['log-2', 'log-3'],
  );
  assert.deepEqual(
    audit.filterResearchLogs(logs, filters({ search: '莫那' })).map((log) => log.id),
    ['log-2'],
  );
  assert.deepEqual(
    audit.filterResearchLogs(logs, filters({ search: 'P001' })).map((log) => log.id),
    ['log-3'],
  );
});

test('admin research log helpers expose changes and readable values', () => {
  assert.deepEqual(audit.researchLogChanges(logs[0]), [
    {
      field: 'description',
      change: {
        before: '舊介紹',
        after: '新版介紹，包含逗號',
      },
    },
  ]);
  assert.equal(audit.formatResearchLogValue(null), '未設定');
  assert.equal(audit.formatResearchLogValue({ code: '01' }), '{\n  "code": "01"\n}');
  assert.equal(audit.researchLogActionLabel('event_updated'), '事件資料更新');
  assert.equal(audit.researchLogActionLabel('assistant_response_generated'), '一般 AI 回覆完成');
});

test('admin research log CSV is UTF-8 friendly and escapes nested payloads', () => {
  const csv = audit.researchLogsToCsv(logs.slice(0, 1), {
    'event-1': '法國大革命',
  });

  assert.equal(csv.startsWith('\uFEFF'), true);
  assert.equal(csv.includes('"法國大革命"'), true);
  assert.equal(csv.includes('"description"'), true);
  assert.equal(csv.includes('新版介紹，包含逗號'), true);
  assert.equal(csv.includes('""description""'), true);
});
