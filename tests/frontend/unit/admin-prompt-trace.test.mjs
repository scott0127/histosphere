import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createSSRApp, h } from 'vue';
import { renderToString } from 'vue/server-renderer';
import { compileScript, parse } from 'vue/compiler-sfc';
import ts from 'typescript';

const filename = 'components/admin/PromptExecutionDetails.vue';
const source = await readFile(filename, 'utf8');
const { descriptor } = parse(source, { filename });
const compiled = compileScript(descriptor, { id: 'admin-prompt-trace', inlineTemplate: true }).content;
const output = ts.transpileModule(compiled, {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext },
}).outputText.replace(/from ['"]vue['"]/g, `from ${JSON.stringify(import.meta.resolve('vue'))}`);
const component = (await import(`data:text/javascript;base64,${Buffer.from(output).toString('base64')}`)).default;
const result = (overrides = {}) => ({
  condition: { roleplay_enabled: true, ebl_enabled: true },
  final_prompt_kind: 'repair', final_prompt: 'SERVICE_REPAIR_MARKER', schema_repair_count: 1,
  final_messages: [{ role: 'system', content: 'SYSTEM_MARKER' }, { role: 'user', content: 'JSON_REPAIR_MARKER' }],
  modules: [{ name: 'initial_persona', content: 'BASE_PERSONA_MARKER' }],
  ...overrides,
});
const render = (value) => renderToString(createSSRApp({ render: () => h(component, { result: value }) }));

test('admin final prompt renders exact system/user and repairs separately from initial modules', async () => {
  const html = await render(result());
  for (const marker of ['SYSTEM_MARKER', 'JSON_REPAIR_MARKER', 'SERVICE_REPAIR_MARKER', 'BASE_PERSONA_MARKER']) {
    assert.match(html, new RegExp(marker));
  }
  assert.match(html, /最後實際送出的 LLM 訊息/);
  assert.match(html, /最後一次 JSON 格式修復/);
  assert.match(html, /基底提示詞＋修正指令/);
  assert.match(html, /首次組裝的基底模組（供比對）/);
  assert.match(html, /包含歷史人物設定/);
  assert.match(html, /包含 EBL 引導/);
  assert.ok(html.indexOf('SYSTEM_MARKER') < html.indexOf('BASE_PERSONA_MARKER'));
});

test('admin constrained recovery does not claim to use the complete original EBL/persona combination', async () => {
  const html = await render(result({ final_prompt_kind: 'constrained', schema_repair_count: 0 }));
  assert.match(html, /受限恢復引導/);
  assert.match(html, /完整 EBL 策略、答案與歷史材料未沿用/);
  assert.doesNotMatch(html, /包含歷史人物設定|包含 EBL 引導/);
  assert.match(html, /此清單描述最初組裝/);
});

test('admin fixed fallback and missing trace do not relabel base preview as an actual LLM request', async () => {
  const fallback = await render(result({ final_prompt_kind: 'system_fallback', final_prompt: '', final_messages: [] }));
  assert.match(fallback, /沒有產生此回覆的 LLM 提示詞/);
  assert.doesNotMatch(fallback, /最後實際送出的 LLM 訊息/);
  const missing = await render(result({ final_messages: [] }));
  assert.match(missing, /不能以基底預覽代替/);
  assert.doesNotMatch(missing, /最後實際送出的 LLM 訊息/);
});
