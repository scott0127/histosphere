const checks = [
  ['Nuxt 首頁', process.env.HISTOSPHERE_FRONTEND_URL || 'http://127.0.0.1:3000/'],
  ['Nuxt Admin', `${(process.env.HISTOSPHERE_FRONTEND_URL || 'http://127.0.0.1:3000').replace(/\/$/, '')}/admin`],
  ['FastAPI health', `${(process.env.HISTOSPHERE_BACKEND_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')}/health`],
  ['FastAPI OpenAPI', `${(process.env.HISTOSPHERE_BACKEND_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')}/openapi.json`],
];

const check = async ([label, url]) => {
  const controller = new AbortController();
  // Nuxt 首次載入會即時編譯頁面，冷啟動保留合理等待時間。
  const timeout = setTimeout(() => controller.abort(), 45_000);
  try {
    const response = await fetch(url, { redirect: 'manual', signal: controller.signal });
    if (response.status < 200 || response.status >= 400) {
      throw new Error(`${label} 回傳 ${response.status}`);
    }
    return `${label}: ${response.status}`;
  } finally {
    clearTimeout(timeout);
  }
};

try {
  const results = await Promise.all(checks.map(check));
  console.log(`Runtime smoke 檢查通過：\n- ${results.join('\n- ')}`);
} catch (error) {
  const message = error?.name === 'AbortError'
    ? 'Runtime smoke 等待逾時，請確認前後端已完成啟動。'
    : error?.message || String(error);
  console.error(message);
  process.exitCode = 1;
}
