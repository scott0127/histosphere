-- Add descriptive captions and the verified 1791 drawing without changing frozen sessions.
-- Clone the current task; retain its questions, answers, and researcher edits.
DO $do$
DECLARE
  v_task event_tasks%ROWTYPE;
  v_materials JSONB;
  v_payload JSONB;
  v_updates JSONB := $json${
  "japan_ryoma_plan": {
    "title": "1867 年坂本龍馬的《新政府綱領八策》",
    "caption": "幕末政局變動之際，坂本龍馬向土佐藩高層提出的新政體草案。"
  },
  "japan_nishi_plan": {
    "title": "1867 年西周的《議題草案》與《別紙議題草案》",
    "caption": "西周於 1867 年 12 月提出的政體構想，討論將軍、各藩與議事機構的權力安排。"
  },
  "opium_lin_letter": {
    "title": "1839 年林則徐致英國君主的禁煙書信",
    "caption": "林則徐在廣東推動禁煙時，透過書信要求英國君主約束販運鴉片的商人。"
  },
  "opium_nanjing_treaty": {
    "title": "1842 年《南京條約》的通商規定",
    "caption": "鴉片戰爭後清英簽訂的條約；本文選取第二、第五款涉及居住口岸與交易對象的規定。"
  },
  "wushe_military_records": {
    "title": "軍事紀錄：2010 年出版的霧社事件史料譯集",
    "caption": "《霧社事件日文史料翻譯》由國立臺灣歷史博物館出版，收錄較早的軍方文件及事件解說。"
  },
  "wushe_photographic_records": {
    "title": "約 1930 年霧社本部前整理行李的照片",
    "caption": "這份攝影資料收錄於佐藤政藏編《第一第二霧社事件誌》（1931 年），呈現士兵與行李整理的場景；攝影者不詳。"
  },
  "france_oath_record": {
    "title": "1789 年 6 月 20 日的網球場宣誓紀錄",
    "caption": "代表們轉往室內網球場集會，宣誓在憲法建立於穩固基礎之前不解散。"
  },
  "france_david_drawing": {
    "title": "大衛畫稿：1791 年描繪的網球場宣誓",
    "caption": "雅克路易大衛於 1791 年製作的預備畫稿，描繪 1789 年 6 月 20 日的宣誓；現藏凡爾賽宮。",
    "image_url": "/images/materials/tennis-court-oath-david-1791.jpg",
    "attribution": "凡爾賽宮 The Royal Tennis Court restored，第 6 頁；圖像為 Jacques-Louis David 1791 年預備畫稿（MV 840f），非 1883 年複製畫。檔案取自 Wikimedia Commons「Le Serment du Jeu de paume.jpg」，標示 PD-Art／公有領域；攝影署名 Château de Versailles, Dist. RMN / Jean-Marc Manaï。圖片未裁切、生成或修補。"
  }
}$json$::JSONB;
BEGIN
  FOR v_task IN
    SELECT DISTINCT ON (event_id) *
    FROM event_tasks
    ORDER BY event_id, created_at DESC, id DESC
  LOOP
    IF COALESCE(v_task.evaluation_payload #>> '{authoring,version}', '') NOT IN (
      'reading-task-draft-20260902-v1', 'wushe-reading-20260905-v2'
    ) THEN
      CONTINUE;
    END IF;
    IF EXISTS (
      SELECT 1 FROM event_tasks
      WHERE event_id = v_task.event_id
        AND evaluation_payload #>> '{authoring,version}' = 'reading-materials-20260905-v3'
    ) THEN
      CONTINUE;
    END IF;
    SELECT jsonb_agg(material || COALESCE(v_updates -> (material ->> 'id'), '{}'::JSONB) ORDER BY position)
    INTO v_materials
    FROM jsonb_array_elements(v_task.evaluation_payload -> 'materials') WITH ORDINALITY AS m(material, position);
    IF v_materials IS NULL THEN CONTINUE; END IF;
    v_payload := jsonb_set(v_task.evaluation_payload, '{materials}', v_materials);
    v_payload := jsonb_set(v_payload, '{authoring,version}', to_jsonb('reading-materials-20260905-v3'::TEXT));
    IF EXISTS (SELECT 1 FROM jsonb_array_elements(v_materials) m WHERE m ->> 'id' = 'france_david_drawing') THEN
      v_payload := jsonb_set(v_payload, '{authoring,sources}',
        COALESCE(v_payload #> '{authoring,sources}', '[]'::JSONB) ||
        '["https://commons.wikimedia.org/wiki/File:Le_Serment_du_Jeu_de_paume.jpg"]'::JSONB);
    END IF;
    INSERT INTO event_tasks (event_id, title, story_text, error_elicitation_task_full_text, evaluation_payload, revision_state)
    VALUES (v_task.event_id, v_task.title, v_task.story_text, v_task.error_elicitation_task_full_text, v_payload, v_task.revision_state);
  END LOOP;
END;
$do$;
