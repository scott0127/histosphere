-- 明確區分 Admin 測試 Session 與正式受測者 Session。
-- 既有資料預設視為非 Admin test；正式匯出仍會另外要求 Participant 綁定，
-- 因此舊的未綁定測試資料也不會混入正式研究資料。

ALTER TABLE experiment_sessions
  ADD COLUMN IF NOT EXISTS is_admin_test BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN experiment_sessions.is_admin_test IS
  'TRUE 表示由 Admin 測試模式建立；可供後台重播，但不得進入正式研究匯出。';
