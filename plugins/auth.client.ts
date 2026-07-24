export default defineNuxtPlugin(async () => {
  // 任何 learner 頁面重新整理後，都先恢復 Supabase session 與 JWT 再發出受保護 API 請求。
  const { initialize } = useAuth();
  await initialize();
});
