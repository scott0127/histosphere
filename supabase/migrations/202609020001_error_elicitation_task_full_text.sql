-- 統一完整題文名稱；只改欄位名稱，不刪除任何現有 Task 或研究資料。
do $$
begin
  if exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'event_tasks' and column_name = 'display_text'
  ) then
    alter table public.event_tasks rename column display_text to error_elicitation_task_full_text;
  end if;
end $$;

comment on column public.event_tasks.error_elicitation_task_full_text is
  'Complete Error-Elicitation Task text, including shared context and all question statements. Question markers map to answer and rationale blocks.';
