-- Correct learner-facing Wushe copy; preserve previous tasks and session snapshots.
-- source_sha256: 75f70d58e8a1e148c0955c557b6806684b0f87b8a39a53ccf803eec02af0c4b7
DO $do$
DECLARE
  v_changes JSONB := $json${
  "version": "reading-materials-20260916-v4",
  "event_name": "霧社事件",
  "description_suffix_to_remove": "理解此事件時，需要同時考慮日本殖民政府、賽德克族部落、漢人居民、學校與警察制度等不同位置，並避免用單一善惡或單一民族敘事取代複雜的歷史判斷。",
  "instruction_before": "請根據兩份材料與照片，回答下面三題。",
  "instruction_after": "請根據下方的軍事紀錄介紹與歷史照片（含圖說），回答下面三題。"
}$json$::jsonb;
  v_event_id UUID;
  v_task event_tasks%ROWTYPE;
  v_payload JSONB;
BEGIN
  SELECT id INTO v_event_id FROM events
  WHERE canonical_name = v_changes ->> 'event_name';
  IF v_event_id IS NULL THEN RETURN; END IF;

  UPDATE events
  SET description = replace(description, v_changes ->> 'description_suffix_to_remove', ''),
      updated_at = now()
  WHERE id = v_event_id
    AND strpos(description, v_changes ->> 'description_suffix_to_remove') > 0;

  SELECT * INTO v_task FROM event_tasks
  WHERE event_id = v_event_id
  ORDER BY created_at DESC, id DESC
  LIMIT 1;
  IF NOT FOUND THEN RETURN; END IF;
  IF strpos(v_task.error_elicitation_task_full_text, v_changes ->> 'instruction_before') = 0 THEN
    RETURN;
  END IF;

  v_payload := jsonb_set(v_task.evaluation_payload, '{authoring,version}', v_changes -> 'version');
  INSERT INTO event_tasks (event_id, title, story_text, error_elicitation_task_full_text, evaluation_payload, revision_state)
  VALUES (
    v_task.event_id, v_task.title, v_task.story_text,
    replace(v_task.error_elicitation_task_full_text, v_changes ->> 'instruction_before', v_changes ->> 'instruction_after'),
    v_payload, v_task.revision_state
  );
END;
$do$;
