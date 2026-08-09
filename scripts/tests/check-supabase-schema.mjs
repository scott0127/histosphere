import { readFileSync } from 'node:fs';

const parseEnvFile = (path) => {
  try {
    return Object.fromEntries(
      readFileSync(path, 'utf8')
        .split(/\r?\n/)
        .map((line) => line.trim())
        .filter((line) => line && !line.startsWith('#') && line.includes('='))
        .map((line) => {
          const separator = line.indexOf('=');
          const key = line.slice(0, separator).trim();
          const value = line.slice(separator + 1).trim().replace(/^['"]|['"]$/g, '');
          return [key, value];
        }),
    );
  } catch {
    return {};
  }
};

const fileEnv = parseEnvFile('.env');
const env = { ...fileEnv, ...process.env };
const supabaseUrl = env.SCHEMA_SUPABASE_URL || env.VITE_SUPABASE_URL || env.SUPABASE_URL;
const supabaseKey = env.SCHEMA_SUPABASE_KEY
  || env.VITE_SUPABASE_ANON_KEY
  || env.SUPABASE_ANON_KEY
  || env.SUPABASE_SERVICE_ROLE_KEY
  || env.SUPABASE_KEY_service_role
  || env.SUPABASE_KEY;

if (!supabaseUrl || !supabaseKey) {
  throw new Error('缺少 Supabase URL 或 key，無法執行唯讀 schema 檢查。');
}

const expectedSchema = {
  conversations: ['id', 'event_id', 'session_id', 'user_id', 'status'],
  event_tasks: ['id', 'event_id', 'story_text', 'display_text', 'evaluation_payload'],
  events: ['id', 'canonical_name', 'description', 'source_summary', 'archived_at'],
  experiment_conditions: ['id', 'condition_key', 'ebl_enabled', 'roleplay_enabled', 'active'],
  experiment_sessions: ['id', 'condition_key_snapshot', 'user_id', 'event_id', 'status', 'timer_ends_at'],
  knowledge_chunks: ['id', 'event_id', 'content', 'embedding', 'metadata'],
  messages: ['id', 'conversation_id', 'speaker_type', 'sequence_index', 'content', 'metadata'],
  personas: ['id', 'event_id', 'name', 'prompt_profile', 'avatar_url', 'active'],
  participants: ['id', 'code', 'auth_user_id', 'condition_list', 'status'],
  research_logs: ['id', 'session_id', 'user_id', 'action_type', 'payload'],
  task_answers: ['id'],
  task_attempts: ['id', 'task_id', 'session_id', 'user_id', 'status', 'response_payload'],
  task_blanks: ['id'],
  wiki_sources: ['id', 'event_id'],
};

const controller = new AbortController();
const timeout = setTimeout(() => controller.abort(), 10_000);
let response;
try {
  response = await fetch(`${supabaseUrl.replace(/\/$/, '')}/rest/v1/`, {
    headers: {
      Accept: 'application/openapi+json',
      apikey: supabaseKey,
      Authorization: `Bearer ${supabaseKey}`,
    },
    signal: controller.signal,
  });
} catch (error) {
  const message = error?.name === 'AbortError'
    ? 'Supabase schema 檢查等待逾時。'
    : '無法連線 Supabase；請先執行 pnpm dev:full。';
  console.error(message);
  process.exit(1);
} finally {
  clearTimeout(timeout);
}

if (!response.ok) {
  throw new Error(`Supabase schema endpoint 回傳 ${response.status}。`);
}

const openApi = await response.json();
const definitions = openApi.definitions || openApi.components?.schemas || {};
const errors = [];

for (const [table, columns] of Object.entries(expectedSchema)) {
  const definition = definitions[table];
  if (!definition) {
    errors.push(`缺少資料表 ${table}`);
    continue;
  }
  const properties = definition.properties || {};
  for (const column of columns) {
    if (!(column in properties)) errors.push(`${table} 缺少欄位 ${column}`);
  }
}

if (errors.length) {
  throw new Error(`Supabase schema 不符合應用程式契約：\n- ${errors.join('\n- ')}`);
}

console.log(`Supabase schema 檢查通過：${Object.keys(expectedSchema).length} 個資料表，且未寫入任何資料。`);
