import assert from 'node:assert/strict';
import { createClient } from '@supabase/supabase-js';

const { resolveSupabaseAuthEndpoint, supabaseAuthProxyRules } = await globalThis.loadTsModule('utils/supabaseEndpoint.ts');

test('local Supabase Auth follows the browser origin when the host changes networks', () => {
  for (const configured of ['http://localhost:54321', 'http://127.0.0.1:54321', 'http://[::1]:54321']) {
    for (const origin of ['http://localhost:3002', 'http://10.0.0.25:3002', 'http://192.168.1.50:3002', 'https://lab.example.test']) {
      assert.equal(resolveSupabaseAuthEndpoint(configured, origin).url, `${origin}/supabase-auth`);
    }
    assert.equal(resolveSupabaseAuthEndpoint(configured).url, configured, 'server-side resolution has no browser origin');
  }
});

test('hosted and explicitly configured remote Supabase endpoints remain unchanged', () => {
  for (const configured of ['https://project.supabase.co', 'http://192.168.1.10:54321', 'https://localhost.example.test']) {
    assert.equal(resolveSupabaseAuthEndpoint(configured, 'http://192.168.1.50:3002').url, configured);
    assert.deepEqual(supabaseAuthProxyRules(configured), {});
  }
  assert.deepEqual(supabaseAuthProxyRules(''), {});
  assert.deepEqual(supabaseAuthProxyRules('not-a-url'), {});
});

test('local Supabase proxy exposes only Auth routes', () => {
  assert.deepEqual(supabaseAuthProxyRules('http://127.0.0.1:54321/'), {
    '/supabase-auth/auth/v1/**': { proxy: 'http://127.0.0.1:54321/auth/v1/**' },
  });
  assert.deepEqual(supabaseAuthProxyRules('http://[::1]:54321'), {
    '/supabase-auth/auth/v1/**': { proxy: 'http://[::1]:54321/auth/v1/**' },
  });
});

test('proxied Auth preserves the installed SDK original token storage namespace', async () => {
  const authOptions = { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false };
  for (const configured of ['http://localhost:54321', 'http://127.0.0.1:54321', 'http://[::1]:54321', 'https://project.supabase.co']) {
    const original = createClient(configured, 'test-anon-key', { auth: authOptions });
    const endpoint = resolveSupabaseAuthEndpoint(configured, 'http://192.168.1.50:3002');
    assert.equal(endpoint.storageKey, original.auth.storageKey);

    const requests = [];
    const proxied = createClient(endpoint.url, 'test-anon-key', {
      auth: { ...authOptions, storageKey: endpoint.storageKey },
      global: { fetch: async (url) => {
        requests.push(String(url));
        return new Response(JSON.stringify({ error: 'invalid_grant', error_description: 'Test credentials' }), {
          status: 400, headers: { 'content-type': 'application/json' },
        });
      } },
    });
    await proxied.auth.signInWithPassword({ email: 'test@example.test', password: 'test-password' });
    assert.equal(proxied.auth.storageKey, original.auth.storageKey);
    assert.deepEqual(requests, [`${endpoint.url}/auth/v1/token?grant_type=password`]);
  }
});
