export const sampleCondition = {
  id: 'condition-1',
  condition_key: 'ebl_roleplay',
  label: '04 模式',
  ebl_enabled: true,
  roleplay_enabled: true,
  agent_mode: 'persona',
  response_policy: 'scaffold',
  description: '測試條件',
  active: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

export const sampleEvent = {
  id: 'event-1',
  canonical_name: '法國大革命',
  description: '舊制度危機與革命轉折。',
  century: 18,
  start_year: 1789,
  end_year: 1799,
  context: '測試事件脈絡',
  source_summary: { review_state: 'teacher_modified' },
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  personas: [],
  latest_task: null,
};

export const sampleTask = {
  id: 'task-1',
  event_id: 'event-1',
  title: '法國大革命：舊制度危機與革命轉折',
  story_text: '1789 年以前，法國舊制度面臨財政危機。',
  error_elicitation_task_full_text: '1789 年以前，法國舊制度面臨 {{blank:q01}}，第三等級主張以 {{blank:q02}} 表決。',
  revision_state: 'teacher_modified',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  evaluation_payload: {
    rubric: '測試 rubric',
    questions: [
      {
        id: 'q01',
        blank_id: 'q01',
        type: 'cloze',
        prompt: '請填入舊制度危機。',
        source_text: '財政危機',
        correct_answer: '財政危機',
        required: true,
      },
      {
        id: 'q02',
        blank_id: 'q02',
        type: 'multiple_choice',
        prompt: '第三等級主張哪種表決方式？',
        options: [
          { id: 'a', label: '人數', value: '人數' },
          { id: 'b', label: '等級', value: '等級' },
        ],
        correct_answer: '人數',
        required: true,
      },
    ],
  },
};

export const samplePersona = {
  id: 'persona-1',
  event_id: 'event-1',
  name: '馬克西米連·羅伯斯比爾',
  role: '雅各賓派領袖',
  biography: '測試人物',
  expertise_areas: ['法國大革命'],
  sources: [],
  prompt_profile: { speaking_style: 'formal' },
  avatar_url: null,
  active: true,
  sort_order: 0,
  revision_state: 'teacher_modified',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};
