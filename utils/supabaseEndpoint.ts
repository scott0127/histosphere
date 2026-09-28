const localAuthBase = '/supabase-auth';

function isLoopbackSupabase(configuredUrl: string) {
  try {
    const url = new URL(configuredUrl);
    return ['http:', 'https:'].includes(url.protocol)
      && ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname);
  } catch {
    return false;
  }
}

export function supabaseAuthProxyRules(configuredUrl: string): Record<string, { proxy: string }> {
  if (!isLoopbackSupabase(configuredUrl)) return {};
  return {
    [`${localAuthBase}/auth/v1/**`]: {
      proxy: `${configuredUrl.replace(/\/+$/, '')}/auth/v1/**`,
    },
  };
}

export function resolveSupabaseAuthEndpoint(configuredUrl: string, browserOrigin?: string) {
  const configured = new URL(configuredUrl);
  return {
    url: browserOrigin && isLoopbackSupabase(configuredUrl)
      ? `${new URL(browserOrigin).origin}${localAuthBase}`
      : configuredUrl,
    // Match Supabase's original namespace so existing browser sessions survive the proxy change.
    storageKey: `sb-${configured.hostname.split('.')[0]}-auth-token`,
  };
}
