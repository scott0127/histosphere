-- Enforce one reusable material/persona set per canonical historical event.
-- 同一個 canonical historical event 必須共用同一組 Wikipedia source、task 與 persona；
-- condition 只能建立不同 experiment session / conversation，不能複製事件素材。

CREATE UNIQUE INDEX IF NOT EXISTS events_canonical_name_unique
ON events(canonical_name);

COMMENT ON INDEX events_canonical_name_unique IS
'Ensures each canonical historical event has exactly one reusable material/persona set across all experiment conditions.';
